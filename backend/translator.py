import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import List, Dict
import logging
import json
import os
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

        # PyTorch 2.0の最適化機能を有効化（可能な場合）
        try:
            # BetterTransformerで高速化を試みる
            from optimum.bettertransformer import BetterTransformer
            logger.info("Applying BetterTransformer optimization...")
            self.model = BetterTransformer.transform(self.model)
            logger.info("BetterTransformer optimization applied")
        except Exception as e:
            logger.warning(f"BetterTransformer not available: {e}")

        # torch.compile()で更に高速化（PyTorch 2.0以降）
        try:
            import torch._dynamo as dynamo
            if hasattr(torch, 'compile') and self.device == "mps":
                logger.info("Compiling model with torch.compile()...")
                # MPSではデフォルトのreduceバックエンドを使用
                self.model = torch.compile(self.model, mode="reduce-overhead")
                logger.info("Model compiled successfully")
        except Exception as e:
            logger.warning(f"torch.compile() not available: {e}")

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
                [{"page": 1, "text": "...", "sections": [...]}, ...]
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
                "translated_text": "",
                "sections": []
            }

            # ページ全体のテキストを翻訳
            if page_data.get("text"):
                translated_page["translated_text"] = self.translate_text(
                    page_data["text"],
                    context="Steel industry equipment specification document"
                )

            # セクションごとに翻訳（より詳細な制御が必要な場合）
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

    def proofread_translation(self, original_text: str, translated_text: str) -> Dict:
        """
        翻訳の校正を実行
        LLMを使用して翻訳の正確性を検証し、問題点を指摘・修正

        Args:
            original_text: 元の英語テキスト
            translated_text: 翻訳された日本語テキスト

        Returns:
            校正結果 {
                "has_issues": bool,
                "corrected_text": str,
                "issues": [{"type": str, "description": str, "suggestion": str}]
            }
        """
        prompt = f"""You are a professional proofreader for technical translations in the steel industry.

Review the following English-to-Japanese translation for accuracy, terminology consistency, and naturalness.

Original English:
{original_text}

Japanese Translation:
{translated_text}

Analyze this translation and:
1. Check if the meaning is accurately conveyed
2. Verify technical terminology is correct for steel industry
3. Check for any Chinese characters that should be Japanese
4. Ensure natural Japanese expression

If there are issues, provide a corrected version and list the problems found.

Output format:
HAS_ISSUES: [YES/NO]
CORRECTED_TEXT: [corrected Japanese text if needed, or same text if no issues]
ISSUES: [list issues found, one per line with format "TYPE: description - suggestion"]

Response:"""

        system_content = """You are a professional technical translation proofreader specializing in steel industry documentation.
Analyze translations carefully and provide constructive feedback.
Always output in a structured format."""

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

        # 校正には高品質設定を使用
        gen_settings = {
            "max_new_tokens": 2048,
            "temperature": 0.1,
            "top_p": 0.95,
            "do_sample": False,
            "num_beams": 1,
        }

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
        response = self._remove_think_tags(response)

        # レスポンスをパース
        has_issues = "YES" in response.split("HAS_ISSUES:")[1].split("\n")[0].upper() if "HAS_ISSUES:" in response else False

        corrected_text = translated_text  # デフォルトは元のテキスト
        if "CORRECTED_TEXT:" in response:
            corrected_part = response.split("CORRECTED_TEXT:")[1]
            if "ISSUES:" in corrected_part:
                corrected_text = corrected_part.split("ISSUES:")[0].strip()
            else:
                corrected_text = corrected_part.strip()

        issues = []
        if "ISSUES:" in response:
            issues_text = response.split("ISSUES:")[1].strip()
            for line in issues_text.split("\n"):
                line = line.strip()
                if line and ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        issue_type = parts[0].strip()
                        rest = parts[1].strip()
                        if " - " in rest:
                            desc, sugg = rest.split(" - ", 1)
                            issues.append({
                                "type": issue_type,
                                "description": desc.strip(),
                                "suggestion": sugg.strip()
                            })

        return {
            "has_issues": has_issues,
            "corrected_text": corrected_text,
            "issues": issues,
            "raw_response": response
        }

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
_current_quality = "balanced"


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
