import requests
import re
from typing import List, Dict
import logging
import json
import os
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 用語集ファイルのパス
GLOSSARY_FILE = Path(__file__).parent / "data" / "glossary.json"

# プロンプト定義ファイルのパス
PROMPTS_FILE = Path(__file__).parent / "prompts.json"

# プロンプトキャッシュ
_prompts_cache = None

def load_prompts() -> Dict:
    """
    プロンプト定義ファイルを読み込む

    Returns:
        プロンプト定義辞書
    """
    global _prompts_cache

    if _prompts_cache is not None:
        return _prompts_cache

    try:
        if PROMPTS_FILE.exists():
            with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
                _prompts_cache = json.load(f)
                logger.info(f"Loaded prompts for {len(_prompts_cache.get('document_types', {}))} document types")
                return _prompts_cache
    except Exception as e:
        logger.error(f"Error loading prompts: {e}")

    # デフォルトのプロンプト（ファイルが存在しない場合）
    _prompts_cache = {"document_types": {}, "default_type": "steel_technical"}
    return _prompts_cache

def get_document_types() -> List[Dict]:
    """
    利用可能な文書タイプのリストを取得

    Returns:
        文書タイプのリスト [{id, name, description}, ...]
    """
    prompts = load_prompts()
    document_types = []

    for type_id, type_info in prompts.get("document_types", {}).items():
        document_types.append({
            "id": type_id,
            "name": type_info.get("name", type_id),
            "description": type_info.get("description", "")
        })

    return document_types

def get_prompt_template(document_type: str, direction: str) -> Dict:
    """
    文書タイプと翻訳方向に応じたプロンプトテンプレートを取得

    Args:
        document_type: 文書タイプID
        direction: 翻訳方向 ("en-to-ja" または "ja-to-en")

    Returns:
        プロンプト情報 {"system": str, "prompt_template": str}
    """
    prompts = load_prompts()
    document_types = prompts.get("document_types", {})

    # 指定された文書タイプが存在しない場合はデフォルトを使用
    if document_type not in document_types:
        document_type = prompts.get("default_type", "steel_technical")

    type_info = document_types.get(document_type, {})

    # 翻訳方向のキー変換（"en-to-ja" → "en_to_ja"）
    direction_key = direction.replace("-", "_")

    prompt_info = type_info.get(direction_key, {})

    return {
        "system": prompt_info.get("system", ""),
        "prompt_template": prompt_info.get("prompt_template", "")
    }

def load_glossary_from_file() -> Dict[str, str]:
    """
    ファイルから用語集を読み込む

    Returns:
        用語集辞書
    """
    try:
        if GLOSSARY_FILE.exists():
            with open(GLOSSARY_FILE, 'r', encoding='utf-8') as f:
                glossary = json.load(f)
                logger.info(f"Loaded {len(glossary)} terms from glossary file")
                return glossary
    except Exception as e:
        logger.error(f"Error loading glossary: {e}")
    return {}

def save_glossary_to_file(glossary: Dict[str, str]) -> bool:
    """
    用語集をファイルに保存

    Args:
        glossary: 用語集辞書

    Returns:
        保存成功したかどうか
    """
    try:
        # ディレクトリが存在しない場合は作成
        GLOSSARY_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(GLOSSARY_FILE, 'w', encoding='utf-8') as f:
            json.dump(glossary, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(glossary)} terms to glossary file")
        return True
    except Exception as e:
        logger.error(f"Error saving glossary: {e}")
        return False


# ========== MLX Server 翻訳エンジン ==========

