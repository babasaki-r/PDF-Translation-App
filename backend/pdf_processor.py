import io
import pdfplumber
import fitz  # PyMuPDF
from typing import List, Dict, BinaryIO
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF処理とテキスト抽出"""

    @staticmethod
    def extract_text_from_pdf(file_content: bytes, use_ocr: bool = False) -> List[Dict]:
        """
        PDFからテキストを抽出
        PyMuPDF (fitz) を優先使用し、CID文字が多い場合は自動対応
        文字化けが検出された場合はOCRにフォールバック

        Args:
            file_content: PDFファイルのバイナリコンテンツ
            use_ocr: OCRを強制使用するかどうか

        Returns:
            ページごとのテキストデータ
            [
                {
                    "page": 1,
                    "text": "ページ全体のテキスト"
                },
                ...
            ]
        """
        pages_data = []
        needs_ocr = use_ocr

        try:
            # PyMuPDF (fitz) を使用してテキスト抽出（CID問題に強い）
            doc = fitz.open(stream=file_content, filetype="pdf")
            logger.info(f"Processing PDF with {len(doc)} pages using PyMuPDF")

            for page_num in range(len(doc)):
                page = doc[page_num]

                # テキスト抽出（複数のオプションを試行）
                text = page.get_text("text")

                # CID文字が多い場合は別の抽出方法を試す
                if PDFProcessor._has_cid_issues(text):
                    logger.info(f"Page {page_num + 1}: CID issues detected, trying alternative extraction")
                    # ブロック単位で抽出を試みる
                    blocks = page.get_text("blocks")
                    text_parts = []
                    for block in blocks:
                        if block[6] == 0:  # テキストブロック
                            block_text = block[4]
                            if not PDFProcessor._has_cid_issues(block_text):
                                text_parts.append(block_text)
                    if text_parts:
                        text = "\n".join(text_parts)

                # 文字化け修正
                text = PDFProcessor._fix_encoding_issues(text)

                # 最初のページで文字化けをチェック
                if page_num == 0 and PDFProcessor._has_encoding_issues(text):
                    logger.warning("Encoding issues detected in first page, will try OCR")
                    needs_ocr = True
                    doc.close()
                    break

                page_data = {
                    "page": page_num + 1,
                    "text": text
                }

                pages_data.append(page_data)
                logger.info(f"Extracted page {page_num + 1}: {len(text)} characters")

            if not needs_ocr:
                doc.close()

        except Exception as e:
            logger.error(f"Error processing PDF with PyMuPDF: {str(e)}")
            needs_ocr = True

        # OCRが必要な場合
        if needs_ocr:
            logger.info("Using OCR for text extraction...")
            pages_data = PDFProcessor._extract_with_ocr(file_content)

        # OCRも失敗した場合はpdfplumberを試す
        if not pages_data:
            logger.info("Falling back to pdfplumber...")
            pages_data = PDFProcessor._extract_with_pdfplumber(file_content)

        return pages_data

    @staticmethod
    def _extract_with_ocr(file_content: bytes) -> List[Dict]:
        """
        OCRを使用してPDFからテキストを抽出
        macOSのVision frameworkを使用
        """
        pages_data = []

        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            logger.info(f"Processing PDF with {len(doc)} pages using OCR")

            for page_num in range(len(doc)):
                page = doc[page_num]

                # ページを画像に変換（高解像度）
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")

                # macOSのOCRを使用
                text = PDFProcessor._ocr_with_vision(img_data)

                if text:
                    text = PDFProcessor._fix_encoding_issues(text)
                    logger.info(f"OCR extracted page {page_num + 1}: {len(text)} characters")
                else:
                    logger.warning(f"OCR failed for page {page_num + 1}")
                    text = ""

                page_data = {
                    "page": page_num + 1,
                    "text": text
                }
                pages_data.append(page_data)

            doc.close()

        except Exception as e:
            logger.error(f"Error during OCR extraction: {str(e)}")

        return pages_data

    @staticmethod
    def _ocr_with_vision(image_data: bytes) -> str:
        """
        macOSのVision frameworkを使用してOCR
        """
        import subprocess
        import tempfile
        import os

        try:
            # 一時ファイルに画像を保存
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                f.write(image_data)
                temp_image_path = f.name

            # Swiftスクリプトを使ってOCRを実行
            swift_code = '''
import Foundation
import Vision
import AppKit

let imagePath = CommandLine.arguments[1]

guard let image = NSImage(contentsOfFile: imagePath),
      let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    fputs("Error: Could not load image", stderr)
    exit(1)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["en-US"]
request.usesLanguageCorrection = true

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

do {
    try handler.perform([request])

    guard let observations = request.results else {
        print("")
        exit(0)
    }

    var texts: [String] = []
    for observation in observations {
        if let topCandidate = observation.topCandidates(1).first {
            texts.append(topCandidate.string)
        }
    }

    print(texts.joined(separator: "\\n"))
} catch {
    fputs("Error: \\(error.localizedDescription)", stderr)
    exit(1)
}
'''
            # 一時Swiftファイルを作成
            with tempfile.NamedTemporaryFile(suffix='.swift', delete=False, mode='w') as f:
                f.write(swift_code)
                temp_swift_path = f.name

            try:
                # Swiftスクリプトを実行
                result = subprocess.run(
                    ['swift', temp_swift_path, temp_image_path],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0:
                    return result.stdout
                else:
                    logger.error(f"OCR Swift error: {result.stderr}")
                    return ""

            finally:
                os.unlink(temp_swift_path)
                os.unlink(temp_image_path)

        except Exception as e:
            logger.error(f"OCR error: {str(e)}")
            return ""

    @staticmethod
    def _has_cid_issues(text: str) -> bool:
        """
        テキストにCID文字化け問題があるかチェック
        """
        cid_count = len(re.findall(r'\(cid:\d+\)', text))
        total_length = len(text)
        # CID文字が全体の10%以上ある場合は問題ありとみなす
        return total_length > 0 and (cid_count / max(total_length, 1)) > 0.1

    @staticmethod
    def _has_encoding_issues(text: str) -> bool:
        """
        テキストにエンコーディング問題（文字化け）があるかチェック
        """
        if not text or len(text) < 50:
            return False

        # 英数字と一般的な記号の比率をチェック
        normal_chars = len(re.findall(r'[a-zA-Z0-9\s.,;:!?\-\'\"()\[\]{}]', text))
        total_chars = len(text)

        # 正常な文字が50%未満の場合は文字化けの可能性が高い
        ratio = normal_chars / total_chars if total_chars > 0 else 0
        return ratio < 0.5

    @staticmethod
    def _extract_with_pdfplumber(file_content: bytes) -> List[Dict]:
        """
        pdfplumberを使用したフォールバック抽出
        """
        pages_data = []

        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                logger.info(f"Processing PDF with {len(pdf.pages)} pages using pdfplumber")

                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    text = PDFProcessor._fix_encoding_issues(text)

                    page_data = {
                        "page": page_num,
                        "text": text
                    }

                    pages_data.append(page_data)
                    logger.info(f"Extracted page {page_num}: {len(text)} characters")

        except Exception as e:
            logger.error(f"Error processing PDF with pdfplumber: {str(e)}")
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
        # パターン1: (cid:数字) 形式の文字化けを全て除去
        # 例: (cid:19)(cid:18)(cid:12) → ""
        result = re.sub(r'\(cid:\d+\)', '', text)
        result = re.sub(r'\(cid\d+\)', '', result)

        # パターン2: ・X・ のような中点で囲まれた文字パターンを除去
        # 例: ・O・n・l・i・n・e・ → Online
        result = re.sub(r'・([A-Za-z0-9])・\s*', r'\1', result)

        # パターン3: 残った先頭と末尾の中点を除去
        result = result.strip('・').strip()

        # パターン4: 通常の文字化け置換
        replacements = {
            "(cid:127)": "・",
            "(cid127)": "・",
            "(cid:149)": "・",
        }

        for old, new in replacements.items():
            result = result.replace(old, new)

        # パターン5: 連続する空白文字を単一のスペースに（改行は保持）
        result = re.sub(r'[^\S\n]+', ' ', result)

        # パターン6: 空行の連続を削減
        result = re.sub(r'\n\s*\n', '\n\n', result)

        return result.strip()

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
                    "text": orig["text"]
                },
                "translated": {
                    "text": trans.get("translated_text", "")
                }
            }
            merged_data.append(merged)

        return merged_data
