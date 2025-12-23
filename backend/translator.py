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


class Qwen3Translator:
    """Qwen3-14Bを使用した技術文書翻訳エンジン"""

    # モデル定義
    MODELS = {
        "high": "Qwen/Qwen3-14B",      # 高品質 (28GB)
        "balanced": "Qwen/Qwen2.5-7B-Instruct",  # バランス (14GB) - 旧7Bを昇格
        "fast": "Qwen/Qwen2.5-3B-Instruct"       # 高速 (6GB) - より小さく高速
    }

    # 品質設定
    QUALITY_SETTINGS = {
        "high": {
            "max_new_tokens": 2048,
            "temperature": 0.1,
            "top_p": 0.95,
            "do_sample": False,
            "num_beams": 1,
        },
        "balanced": {
            "max_new_tokens": 1536,
            "temperature": 0.2,
            "top_p": 0.9,
            "do_sample": False,
            "num_beams": 1,
        },
        "fast": {
            "max_new_tokens": 512,  # 3Bモデル用に最適化
            "temperature": 0.2,
            "top_p": 0.9,
            "do_sample": False,
            "num_beams": 1,
        }
    }

    def __init__(self, quality: str = "balanced", glossary: Dict[str, str] = None):
        """
        Qwen翻訳モデルの初期化
        M4 Pro Mac mini (Apple Silicon)に最適化

        Args:
            quality: 翻訳品質 ("high", "balanced", "fast")
            glossary: 用語集 {"英語": "日本語", ...}
        """
        self.quality = quality if quality in self.MODELS else "balanced"
        model_name = self.MODELS[self.quality]

        logger.info(f"Loading model: {model_name} (quality: {self.quality})")

        # Apple Siliconの場合、mpsデバイスを使用
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")

        # 用語集の初期化（ファイルから読み込み + 引数で渡された用語）
        self.glossary = load_glossary_from_file()
        if glossary:
            self.glossary.update(glossary)
            save_glossary_to_file(self.glossary)

        # 進捗トラッキング用
        self.current_page = 0
        self.total_pages = 0
        self.progress_callback = None
        self.is_cancelled = False

        # トークナイザーとモデルのロード
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )

        # Apple Silicon (MPS) では8bit量子化が未サポートのため、float16を使用
        # メモリ効率化のためlow_cpu_mem_usageを有効化
        logger.info(f"Loading model with float16 precision ({self.quality} mode)")
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,  # メモリ効率化
            trust_remote_code=True,
            use_cache=True,  # KV Cacheを有効化して生成速度を向上
        )

        # モデルをデバイスに移動
        self.model = self.model.to(self.device)
        self.model.eval()

        # 注意: BetterTransformerとtorch.compile()はメモリを大量に消費するため無効化
        # これによりメモリ使用量を大幅に削減
        logger.info("Skipping BetterTransformer and torch.compile() to reduce memory usage")

        logger.info("Model loaded and optimized successfully")

    def translate_text(self, text: str, context: str = "") -> str:
        """
        単一テキストの翻訳

        Args:
            text: 翻訳するテキスト
            context: 翻訳の文脈情報（オプション）

        Returns:
            翻訳されたテキスト
        """
        if not text.strip():
            return ""

        # 用語集の適用情報を作成
        glossary_info = self._format_glossary_for_prompt()

        # 鉄鋼業設備技術文書専用の翻訳プロンプト
        prompt = f"""You are translating a steel industry equipment technical specification document from English to Japanese.

CRITICAL RULES:
1. Output ONLY in Japanese (日本語のみ). NEVER output Chinese (中文).
2. This is a technical document about steel manufacturing equipment.
3. Use appropriate Japanese technical terminology for steel industry.
4. Maintain the technical accuracy and formatting.{glossary_info}

English Text:
{text}

Japanese Translation (日本語訳):"""

        # システムプロンプトで日本語出力を強制
        system_content = """You are a specialized technical translator for steel industry equipment documentation.
IMPORTANT: You MUST output ONLY in Japanese (日本語). Do NOT output in Chinese (中文).
Translate directly without explanation. Do NOT use <think> tags.
Output only the final Japanese translation."""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt}
        ]

        # テキスト生成
        text_input = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        model_inputs = self.tokenizer([text_input], return_tensors="pt").to(self.device)

        # 品質設定を取得
        gen_settings = self.QUALITY_SETTINGS[self.quality]

        # torch.inference_mode()はno_grad()より高速
        with torch.inference_mode():
            generated_ids = self.model.generate(
                **model_inputs,
                **gen_settings,
                use_cache=True,  # KV Cacheを明示的に有効化
                pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
            )

        generated_ids = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

        # Qwen3の思考タグを除去
        response = self._remove_think_tags(response)

        # 文字化け修正: (cid127) → ・
        response = self._fix_encoding_issues(response)

        # メモリ解放
        del model_inputs, generated_ids
        self._clear_memory_cache()

        return response.strip()

    def translate_batch(self, texts: List[str], context: str = "") -> List[str]:
        """
        複数テキストのバッチ翻訳

        Args:
            texts: 翻訳するテキストのリスト
            context: 翻訳の文脈情報（オプション）

        Returns:
            翻訳されたテキストのリスト
        """
        translations = []
        for text in texts:
            translation = self.translate_text(text, context)
            translations.append(translation)

        return translations

    def translate_pages(self, pages_data: List[Dict], progress_callback=None) -> List[Dict]:
        """
        PDFページデータの翻訳

        Args:
            pages_data: ページごとのテキストデータ
                [{"page": 1, "text": "..."}, ...]
            progress_callback: 進捗コールバック関数 callback(current, total, page_num)

        Returns:
            翻訳されたページデータ
        """
        translated_pages = []
        self.total_pages = len(pages_data)
        self.current_page = 0
        self.is_cancelled = False

        for idx, page_data in enumerate(pages_data, start=1):
            # キャンセルチェック
            if self.is_cancelled:
                logger.info(f"Translation cancelled at page {idx}/{self.total_pages}")
                break

            page_num = page_data.get("page", 0)
            self.current_page = idx

            logger.info(f"Translating page {page_num} ({idx}/{self.total_pages})...")

            # 進捗コールバック実行
            if progress_callback:
                progress_callback(idx, self.total_pages, page_num)

            translated_page = {
                "page": page_num,
                "original_text": page_data.get("text", ""),
                "translated_text": ""
            }

            # ページ全体のテキストを翻訳
            if page_data.get("text"):
                translated_page["translated_text"] = self.translate_text(
                    page_data["text"],
                    context="Steel industry equipment specification document"
                )

            translated_pages.append(translated_page)

            # 5ページごとにメモリを積極的に解放
            if idx % 5 == 0:
                self._clear_memory_cache()
                logger.info(f"Memory cache cleared after page {idx}")

        # 最後にもメモリ解放
        self._clear_memory_cache()

        return translated_pages

    def get_progress(self) -> Dict:
        """
        現在の翻訳進捗を取得

        Returns:
            進捗情報 {"current": int, "total": int, "percentage": float}
        """
        if self.total_pages == 0:
            return {"current": 0, "total": 0, "percentage": 0.0}

        percentage = (self.current_page / self.total_pages) * 100
        return {
            "current": self.current_page,
            "total": self.total_pages,
            "percentage": round(percentage, 2)
        }

    def cancel_translation(self):
        """
        翻訳処理をキャンセル
        """
        self.is_cancelled = True
        logger.info("Translation cancellation requested")

    def _remove_think_tags(self, text: str) -> str:
        """
        Qwen3の思考タグを除去

        Args:
            text: 処理するテキスト

        Returns:
            思考タグを除去したテキスト
        """
        import re

        # <think>...</think> タグとその内容を除去
        result = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

        # 残った単独の開始・終了タグを除去
        result = result.replace('<think>', '').replace('</think>', '')

        return result

    def _fix_encoding_issues(self, text: str) -> str:
        """
        文字化け修正

        Args:
            text: 修正するテキスト

        Returns:
            修正後のテキスト
        """
        # (cid127)などの文字化けを修正
        replacements = {
            "(cid127)": "・",
            "(cid:127)": "・",
            "•": "・",  # 英語の箇条書き記号も統一
        }

        result = text
        for old, new in replacements.items():
            result = result.replace(old, new)

        return result

    def _format_glossary_for_prompt(self) -> str:
        """
        用語集をプロンプト用にフォーマット

        Returns:
            フォーマットされた用語集情報
        """
        if not self.glossary:
            return ""

        glossary_lines = [f"{en} → {ja}" for en, ja in self.glossary.items()]
        return f"\n\nUse these terminology translations:\n" + "\n".join(glossary_lines)

    def _clear_memory_cache(self):
        """
        GPUメモリキャッシュをクリア
        """
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
            torch.mps.synchronize()
        gc.collect()

    def update_glossary(self, glossary: Dict[str, str]):
        """
        用語集を更新

        Args:
            glossary: 新しい用語集
        """
        self.glossary = glossary
        save_glossary_to_file(self.glossary)
        logger.info(f"Glossary updated with {len(glossary)} terms")

    def add_glossary_term(self, english: str, japanese: str):
        """
        用語を追加

        Args:
            english: 英語の用語
            japanese: 日本語の訳語
        """
        self.glossary[english] = japanese
        save_glossary_to_file(self.glossary)
        logger.info(f"Added glossary term: {english} → {japanese}")

    def ask_question(self, question: str, context: str) -> str:
        """
        PDFの内容に関する質問に回答

        Args:
            question: ユーザーからの質問
            context: PDFから抽出されたテキスト（質問の文脈として使用）

        Returns:
            AIからの回答
        """
        # コンテキストが長すぎる場合は切り詰める（トークン制限対策）
        max_context_length = 6000
        if len(context) > max_context_length:
            context = context[:max_context_length] + "\n...(以下省略)"

        prompt = f"""PDF文書の内容に基づいて質問に回答してください。

文書内容:
{context}

質問: {question}

回答:"""

        system_content = """技術文書に関する質問に回答するアシスタントです。日本語で簡潔に回答してください。"""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt}
        ]

        # テキスト生成
        text_input = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        model_inputs = self.tokenizer([text_input], return_tensors="pt").to(self.device)

        # 質問回答用の設定
        gen_settings = {
            "max_new_tokens": 1024,
            "temperature": 0.7,
            "top_p": 0.9,
            "do_sample": False,
            "num_beams": 1,
        }

        with torch.inference_mode():
            generated_ids = self.model.generate(
                **model_inputs,
                **gen_settings,
                use_cache=True,
                pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
            )

        generated_ids = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        response = self._remove_think_tags(response)

        # メモリ解放
        del model_inputs, generated_ids
        self._clear_memory_cache()

        return response.strip()

    def unload_model(self):
        """
        モデルをメモリから解放
        """
        import gc

        if hasattr(self, 'model'):
            del self.model
        if hasattr(self, 'tokenizer'):
            del self.tokenizer

        # メモリキャッシュをクリア
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()

        gc.collect()
        logger.info(f"Model unloaded for quality: {self.quality}")