class MLXServerTranslator:
    """
    MLXサーバー (mlx_lm.server) を使用した翻訳エンジン
    OpenAI互換APIでQwen2.5-7B-Instruct-4bitモデルを利用
    Apple Silicon最適化
    """

    MODEL_NAME = "mlx-community/Qwen2.5-7B-Instruct-4bit"

    def __init__(self):
        """
        MLXサーバー翻訳エンジンの初期化
        """
        self.base_url = "http://localhost:8080"

        # 用語集の初期化
        self.glossary = load_glossary_from_file()

        # 進捗トラッキング用
        self.current_page = 0
        self.total_pages = 0
        self.is_cancelled = False

        # MLXサーバーが利用可能かチェック
        self.server_available = self._check_mlx_server()

        if self.server_available:
            logger.info(f"MLX Server Translator initialized ({self.base_url})")
        else:
            logger.warning("MLX Server is not available")

    def _check_mlx_server(self) -> bool:
        """
        MLXサーバーが利用可能かチェック
        """
        try:
            response = requests.get(
                f"{self.base_url}/v1/models",
                timeout=5,
                proxies={"http": None, "https": None}
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"MLX Server check failed: {e}")
            return False

    def translate_text(self, text: str, context: str = "", direction: str = "en-to-ja", document_type: str = "steel_technical") -> str:
        """
        MLXサーバーを使用してテキストを翻訳

        Args:
            text: 翻訳するテキスト
            context: 翻訳の文脈情報（オプション）
            direction: 翻訳方向 ("en-to-ja" または "ja-to-en")
            document_type: 文書タイプ（デフォルト: steel_technical）

        Returns:
            翻訳されたテキスト
        """
        if not text.strip():
            return ""

        if not self.server_available:
            # 再チェック（サーバーが後から起動された可能性）
            self.server_available = self._check_mlx_server()
            if not self.server_available:
                return f"[MLXサーバーに接続できません] {text}"

        # 用語集の適用情報を作成
        glossary_info = self._format_glossary_for_prompt(direction)

        # 文書タイプに応じたプロンプトテンプレートを取得
        prompt_info = get_prompt_template(document_type, direction)
        prompt_template = prompt_info.get("prompt_template", "")

        if prompt_template:
            prompt = prompt_template.format(glossary_info=glossary_info, text=text)
        else:
            # フォールバック: デフォルトのプロンプト
            if direction == "ja-to-en":
                prompt = f"""You are translating a technical document from Japanese to English.

CRITICAL RULES:
1. Output ONLY in English. NEVER output in Japanese or Chinese.
2. Maintain the technical accuracy and formatting.
3. Do NOT include any explanation or notes. Output ONLY the translation.{glossary_info}

Japanese Text:
{text}

English Translation:"""
            else:
                prompt = f"""You are translating a technical document from English to Japanese.

CRITICAL RULES:
1. Output ONLY in Japanese (日本語のみ). NEVER output Chinese (中文).
2. Maintain the technical accuracy and formatting.
3. Do NOT include any explanation or notes. Output ONLY the translation.{glossary_info}

English Text:
{text}

Japanese Translation (日本語訳):"""

        try:
            # OpenAI互換APIでリクエスト
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2048,
                    "top_p": 0.9,
                },
                timeout=180,
                proxies={"http": None, "https": None}
            )

            if response.status_code == 200:
                result = response.json()
                translated = result["choices"][0]["message"]["content"].strip()

                # 思考タグを除去
                translated = self._remove_think_tags(translated)

                return translated
            else:
                logger.error(f"MLX Server API error: {response.status_code} - {response.text}")
                return f"[翻訳エラー] {text}"

        except requests.exceptions.Timeout:
            logger.error("MLX Server request timed out")
            return f"[タイムアウト] {text}"
        except Exception as e:
            logger.error(f"MLX Server translation error: {e}")
            return f"[翻訳エラー] {text}"

    def translate_pages(self, pages_data: List[Dict], progress_callback=None, direction: str = "en-to-ja", document_type: str = "steel_technical") -> List[Dict]:
        """
        PDFページデータの翻訳

        Args:
            pages_data: ページごとのテキストデータ
            progress_callback: 進捗コールバック関数
            direction: 翻訳方向 ("en-to-ja" または "ja-to-en")
            document_type: 文書タイプ（デフォルト: steel_technical）

        Returns:
            翻訳されたページデータ
        """
        translated_pages = []
        self.total_pages = len(pages_data)
        self.current_page = 0
        self.is_cancelled = False

        for idx, page_data in enumerate(pages_data, start=1):
            if self.is_cancelled:
                logger.info(f"Translation cancelled at page {idx}/{self.total_pages}")
                break

            page_num = page_data.get("page", 0)
            self.current_page = idx

            logger.info(f"[MLX] Translating page {page_num} ({idx}/{self.total_pages}), direction: {direction}, doc_type: {document_type}...")

            if progress_callback:
                progress_callback(idx, self.total_pages, page_num)

            translated_page = {
                "page": page_num,
                "original_text": page_data.get("text", ""),
                "translated_text": ""
            }

            if page_data.get("text"):
                translated_page["translated_text"] = self.translate_text(
                    page_data["text"], direction=direction, document_type=document_type
                )

            translated_pages.append(translated_page)

        return translated_pages

    def get_progress(self) -> Dict:
        """現在の翻訳進捗を取得"""
        if self.total_pages == 0:
            return {"current": 0, "total": 0, "percentage": 0.0}

        percentage = ((self.current_page - 1) / self.total_pages) * 100
        return {
            "current": self.current_page,
            "total": self.total_pages,
            "percentage": round(max(0, percentage), 2)
        }

    def cancel_translation(self):
        """翻訳処理をキャンセル"""
        self.is_cancelled = True
        logger.info("MLX translation cancellation requested")

    def _remove_think_tags(self, text: str) -> str:
        """思考タグを除去"""
        result = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        result = result.replace('<think>', '').replace('</think>', '')
        return result.strip()

    def _format_glossary_for_prompt(self, direction: str = "en-to-ja") -> str:
        """用語集をプロンプト用にフォーマット"""
        if not self.glossary:
            return ""

        if direction == "ja-to-en":
            glossary_lines = [f"{ja} → {en}" for en, ja in self.glossary.items()]
        else:
            glossary_lines = [f"{en} → {ja}" for en, ja in self.glossary.items()]
        return f"\n\nUse these terminology translations:\n" + "\n".join(glossary_lines)

    def update_glossary(self, glossary: Dict[str, str]):
        """用語集を更新"""
        self.glossary = glossary
        save_glossary_to_file(self.glossary)
        logger.info(f"Glossary updated with {len(glossary)} terms")

    def add_glossary_term(self, english: str, japanese: str):
        """用語を追加"""
        self.glossary[english] = japanese
        save_glossary_to_file(self.glossary)
        logger.info(f"Added glossary term: {english} → {japanese}")

    def ask_question(self, question: str, context: str) -> str:
        """
        PDFの内容に関する質問に回答

        Args:
            question: ユーザーからの質問
            context: PDFから抽出されたテキスト

        Returns:
            AIからの回答
        """
        if not self.server_available:
            self.server_available = self._check_mlx_server()
            if not self.server_available:
                return "MLXサーバーに接続できません"

        # コンテキストが長すぎる場合は切り詰める
        max_context_length = 6000
        if len(context) > max_context_length:
            context = context[:max_context_length] + "\n...(以下省略)"

        prompt = f"""PDF文書の内容に基づいて質問に回答してください。

文書内容:
{context}

質問: {question}

回答（日本語で簡潔に）:"""

        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1024,
                    "top_p": 0.9,
                },
                timeout=60,
                proxies={"http": None, "https": None}
            )

            if response.status_code == 200:
                result = response.json()
                answer = result["choices"][0]["message"]["content"].strip()
                answer = self._remove_think_tags(answer)
                return answer
            else:
                return f"エラーが発生しました: {response.status_code}"

        except Exception as e:
            logger.error(f"MLX question error: {e}")
            return f"エラーが発生しました: {str(e)}"


