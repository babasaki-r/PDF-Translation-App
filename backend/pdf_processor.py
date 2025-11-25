import io
import pdfplumber
from typing import List, Dict, BinaryIO
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF処理とテキスト抽出"""

    @staticmethod
    def extract_text_from_pdf(file_content: bytes) -> List[Dict]:
        """
        PDFからテキストを抽出

        Args:
            file_content: PDFファイルのバイナリコンテンツ

        Returns:
            ページごとのテキストデータ
            [
                {
                    "page": 1,
                    "text": "ページ全体のテキスト",
                    "sections": [
                        {"text": "セクションテキスト", "metadata": {...}}
                    ]
                },
                ...
            ]
        """
        pages_data = []

        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                logger.info(f"Processing PDF with {len(pdf.pages)} pages")

                for page_num, page in enumerate(pdf.pages, start=1):
                    # ページ全体のテキスト抽出
                    text = page.extract_text() or ""

                    # 文字化け修正
                    text = PDFProcessor._fix_encoding_issues(text)

                    # テーブルの抽出（オプション）
                    tables = page.extract_tables()

                    # セクション分割（段落ベース）
                    sections = PDFProcessor._split_into_sections(text)

                    page_data = {
                        "page": page_num,
                        "text": text,
                        "sections": sections,
                        "tables": tables if tables else [],
                        "metadata": {
                            "width": page.width,
                            "height": page.height,
                            "has_tables": len(tables) > 0 if tables else False
                        }
                    }

                    pages_data.append(page_data)
                    logger.info(f"Extracted page {page_num}: {len(text)} characters")

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise

        return pages_data

    @staticmethod
    def _fix_encoding_issues(text: str) -> str:
        """
        PDFテキストの文字化け修正

        Args:
            text: 修正するテキスト

        Returns:
            修正後のテキスト
        """
        import re

        # パターン1: ・X・ のような中点で囲まれた文字パターンを除去
        # 例: ・O・n・l・i・n・e・ → Online
        result = re.sub(r'・([A-Za-z0-9])・\s*', r'\1', text)

        # パターン2: 残った先頭と末尾の中点を除去
        result = result.strip('・').strip()

        # パターン3: 通常の文字化け置換
        replacements = {
            "(cid:127)": "・",
            "(cid127)": "・",
            "(cid:149)": "・",
        }

        for old, new in replacements.items():
            result = result.replace(old, new)

        return result

    @staticmethod
    def _split_into_sections(text: str) -> List[Dict]:
        """
        テキストをセクションに分割

        Args:
            text: ページのテキスト

        Returns:
            セクションデータのリスト
        """
        sections = []

        # 段落で分割（空行で区切る）
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        for idx, paragraph in enumerate(paragraphs):
            # セクションの特徴を検出
            is_heading = PDFProcessor._is_heading(paragraph)
            is_list_item = paragraph.strip().startswith(('-', '•', '○', '●'))

            section = {
                "text": paragraph,
                "metadata": {
                    "index": idx,
                    "is_heading": is_heading,
                    "is_list": is_list_item,
                    "length": len(paragraph)
                }
            }
            sections.append(section)

        return sections

    @staticmethod
    def _is_heading(text: str) -> bool:
        """テキストが見出しかどうかを判定"""
        # 簡易的な見出し判定
        text = text.strip()

        # 短いテキスト（通常80文字以下）
        if len(text) > 80:
            return False

        # すべて大文字、または数字で始まる
        if text.isupper() or (text and text[0].isdigit()):
            return True

        # 末尾にピリオドがない
        if not text.endswith('.'):
            return True

        return False

    @staticmethod
    def get_pdf_info(file_content: bytes) -> Dict:
        """
        PDF基本情報の取得

        Args:
            file_content: PDFファイルのバイナリコンテンツ

        Returns:
            PDF情報
        """
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                info = {
                    "pages": len(pdf.pages),
                    "metadata": pdf.metadata,
                    "first_page_size": {
                        "width": pdf.pages[0].width,
                        "height": pdf.pages[0].height
                    } if pdf.pages else None
                }
                return info
        except Exception as e:
            logger.error(f"Error getting PDF info: {str(e)}")
            raise


class PDFTextMerger:
    """翻訳結果とPDFのマージ処理"""

    @staticmethod
    def merge_translations(
        original_pages: List[Dict],
        translated_pages: List[Dict]
    ) -> List[Dict]:
        """
        オリジナルと翻訳をマージ

        Args:
            original_pages: オリジナルのページデータ
            translated_pages: 翻訳されたページデータ

        Returns:
            マージされたデータ
        """
        merged_data = []

        for orig, trans in zip(original_pages, translated_pages):
            merged = {
                "page": orig["page"],
                "original": {
                    "text": orig["text"],
                    "sections": orig.get("sections", [])
                },
                "translated": {
                    "text": trans.get("translated_text", ""),
                    "sections": trans.get("sections", [])
                },
                "metadata": orig.get("metadata", {}),
                "tables": orig.get("tables", [])
            }
            merged_data.append(merged)

        return merged_data
