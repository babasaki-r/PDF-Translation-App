import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import List, Dict
import logging
import json
import os
import gc
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


class SwallowTranslator:
    """
    Llama-3.1-Swallow-8B-Instruct-v0.5を使用した日英翻訳エンジン
    日本語に特化したLlamaベースのモデル
    """

    MODEL_NAME = "tokyotech-llm/Llama-3.1-Swallow-8B-Instruct-v0.5"

    def __init__(self, glossary: Dict[str, str] = None):
        """
        Swallow翻訳モデルの初期化

        Args:
            glossary: 用語集 {"英語": "日本語", ...}
        """
        logger.info(f"Loading Swallow model: {self.MODEL_NAME}")

        # Apple Siliconの場合、mpsデバイスを使用
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")

        # 用語集の初期化
        self.glossary = load_glossary_from_file()
        if glossary:
            self.glossary.update(glossary)
            save_glossary_to_file(self.glossary)

        # 進捗トラッキング用
        self.current_page = 0
        self.total_pages = 0
        self.is_cancelled = False

        # トークナイザーとモデルのロード
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.MODEL_NAME,
            trust_remote_code=True
        )

        # Apple Silicon用にfloat16で読み込み
        logger.info("Loading Swallow model with float16 precision")
        self.model = AutoModelForCausalLM.from_pretrained(
            self.MODEL_NAME,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
            trust_remote_code=True,
            use_cache=True,
        )

        # モデルをデバイスに移動
        self.model = self.model.to(self.device)
        self.model.eval()

        logger.info("Swallow model loaded successfully")

    def translate_text(self, text: str, context: str = "", direction: str = "en-to-ja", document_type: str = "steel_technical") -> str:
        """
        テキストを翻訳

        Args:
            text: 翻訳するテキスト
            context: 文脈情報（オプション）
            direction: 翻訳方向 ("en-to-ja" または "ja-to-en")
            document_type: 文書タイプ（デフォルト: steel_technical）

        Returns:
            翻訳されたテキスト
        """
        if not text.strip():
            return ""

        # 用語集の適用情報を作成
        glossary_info = self._format_glossary_for_prompt(direction)

        # 文書タイプに応じたプロンプトテンプレートを取得
        prompt_info = get_prompt_template(document_type, direction)
        prompt_template = prompt_info.get("prompt_template", "")

        if prompt_template:
            # プロンプトテンプレートを使用
            prompt = prompt_template.format(glossary_info=glossary_info, text=text)
        else:
            # フォールバック: デフォルトのプロンプト
            if direction == "ja-to-en":
                prompt = f"""以下の日本語テキストを英語に翻訳してください。技術文書として適切な英語を使用してください。{glossary_info}

日本語テキスト:
{text}

英語翻訳:"""
            else:
                prompt = f"""以下の英語テキストを日本語に翻訳してください。技術文書として適切な日本語を使用してください。{glossary_info}

英語テキスト:
{text}

日本語翻訳:"""

        messages = [
            {"role": "user", "content": prompt}
        ]

        # Swallowモデル用のチャットテンプレート適用
        inputs = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.device)

        # 生成設定
        gen_settings = {
            "max_new_tokens": 1536,
            "temperature": 0.1,
            "top_p": 0.9,
            "do_sample": False,
            "num_beams": 1,
        }

        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                **gen_settings,
                use_cache=True,
                pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
            )

        # 入力部分を除去して生成部分のみ取得
        response = self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)

        # メモリ解放
        del inputs, outputs
        self._clear_memory_cache()

        return response.strip()

    def translate_pages(self, pages_data: List[Dict], progress_callback=None, direction: str = "en-to-ja", document_type: str = "steel_technical") -> List[Dict]:
        """
        PDFページデータの翻訳

        Args:
            pages_data: ページごとのテキストデータ
            progress_callback: 進捗コールバック関数
            direction: 翻訳方向
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

            logger.info(f"[Swallow] Translating page {page_num} ({idx}/{self.total_pages}), direction: {direction}, doc_type: {document_type}...")

            if progress_callback:
                progress_callback(idx, self.total_pages, page_num)

            translated_page = {
                "page": page_num,
                "original_text": page_data.get("text", ""),
                "translated_text": ""
            }

            if page_data.get("text"):
                translated_page["translated_text"] = self.translate_text(
                    page_data["text"],
                    direction=direction,
                    document_type=document_type
                )

            translated_pages.append(translated_page)

            # 3ページごとにメモリを解放
            if idx % 3 == 0:
                self._clear_memory_cache()
                logger.info(f"Memory cache cleared after page {idx}")

        return translated_pages

    def get_progress(self) -> Dict:
        """現在の翻訳進捗を取得"""
        if self.total_pages == 0:
            return {"current": 0, "total": 0, "percentage": 0}

        # ページ処理開始時点の進捗を表示（例：5ページ中2ページ目開始時は20%）
        percentage = int(((self.current_page - 1) / self.total_pages) * 100)
        return {
            "current": self.current_page,
            "total": self.total_pages,
            "percentage": max(0, percentage)
        }

    def cancel_translation(self):
        """翻訳をキャンセル"""
        self.is_cancelled = True
        logger.info("Translation cancellation requested")

    def _format_glossary_for_prompt(self, direction: str = "en-to-ja") -> str:
        """用語集をプロンプト用にフォーマット"""
        if not self.glossary:
            return ""

        if direction == "ja-to-en":
            glossary_lines = [f"{ja} → {en}" for en, ja in self.glossary.items()]
        else:
            glossary_lines = [f"{en} → {ja}" for en, ja in self.glossary.items()]
        return f"\n\n以下の用語を使用してください:\n" + "\n".join(glossary_lines)

    def _clear_memory_cache(self):
        """GPUメモリキャッシュをクリア"""
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
            torch.mps.synchronize()
        gc.collect()

    def update_glossary(self, glossary: Dict[str, str]):
        """用語集を更新"""
        self.glossary = glossary
        save_glossary_to_file(self.glossary)
        logger.info(f"Glossary updated with {len(glossary)} terms")

    def unload_model(self):
        """モデルをメモリから解放"""
        if hasattr(self, 'model'):
            del self.model
        if hasattr(self, 'tokenizer'):
            del self.tokenizer

        if torch.backends.mps.is_available():
            torch.mps.empty_cache()

        gc.collect()
        logger.info("Swallow model unloaded")


# Swallow翻訳エンジンのシングルトンインスタンス
_swallow_translator = None
_swallow_loading = False  # ロード中フラグ
_swallow_load_error = None  # ロードエラー


def get_swallow_status() -> Dict:
    """
    Swallowモデルのロード状態を取得

    Returns:
        ステータス情報 {"loaded": bool, "loading": bool, "error": str|None}
    """
    global _swallow_translator, _swallow_loading, _swallow_load_error

    return {
        "loaded": _swallow_translator is not None,
        "loading": _swallow_loading,
        "error": _swallow_load_error
    }


def get_swallow_translator() -> SwallowTranslator:
    """
    Swallow翻訳エンジンのインスタンスを取得

    Returns:
        SwallowTranslatorインスタンス
    """
    global _swallow_translator, _swallow_loading, _swallow_load_error

    if _swallow_translator is None:
        if _swallow_loading:
            raise Exception("Swallow model is currently loading. Please wait.")

        _swallow_loading = True
        _swallow_load_error = None
        try:
            logger.info("Creating new Swallow translator instance")
            _swallow_translator = SwallowTranslator()
            logger.info("Swallow translator loaded successfully")
        except Exception as e:
            _swallow_load_error = str(e)
            logger.error(f"Failed to load Swallow translator: {e}")
            raise
        finally:
            _swallow_loading = False

    return _swallow_translator


def unload_swallow_translator():
    """
    Swallowモデルをメモリから解放
    エンジン切り替え時に呼び出される
    """
    global _swallow_translator, _swallow_loading, _swallow_load_error

    if _swallow_translator is not None:
        logger.info("Unloading Swallow translator...")
        _swallow_translator.unload_model()
        _swallow_translator = None
        _swallow_load_error = None
        logger.info("Swallow translator unloaded")
        return True
    return False


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
            # macOSバージョンをチェック
            result = subprocess.run(
                ['sw_vers', '-productVersion'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                major_version = int(version.split('.')[0])
                # macOS 15 (Sequoia) 以降が必要
                return major_version >= 15
        except Exception as e:
            logger.warning(f"Failed to check macOS version: {e}")
        return False

    def translate_text(self, text: str, context: str = "", direction: str = "en-to-ja") -> str:
        """
        AppleのTranslation APIを使用してテキストを翻訳

        Args:
            text: 翻訳するテキスト
            context: 翻訳の文脈情報（オプション、未使用）
            direction: 翻訳方向 ("en-to-ja" または "ja-to-en")

        Returns:
            翻訳されたテキスト
        """
        if not text.strip():
            return ""

        try:
            # 用語集の前処理：テキスト内の用語を一時的にマーカーで置換
            text_with_markers, markers = self._apply_glossary_markers(text, direction)

            # Apple Translation APIで翻訳
            translated = self._translate_with_apple_api(text_with_markers, direction)

            # マーカーを用語集の翻訳に置換
            translated = self._replace_markers_with_translations(translated, markers)

            # 不要な空行を削除（連続する空行を1つに、先頭・末尾の空行を除去）
            translated = self._remove_extra_blank_lines(translated)

            return translated.strip()

        except Exception as e:
            logger.error(f"Apple translation error: {e}")
            # フォールバック: 元のテキストを返す
            return f"[翻訳エラー] {text}"

    def _translate_with_apple_api(self, text: str, direction: str = "en-to-ja") -> str:
        """
        Apple Translation APIを使用して翻訳

        Args:
            text: 翻訳するテキスト
            direction: 翻訳方向 ("en-to-ja" または "ja-to-en")

        Returns:
            翻訳されたテキスト
        """
        # テキストが長い場合は分割して翻訳
        max_length = 4000  # 安全なサイズ
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
        """
        Swiftスクリプトを呼び出してApple Translation APIを使用

        Args:
            text: 翻訳するテキスト
            direction: 翻訳方向 ("en-to-ja" または "ja-to-en")

        Returns:
            翻訳されたテキスト
        """
        if not self.apple_api_available:
            raise Exception("Apple Translation API is not available on this system")

        try:
            # 一時ファイルにテキストを書き込む（長いテキスト対応）
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(text)
                temp_file = f.name

            try:
                # Swiftスクリプトを実行（翻訳方向を引数として渡す）
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
                # 一時ファイルを削除
                os.unlink(temp_file)

        except subprocess.TimeoutExpired:
            raise Exception("Translation timed out")
        except Exception as e:
            raise Exception(f"Failed to call Swift translator: {e}")

    def _split_text(self, text: str, max_length: int) -> List[str]:
        """
        テキストを指定された最大長で分割

        Args:
            text: 分割するテキスト
            max_length: 最大文字数

        Returns:
            分割されたテキストのリスト
        """
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
        """
        用語集の用語をマーカーで置換

        Args:
            text: 元のテキスト
            direction: 翻訳方向 ("en-to-ja" または "ja-to-en")

        Returns:
            (マーカー付きテキスト, マーカー辞書)
        """
        markers = {}
        result = text

        for idx, (english, japanese) in enumerate(self.glossary.items()):
            marker = f"__GLOSSARY_{idx}__"

            if direction == "ja-to-en":
                # 日→英の場合、日本語をマーカーに置換し、英語に変換
                if japanese in result:
                    result = result.replace(japanese, marker)
                    markers[marker] = english
            else:
                # 英→日の場合、英語をマーカーに置換し、日本語に変換
                if english.lower() in result.lower():
                    import re
                    pattern = re.compile(re.escape(english), re.IGNORECASE)
                    result = pattern.sub(marker, result)
                    markers[marker] = japanese

        return result, markers

    def _replace_markers_with_translations(self, text: str, markers: dict) -> str:
        """
        マーカーを用語集の日本語訳に置換

        Args:
            text: マーカー付きテキスト
            markers: マーカー辞書

        Returns:
            置換後のテキスト
        """
        result = text
        for marker, japanese in markers.items():
            result = result.replace(marker, japanese)
        return result

    def translate_pages(self, pages_data: List[Dict], progress_callback=None, direction: str = "en-to-ja") -> List[Dict]:
        """
        PDFページデータの翻訳

        Args:
            pages_data: ページごとのテキストデータ
            progress_callback: 進捗コールバック関数
            direction: 翻訳方向 ("en-to-ja" または "ja-to-en")

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

        # ページ処理開始時点の進捗を表示（例：5ページ中2ページ目開始時は20%）
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
        """
        不要な空行を削除
        - 連続する空行を1つに圧縮
        - 段落間の改行は保持
        """
        import re
        # 3つ以上の連続する改行を2つに圧縮（段落間の空行は1つ保持）
        text = re.sub(r'\n{3,}', '\n\n', text)
        # 行頭・行末の空白のみの行を削除
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