# MLXサーバー翻訳エンジンのグローバルインスタンス
_mlx_translator = None


def get_mlx_status() -> Dict:
    """
    MLXサーバーの接続状態を取得

    Returns:
        ステータス情報
    """
    global _mlx_translator

    if _mlx_translator is not None:
        # 既存インスタンスがある場合、接続状態を再チェック
        _mlx_translator.server_available = _mlx_translator._check_mlx_server()
        return {
            "available": _mlx_translator.server_available,
            "model": MLXServerTranslator.MODEL_NAME,
            "base_url": _mlx_translator.base_url
        }
    else:
        # インスタンスがなくても接続チェックだけ行う
        try:
            response = requests.get(
                "http://localhost:8080/v1/models",
                timeout=5,
                proxies={"http": None, "https": None}
            )
            available = response.status_code == 200
        except Exception:
            available = False

        return {
            "available": available,
            "model": MLXServerTranslator.MODEL_NAME,
            "base_url": "http://localhost:8080"
        }


def get_mlx_progress_safe() -> Dict:
    """
    MLXトランスレータの生成を誘発せずに翻訳進捗を取得

    Returns:
        進捗情報
    """
    global _mlx_translator
    if _mlx_translator is not None:
        return _mlx_translator.get_progress()
    return {"current": 0, "total": 0, "percentage": 0}


