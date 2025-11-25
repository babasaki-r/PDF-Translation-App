import logging
from typing import List, Dict
from mlx_lm import load, generate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QwenMLXTranslator:
    """MLXフレームワークを使用したQwen翻訳エンジン (Apple Silicon最適化)"""

    # モデル定義 (MLX Community量子化モデル)
    # 8bit版を使用（4bitより互換性が高い）
    MODELS = {
        "high": "mlx-community/Qwen2.5-14B-Instruct-8bit",      # 高品質 8bit量子化
        "balanced": "mlx-community/Qwen2.5-7B-Instruct-8bit",  # バランス 8bit量子化
        "fast": "mlx-community/Qwen2.5-3B-Instruct-8bit"       # 高速 8bit量子化
    }

    # 品質設定
    QUALITY_SETTINGS = {
        "high": {
            "max_tokens": 2048,
            "temperature": 0.1,
            "top_p": 0.95,
        },
        "balanced": {
            "max_tokens": 1536,
            "temperature": 0.2,
            "top_p": 0.9,
        },
        "fast": {
            "max_tokens": 512,
            "temperature": 0.2,
            "top_p": 0.9,
        }
    }

    def __init__(self, quality: str = "balanced", glossary: Dict[str, str] = None):
        """
        MLX Qwen翻訳モデルの初期化
        Apple Silicon M4 Pro専用最適化

        Args:
            quality: 翻訳品質 ("high", "balanced", "fast")
            glossary: 用語集 {"英語": "日本語", ...}
        """
        self.quality = quality if quality in self.MODELS else "balanced"
        model_name = self.MODELS[self.quality]

        logger.info(f"Loading MLX model: {model_name} (quality: {self.quality})")

        # 用語集の初期化
        self.glossary = glossary or {}

        # 進捗トラッキング用
        self.current_page = 0
        self.total_pages = 0
        self.is_cancelled = False

        # MLXモデルとトークナイザーのロード
        try:
            # trust_remote_code=Trueを指定してロード
            self.model, self.tokenizer = load(model_name, tokenizer_config={"trust_remote_code": True})
            logger.info("MLX model loaded successfully with 4-bit quantization")
        except Exception as e:
            logger.error(f"Failed to load MLX model: {e}")
            raise

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

        # シンプルな翻訳プロンプト
        prompt = f"""Translate the following English text to Japanese. Output ONLY the Japanese translation, nothing else.{glossary_info}

English:
{text}

Japanese:"""

        # 品質設定を取得
        gen_settings = self.QUALITY_SETTINGS[self.quality]

        # MLXで生成
        try:
            response = generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=gen_settings["max_tokens"],
                temp=gen_settings["temperature"],
                top_p=gen_settings["top_p"],
                verbose=False
            )

            # 思考タグを除去
            response = self._remove_think_tags(response)

            # 文字化け修正
            response = self._fix_encoding_issues(response)

            return response.strip()

        except Exception as e:
            logger.error(f"Translation error: {e}")
            return ""

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
            # キャンセルチェック
            if self.is_cancelled:
                logger.info(f"Translation cancelled at page {idx}/{self.total_pages}")
                break

            page_num = page_data.get("page", 0)
            self.current_page = idx

            logger.info(f"Translating page {page_num} ({idx}/{self.total_pages}) with MLX...")

            # 進捗コールバック実行
            if progress_callback:
                progress_callback(idx, self.total_pages, page_num)

            translated_page = {
                "page": page_num,
                "original_text": page_data.get("text", ""),
                "translated_text": "",
                "sections": []
            }

            # ページ全体のテキストを翻訳
            if page_data.get("text"):
                translated_page["translated_text"] = self.translate_text(
                    page_data["text"],
                    context="Equipment specification document"
                )

            # セクションごとに翻訳
            for section in page_data.get("sections", []):
                translated_section = {
                    "original": section.get("text", ""),
                    "translated": self.translate_text(
                        section.get("text", ""),
                        context=f"Page {page_num}, Section"
                    ),
                    "metadata": section.get("metadata", {})
                }
                translated_page["sections"].append(translated_section)

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
        logger.info("Translation cancellation requested")

    def _remove_think_tags(self, text: str) -> str:
        """思考タグを除去"""
        import re
        result = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        result = result.replace('<think>', '').replace('</think>', '')
        return result

    def _fix_encoding_issues(self, text: str) -> str:
        """文字化け修正"""
        replacements = {
            "(cid127)": "・",
            "(cid:127)": "・",
            "•": "・",
        }
        result = text
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result

    def _format_glossary_for_prompt(self) -> str:
        """用語集をプロンプト用にフォーマット"""
        if not self.glossary:
            return ""
        glossary_lines = [f"{en} → {ja}" for en, ja in self.glossary.items()]
        return f"\n\nUse these terminology translations:\n" + "\n".join(glossary_lines)

    def update_glossary(self, glossary: Dict[str, str]):
        """用語集を更新"""
        self.glossary = glossary
        logger.info(f"Glossary updated with {len(glossary)} terms")

    def add_glossary_term(self, english: str, japanese: str):
        """用語を追加"""
        self.glossary[english] = japanese
        logger.info(f"Added glossary term: {english} → {japanese}")


# グローバルインスタンス管理
_current_mlx_translator = None
_current_mlx_quality = "balanced"


def get_mlx_translator(quality: str = None) -> QwenMLXTranslator:
    """
    MLX翻訳エンジンのインスタンスを取得
    品質変更時に古いモデルをアンロード

    Args:
        quality: 翻訳品質 ("high", "balanced", "fast")

    Returns:
        翻訳エンジンインスタンス
    """
    global _current_mlx_translator, _current_mlx_quality

    if quality is None:
        quality = _current_mlx_quality

    # 有効な品質設定かチェック
    if quality not in QwenMLXTranslator.MODELS:
        quality = "balanced"

    # 品質が変更された場合、新しいモデルをロード
    if _current_mlx_translator is None or _current_mlx_quality != quality:
        logger.info(f"Creating new MLX translator instance for quality: {quality}")
        _current_mlx_translator = QwenMLXTranslator(quality=quality)
        _current_mlx_quality = quality

    return _current_mlx_translator


def set_mlx_quality(quality: str):
    """
    デフォルト品質設定を変更

    Args:
        quality: 翻訳品質 ("high", "balanced", "fast")
    """
    global _current_mlx_quality
    if quality in QwenMLXTranslator.MODELS:
        _current_mlx_quality = quality
        logger.info(f"Default MLX quality set to: {quality}")
    else:
        logger.warning(f"Invalid quality: {quality}. Keeping current: {_current_mlx_quality}")