def get_apple_translator() -> AppleTranslator:
    """
    Apple翻訳エンジンのインスタンスを取得

    Returns:
        Apple翻訳エンジンインスタンス
    """
    global _apple_translator

    if _apple_translator is None:
        _apple_translator = AppleTranslator()

    return _apple_translator


class OllamaTranslator:
    """
    Ollamaを使用した翻訳エンジン
    ローカルで動作するLLMを使用してメモリ効率的に翻訳
    """

    # 利用可能なモデル定義
    MODELS = {
        "qwen3:4b-instruct": {
            "name": "Qwen3 4B",
            "description": "高速・軽量（推奨）",
            "size": "2.5GB"
        },
        "qwen2.5:7b-instruct": {
            "name": "Qwen2.5 7B",
            "description": "バランス型",
            "size": "4.7GB"
        },
        "llama3.1:8b": {
            "name": "Llama 3.1 8B",
            "description": "汎用モデル",
            "size": "4.9GB"
        },
        "qwen3-vl:8b-instruct": {
            "name": "Qwen3-VL 8B",
            "description": "視覚対応モデル",
            "size": "6.1GB"
        },
        "qwen3:14b": {
            "name": "Qwen3 14B",
            "description": "高品質",
            "size": "9.3GB"
        },
        "qwen2.5:14b": {
            "name": "Qwen2.5 14B",
            "description": "高品質",
            "size": "9.0GB"
        }
    }

    # デフォルトモデル
    DEFAULT_MODEL = "qwen3:4b-instruct"

    def __init__(self, model: str = None):
        """
        Ollama翻訳エンジンの初期化

        Args:
            model: 使用するモデル名
        """
        self.model = model or self.DEFAULT_MODEL
        self.base_url = "http://localhost:11434"

        # 用語集の初期化
        self.glossary = load_glossary_from_file()

        # 進捗トラッキング用
        self.current_page = 0
        self.total_pages = 0
        self.is_cancelled = False

        # Ollamaが利用可能かチェック
        self.ollama_available = self._check_ollama()

        if self.ollama_available:
            logger.info(f"Ollama Translator initialized with model: {self.model}")
        else:
            logger.warning("Ollama is not available")

    def _check_ollama(self) -> bool:
        """
        Ollamaが利用可能かチェック
        """
        import requests
        try:
            # プロキシを無効化してローカル接続
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
                proxies={"http": None, "https": None}
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama check failed: {e}")
            return False

    def get_available_models(self) -> List[Dict]:
        """
        利用可能なOllamaモデルを取得
        """
        import requests
        try:
            # プロキシを無効化してローカル接続
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
                proxies={"http": None, "https": None}
            )
            if response.status_code == 200:
                data = response.json()
                models = []
                for model in data.get("models", []):
                    model_name = model.get("name", "")
                    model_info = self.MODELS.get(model_name, {
                        "name": model_name,
                        "description": "カスタムモデル",
                        "size": f"{model.get('size', 0) / 1e9:.1f}GB"
                    })
                    models.append({
                        "id": model_name,
                        "name": model_info.get("name", model_name),
                        "description": model_info.get("description", ""),
                        "size": model_info.get("size", "不明")
                    })
                return models
        except Exception as e:
            logger.error(f"Failed to get Ollama models: {e}")
        return []

    def set_model(self, model: str):
        """
        使用するモデルを変更
        """
        self.model = model
        logger.info(f"Ollama model changed to: {model}")

    def translate_text(self, text: str, context: str = "", direction: str = "en-to-ja", document_type: str = "steel_technical") -> str:
        """
        Ollamaを使用してテキストを翻訳

        Args:
            text: 翻訳するテキスト
            context: 翻訳の文脈情報（オプション）
            direction: 翻訳方向 ("en-to-ja" または "ja-to-en")
            document_type: 文書タイプ（デフォルト: steel_technical）

        Returns:
            翻訳されたテキスト
        """
        import requests

        if not text.strip():
            return ""

        if not self.ollama_available:
            return f"[Ollamaが利用できません] {text}"

        # 用語集の適用情報を作成
        glossary_info = self._format_glossary_for_prompt(direction)

        # 文書タイプに応じたプロンプトテンプレートを取得
        prompt_info = get_prompt_template(document_type, direction)
        prompt_template = prompt_info.get("prompt_template", "")

        if prompt_template:
            # プロンプトテンプレートを使用
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
            # プロキシを無効化してローカル接続
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 2048
                    }
                },
                timeout=120,
                proxies={"http": None, "https": None}
            )

            if response.status_code == 200:
                result = response.json()
                translated = result.get("response", "").strip()

                # 思考タグを除去
                translated = self._remove_think_tags(translated)

                return translated
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return f"[翻訳エラー] {text}"

        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            return f"[タイムアウト] {text}"
        except Exception as e:
            logger.error(f"Ollama translation error: {e}")
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

            logger.info(f"[Ollama] Translating page {page_num} ({idx}/{self.total_pages}), direction: {direction}, doc_type: {document_type}...")

            if progress_callback:
                progress_callback(idx, self.total_pages, page_num)

            translated_page = {
                "page": page_num,
                "original_text": page_data.get("text", ""),
                "translated_text": ""
            }

            if page_data.get("text"):
                translated_page["translated_text"] = self.translate_text(page_data["text"], direction=direction, document_type=document_type)

            translated_pages.append(translated_page)

        return translated_pages

    def get_progress(self) -> Dict:
        """現在の翻訳進捗を取得"""
        if self.total_pages == 0:
            return {"current": 0, "total": 0, "percentage": 0.0}

        # ページ処理開始時点の進捗を表示（例：5ページ中2ページ目開始時は20%）
        percentage = ((self.current_page - 1) / self.total_pages) * 100
        return {
            "current": self.current_page,
            "total": self.total_pages,
            "percentage": round(max(0, percentage), 2)
        }

    def cancel_translation(self):
        """翻訳処理をキャンセル"""
        self.is_cancelled = True
        logger.info("Ollama translation cancellation requested")

    def _remove_think_tags(self, text: str) -> str:
        """思考タグを除去"""
        import re
        result = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        result = result.replace('<think>', '').replace('</think>', '')
        return result.strip()

    def _format_glossary_for_prompt(self, direction: str = "en-to-ja") -> str:
        """用語集をプロンプト用にフォーマット"""
        if not self.glossary:
            return ""

        if direction == "ja-to-en":
            # 日→英の場合は逆方向（日本語→英語）
            glossary_lines = [f"{ja} → {en}" for en, ja in self.glossary.items()]
        else:
            # 英→日の場合（デフォルト）
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
        import requests

        if not self.ollama_available:
            return "Ollamaが利用できません"

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
            # プロキシを無効化してローカル接続
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 1024
                    }
                },
                timeout=60,
                proxies={"http": None, "https": None}
            )

            if response.status_code == 200:
                result = response.json()
                answer = result.get("response", "").strip()
                answer = self._remove_think_tags(answer)
                return answer
            else:
                return f"エラーが発生しました: {response.status_code}"

        except Exception as e:
            logger.error(f"Ollama question error: {e}")
            return f"エラーが発生しました: {str(e)}"


# Ollama翻訳エンジンのグローバルインスタンス
_ollama_translator = None


def get_ollama_translator(model: str = None) -> OllamaTranslator:
    """
    Ollama翻訳エンジンのインスタンスを取得

    Args:
        model: 使用するモデル名（Noneの場合はデフォルト）

    Returns:
        Ollama翻訳エンジンインスタンス
    """
    global _ollama_translator

    if _ollama_translator is None:
        _ollama_translator = OllamaTranslator(model=model)
    elif model and _ollama_translator.model != model:
        _ollama_translator.set_model(model)

    return _ollama_translator