def cancel_mlx_safe() -> bool:
    """
    MLXトランスレータの生成を誘発せずに翻訳をキャンセル

    Returns:
        キャンセルが実行されたかどうか
    """
    global _mlx_translator
    if _mlx_translator is not None:
        _mlx_translator.cancel_translation()
        return True
    return False


def get_mlx_translator() -> MLXServerTranslator:
    """
    MLXサーバー翻訳エンジンのインスタンスを取得

    Returns:
        MLXServerTranslatorインスタンス
    """
    global _mlx_translator

    if _mlx_translator is None:
        _mlx_translator = MLXServerTranslator()

    return _mlx_translator


# ========== Apple 翻訳エンジン ==========

class AppleTranslator:
    """
    AppleのTranslation framework (macOS 15+) を使用した軽量翻訳エンジン
    オフラインで動作可能（言語パックがダウンロード済みの場合）
    """

    def __init__(self):
        """
        Apple翻訳エンジンの初期化
        """
        logger.info("Initializing Apple Translator...")

        # 用語集の初期化
        self.glossary = load_glossary_from_file()

        # 進捗トラッキング用
        self.current_page = 0
        self.total_pages = 0
        self.is_cancelled = False

        # Swiftスクリプトのパス
        self.swift_script_path = Path(__file__).parent / "apple_translate.swift"

        # Apple Translation APIが利用可能かチェック
        self.apple_api_available = self._check_apple_api()

        if self.apple_api_available:
            logger.info("Apple Translation API is available (macOS 15+)")
        else:
            logger.warning("Apple Translation API not available. Will use fallback.")

        logger.info("Apple Translator initialized")

    def _check_apple_api(self) -> bool:
        """
        Apple Translation APIが利用可能かチェック
        """
        try:
            result = subprocess.run(
                ['sw_vers', '-productVersion'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                major_version = int(version.split('.')[0])
                return major_version >= 15
        except Exception as e:
            logger.warning(f"Failed to check macOS version: {e}")
        return False

    def translate_text(self, text: str, context: str = "", direction: str = "en-to-ja") -> str:
        """
        AppleのTranslation APIを使用してテキストを翻訳
        """
        if not text.strip():
            return ""

        try:
            text_with_markers, markers = self._apply_glossary_markers(text, direction)
            translated = self._translate_with_apple_api(text_with_markers, direction)
            translated = self._replace_markers_with_translations(translated, markers)
            translated = self._remove_extra_blank_lines(translated)
            return translated.strip()

        except Exception as e:
            logger.error(f"Apple translation error: {e}")
            return f"[翻訳エラー] {text}"

    def _translate_with_apple_api(self, text: str, direction: str = "en-to-ja") -> str:
        """Apple Translation APIを使用して翻訳"""
        max_length = 4000
        if len(text) > max_length:
            chunks = self._split_text(text, max_length)
            translated_chunks = []
            for chunk in chunks:
                translated_chunk = self._call_swift_translator(chunk, direction)
                translated_chunks.append(translated_chunk)
            return '\n'.join(translated_chunks)
        else:
            return self._call_swift_translator(text, direction)

    def _call_swift_translator(self, text: str, direction: str = "en-to-ja") -> str:
        """Swiftスクリプトを呼び出してApple Translation APIを使用"""
        if not self.apple_api_available:
            raise Exception("Apple Translation API is not available on this system")

        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(text)
                temp_file = f.name

            try:
                result = subprocess.run(
                    ['swift', str(self.swift_script_path), temp_file, direction],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env={**os.environ, 'LANG': 'en_US.UTF-8'}
                )

                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    logger.error(f"Swift translation error: {result.stderr}")
                    raise Exception(f"Translation failed: {result.stderr}")

            finally:
                os.unlink(temp_file)

        except subprocess.TimeoutExpired:
            raise Exception("Translation timed out")
        except Exception as e:
            raise Exception(f"Failed to call Swift translator: {e}")

    def _split_text(self, text: str, max_length: int) -> List[str]:
        """テキストを指定された最大長で分割"""
        chunks = []
        current_chunk = ""

        for line in text.split('\n'):
            if len(current_chunk) + len(line) + 1 <= max_length:
                current_chunk += line + '\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line + '\n'

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _apply_glossary_markers(self, text: str, direction: str = "en-to-ja") -> tuple:
        """用語集の用語をマーカーで置換"""
        markers = {}
        result = text

        for idx, (english, japanese) in enumerate(self.glossary.items()):
            marker = f"__GLOSSARY_{idx}__"

            if direction == "ja-to-en":
                if japanese in result:
                    result = result.replace(japanese, marker)
                    markers[marker] = english
            else:
                if english.lower() in result.lower():
                    pattern = re.compile(re.escape(english), re.IGNORECASE)
                    result = pattern.sub(marker, result)
                    markers[marker] = japanese

        return result, markers

    def _replace_markers_with_translations(self, text: str, markers: dict) -> str:
        """マーカーを用語集の翻訳に置換"""
        result = text
        for marker, translation in markers.items():
            result = result.replace(marker, translation)
        return result

    def translate_pages(self, pages_data: List[Dict], progress_callback=None, direction: str = "en-to-ja") -> List[Dict]:
        """PDFページデータの翻訳"""
        translated_pages = []
        self.total_pages = len(pages_data)
        self.current_page = 0
        self.is_cancelled = False

        for idx, page_data in enumerate(pages_data, start=1):
            if self.is_cancelled:
                logger.info(f"Translation cancelled at page {idx}/{self.total_pages}")
                break

            page_num = page_data.get("page", 0)
            self.current_page = idx

            logger.info(f"[Apple] Translating page {page_num} ({idx}/{self.total_pages}), direction: {direction}...")

            if progress_callback:
                progress_callback(idx, self.total_pages, page_num)

            translated_page = {
                "page": page_num,
                "original_text": page_data.get("text", ""),
                "translated_text": ""
            }

            if page_data.get("text"):
                translated_page["translated_text"] = self.translate_text(page_data["text"], direction=direction)

            translated_pages.append(translated_page)

        return translated_pages

    def get_progress(self) -> Dict:
        """現在の翻訳進捗を取得"""
        if self.total_pages == 0:
            return {"current": 0, "total": 0, "percentage": 0.0}

        percentage = ((self.current_page - 1) / self.total_pages) * 100
        return {
            "current": self.current_page,
            "total": self.total_pages,
            "percentage": round(max(0, percentage), 2)
        }

    def cancel_translation(self):
        """翻訳処理をキャンセル"""
        self.is_cancelled = True
        logger.info("Apple translation cancellation requested")

    def _remove_extra_blank_lines(self, text: str) -> str:
        """不要な空行を削除"""
        text = re.sub(r'\n{3,}', '\n\n', text)
        lines = text.split('\n')
        cleaned_lines = []
        prev_empty = False
        for line in lines:
            is_empty = len(line.strip()) == 0
            if is_empty:
                if not prev_empty:
                    cleaned_lines.append('')
                prev_empty = True
            else:
                cleaned_lines.append(line)
                prev_empty = False
        return '\n'.join(cleaned_lines)

    def update_glossary(self, glossary: Dict[str, str]):
        """用語集を更新"""
        self.glossary = glossary
        save_glossary_to_file(self.glossary)
        logger.info(f"Glossary updated with {len(glossary)} terms")

    def add_glossary_term(self, english: str, japanese: str):
        """用語を追加"""
        self.glossary[english] = japanese
        save_glossary_to_file(self.glossary)
        logger.info(f"Added glossary term: {english} → {japanese}")


# Apple翻訳エンジンのグローバルインスタンス
_apple_translator = None


def get_apple_progress_safe() -> Dict:
    """Appleトランスレータの生成を誘発せずに翻訳進捗を取得"""
    global _apple_translator
    if _apple_translator is not None:
        return _apple_translator.get_progress()
    return {"current": 0, "total": 0, "percentage": 0}


def cancel_apple_safe() -> bool:
    """Appleトランスレータの生成を誘発せずに翻訳をキャンセル"""
    global _apple_translator
    if _apple_translator is not None:
        _apple_translator.cancel_translation()
        return True
    return False


def get_apple_translator() -> AppleTranslator:
    """Apple翻訳エンジンのインスタンスを取得"""
    global _apple_translator

    if _apple_translator is None:
        _apple_translator = AppleTranslator()

    return _apple_translator