# グローバルインスタンス管理（1つのみメモリに保持）
_current_translator = None
_current_quality = "fast"  # デフォルトを最軽量モデル(3B)に変更してメモリ使用量を削減


def get_translator(quality: str = None) -> Qwen3Translator:
    """
    翻訳エンジンのインスタンスを取得
    品質変更時に古いモデルをアンロード

    Args:
        quality: 翻訳品質 ("high", "balanced", "fast")
                 Noneの場合は現在の品質設定を使用

    Returns:
        翻訳エンジンインスタンス
    """
    global _current_translator, _current_quality

    if quality is None:
        quality = _current_quality

    # 有効な品質設定かチェック
    if quality not in Qwen3Translator.MODELS:
        quality = "balanced"

    # 品質が変更された場合、古いモデルをアンロード
    if _current_translator is not None and _current_quality != quality:
        logger.info(f"Quality changed from {_current_quality} to {quality}, unloading old model...")
        _current_translator.unload_model()
        _current_translator = None

    # 新しいインスタンスを作成
    if _current_translator is None or _current_quality != quality:
        logger.info(f"Creating new translator instance for quality: {quality}")
        _current_translator = Qwen3Translator(quality=quality)
        _current_quality = quality

    return _current_translator


def set_quality(quality: str):
    """
    デフォルト品質設定を変更

    Args:
        quality: 翻訳品質 ("high", "balanced", "fast")
    """
    global _current_quality
    if quality in Qwen3Translator.MODELS:
        _current_quality = quality
        logger.info(f"Default quality set to: {quality}")
    else:
        logger.warning(f"Invalid quality: {quality}. Keeping current: {_current_quality}")


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

    def translate_text(self, text: str, context: str = "") -> str:
        """
        AppleのTranslation APIを使用してテキストを翻訳

        Args:
            text: 翻訳するテキスト
            context: 翻訳の文脈情報（オプション、未使用）

        Returns:
            翻訳されたテキスト
        """
        if not text.strip():
            return ""

        try:
            # 用語集の前処理：テキスト内の用語を一時的にマーカーで置換
            text_with_markers, markers = self._apply_glossary_markers(text)

            # Apple Translation APIで翻訳
            translated = self._translate_with_apple_api(text_with_markers)

            # マーカーを用語集の日本語訳に置換
            translated = self._replace_markers_with_translations(translated, markers)

            return translated.strip()

        except Exception as e:
            logger.error(f"Apple translation error: {e}")
            # フォールバック: 元のテキストを返す
            return f"[翻訳エラー] {text}"

    def _translate_with_apple_api(self, text: str) -> str:
        """
        Apple Translation APIを使用して翻訳

        Args:
            text: 翻訳するテキスト

        Returns:
            翻訳されたテキスト
        """
        # テキストが長い場合は分割して翻訳
        max_length = 4000  # 安全なサイズ
        if len(text) > max_length:
            chunks = self._split_text(text, max_length)
            translated_chunks = []
            for chunk in chunks:
                translated_chunk = self._call_swift_translator(chunk)
                translated_chunks.append(translated_chunk)
            return '\n'.join(translated_chunks)
        else:
            return self._call_swift_translator(text)

    def _call_swift_translator(self, text: str) -> str:
        """
        Swiftスクリプトを呼び出してApple Translation APIを使用

        Args:
            text: 翻訳するテキスト

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
                # Swiftスクリプトを実行
                result = subprocess.run(
                    ['swift', str(self.swift_script_path), temp_file],
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

    def _apply_glossary_markers(self, text: str) -> tuple:
        """
        用語集の用語をマーカーで置換

        Args:
            text: 元のテキスト

        Returns:
            (マーカー付きテキスト, マーカー辞書)
        """
        markers = {}
        result = text

        for idx, (english, japanese) in enumerate(self.glossary.items()):
            marker = f"__GLOSSARY_{idx}__"
            if english.lower() in result.lower():
                # 大文字小文字を無視して置換
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

    def translate_pages(self, pages_data: List[Dict], progress_callback=None) -> List[Dict]:
        """
        PDFページデータの翻訳

        Args:
            pages_data: ページごとのテキストデータ
            progress_callback: 進捗コールバック関数

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

            logger.info(f"[Apple] Translating page {page_num} ({idx}/{self.total_pages})...")

            if progress_callback:
                progress_callback(idx, self.total_pages, page_num)

            translated_page = {
                "page": page_num,
                "original_text": page_data.get("text", ""),
                "translated_text": ""
            }

            if page_data.get("text"):
                translated_page["translated_text"] = self.translate_text(page_data["text"])

            translated_pages.append(translated_page)

        return translated_pages

    def get_progress(self) -> Dict:
        """現在の翻訳進捗を取得"""
        if self.total_pages == 0:
            return {"current": 0, "total": 0, "percentage": 0.0}

        percentage = (self.current_page / self.total_pages) * 100
        return {
            "current": self.current_page,
            "total": self.total_pages,
            "percentage": round(percentage, 2)
        }

    def cancel_translation(self):
        """翻訳処理をキャンセル"""
        self.is_cancelled = True
        logger.info("Apple translation cancellation requested")

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
