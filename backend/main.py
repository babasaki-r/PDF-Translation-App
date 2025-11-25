from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import logging
from typing import List, Dict
import asyncio
from contextlib import asynccontextmanager
import io
from datetime import datetime

from pdf_processor import PDFProcessor, PDFTextMerger
from translator import get_translator, set_quality

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# アプリケーション起動時にモデルをロード
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時
    logger.info("Loading translation model...")
    get_translator()  # モデルの事前ロード
    logger.info("Model loaded successfully")
    yield
    # 終了時
    logger.info("Shutting down...")


app = FastAPI(
    title="PDF Translation API",
    description="Technical document translation using Qwen3-14B",
    version="1.0.0",
    lifespan=lifespan
)

# CORS設定（Reactフロントエンドとの通信用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """ヘルスチェック"""
    return {
        "status": "ok",
        "message": "PDF Translation API is running"
    }


@app.get("/health")
async def health_check():
    """詳細なヘルスチェック"""
    translator = get_translator()
    return {
        "status": "healthy",
        "model_loaded": translator is not None,
        "device": translator.device if translator else "unknown"
    }


@app.post("/api/pdf/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    PDFファイルのアップロードとテキスト抽出

    Args:
        file: アップロードされたPDFファイル

    Returns:
        抽出されたテキストデータ
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        # ファイル読み込み
        content = await file.read()
        logger.info(f"Received PDF: {file.filename} ({len(content)} bytes)")

        # PDF情報の取得
        pdf_info = PDFProcessor.get_pdf_info(content)

        # テキスト抽出
        pages_data = PDFProcessor.extract_text_from_pdf(content)

        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "info": pdf_info,
            "pages": pages_data
        })

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@app.post("/api/translate")
async def translate_text(data: Dict):
    """
    テキストの翻訳

    Args:
        data: {"text": "翻訳するテキスト", "context": "オプションの文脈"}

    Returns:
        翻訳結果
    """
    try:
        text = data.get("text", "")
        context = data.get("context", "")

        if not text:
            raise HTTPException(status_code=400, detail="Text is required")

        translator = get_translator()
        translation = translator.translate_text(text, context)

        return JSONResponse({
            "success": True,
            "original": text,
            "translated": translation
        })

    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")


@app.post("/api/translate/pages")
async def translate_pages(data: Dict):
    """
    PDFページデータの翻訳

    Args:
        data: {
            "pages": [ページデータのリスト],
            "quality": "high"|"balanced"|"fast" (オプション)
        }

    Returns:
        翻訳されたページデータ
    """
    try:
        pages_data = data.get("pages", [])
        quality = data.get("quality", "balanced")

        if not pages_data:
            raise HTTPException(status_code=400, detail="Pages data is required")

        logger.info(f"Translating {len(pages_data)} pages with quality: {quality}...")

        translator = get_translator(quality=quality)

        # 翻訳処理（非同期で実行）
        loop = asyncio.get_event_loop()
        translated_pages = await loop.run_in_executor(
            None,
            translator.translate_pages,
            pages_data
        )

        # オリジナルと翻訳をマージ
        merged_data = PDFTextMerger.merge_translations(pages_data, translated_pages)

        return JSONResponse({
            "success": True,
            "pages": merged_data,
            "quality": quality
        })

    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")


@app.post("/api/translate/batch")
async def translate_batch(data: Dict):
    """
    複数テキストのバッチ翻訳

    Args:
        data: {"texts": ["text1", "text2", ...], "context": "オプション"}

    Returns:
        翻訳結果のリスト
    """
    try:
        texts = data.get("texts", [])
        context = data.get("context", "")

        if not texts:
            raise HTTPException(status_code=400, detail="Texts are required")

        translator = get_translator()

        # バッチ翻訳
        loop = asyncio.get_event_loop()
        translations = await loop.run_in_executor(
            None,
            translator.translate_batch,
            texts,
            context
        )

        return JSONResponse({
            "success": True,
            "translations": [
                {"original": orig, "translated": trans}
                for orig, trans in zip(texts, translations)
            ]
        })

    except Exception as e:
        logger.error(f"Batch translation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")


@app.get("/api/translate/progress")
async def get_translation_progress():
    """
    翻訳進捗状況を取得

    Returns:
        進捗情報
    """
    try:
        translator = get_translator()
        progress = translator.get_progress()

        return JSONResponse({
            "success": True,
            "progress": progress
        })

    except Exception as e:
        logger.error(f"Progress error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Progress error: {str(e)}")


@app.post("/api/translate/cancel")
async def cancel_translation():
    """
    翻訳処理をキャンセル

    Returns:
        キャンセル結果
    """
    try:
        translator = get_translator()
        translator.cancel_translation()

        return JSONResponse({
            "success": True,
            "message": "Translation cancellation requested"
        })

    except Exception as e:
        logger.error(f"Cancel error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cancel error: {str(e)}")


@app.post("/api/download/translation")
async def download_translation(data: Dict):
    """
    翻訳結果をテキストファイルとしてダウンロード

    Args:
        data: {
            "pages": [翻訳済みページデータ],
            "format": "original"|"translated"|"both",
            "pageNumbers": [1, 2, 3] (オプション、指定ページのみダウンロード)
        }

    Returns:
        テキストファイル
    """
    try:
        pages_data = data.get("pages", [])
        download_format = data.get("format", "both")
        page_numbers = data.get("pageNumbers", None)

        if not pages_data:
            raise HTTPException(status_code=400, detail="Pages data is required")

        # 特定ページのみフィルタリング
        if page_numbers:
            pages_data = [p for p in pages_data if p.get("page") in page_numbers]
            if not pages_data:
                raise HTTPException(status_code=400, detail="No matching pages found")

        # テキストファイルの生成
        text_content = _generate_text_file(pages_data, download_format)

        # ファイル名の生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if page_numbers and len(page_numbers) == 1:
            filename = f"translation_page{page_numbers[0]}_{timestamp}.txt"
        else:
            filename = f"translation_{timestamp}.txt"

        # BytesIOでファイルストリームを作成
        file_stream = io.BytesIO(text_content.encode('utf-8'))

        return StreamingResponse(
            file_stream,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")


@app.post("/api/quality/set")
async def set_translation_quality(data: Dict):
    """
    翻訳品質設定を変更

    Args:
        data: {"quality": "high"|"balanced"|"fast"}

    Returns:
        設定結果
    """
    try:
        quality = data.get("quality", "balanced")

        if quality not in ["high", "balanced", "fast"]:
            raise HTTPException(status_code=400, detail="Invalid quality. Must be 'high', 'balanced', or 'fast'")

        set_quality(quality)

        return JSONResponse({
            "success": True,
            "quality": quality,
            "message": f"Quality set to {quality}"
        })

    except Exception as e:
        logger.error(f"Quality setting error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Quality setting error: {str(e)}")


@app.get("/api/quality/info")
async def get_quality_info():
    """
    利用可能な品質設定情報を取得

    Returns:
        品質設定情報
    """
    try:
        from translator import Qwen3Translator, _current_quality

        return JSONResponse({
            "success": True,
            "current": _current_quality,
            "options": {
                "high": {
                    "model": Qwen3Translator.MODELS["high"],
                    "description": "最高品質 - Qwen3-14B",
                    "speed": "遅い",
                    "quality": "最高"
                },
                "balanced": {
                    "model": Qwen3Translator.MODELS["balanced"],
                    "description": "バランス - Qwen2.5-14B",
                    "speed": "中",
                    "quality": "高"
                },
                "fast": {
                    "model": Qwen3Translator.MODELS["fast"],
                    "description": "高速 - Qwen2.5-7B",
                    "speed": "速い",
                    "quality": "中"
                }
            }
        })

    except Exception as e:
        logger.error(f"Quality info error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Quality info error: {str(e)}")


@app.post("/api/glossary/update")
async def update_glossary(data: Dict):
    """
    用語集を更新

    Args:
        data: {"glossary": {"英語": "日本語", ...}}

    Returns:
        更新結果
    """
    try:
        glossary = data.get("glossary", {})

        if not isinstance(glossary, dict):
            raise HTTPException(status_code=400, detail="Glossary must be a dictionary")

        translator = get_translator()
        translator.update_glossary(glossary)

        return JSONResponse({
            "success": True,
            "message": f"Glossary updated with {len(glossary)} terms",
            "terms": glossary
        })

    except Exception as e:
        logger.error(f"Glossary update error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Glossary update error: {str(e)}")


@app.post("/api/glossary/add")
async def add_glossary_term(data: Dict):
    """
    用語を1つ追加

    Args:
        data: {"english": "English term", "japanese": "日本語訳"}

    Returns:
        追加結果
    """
    try:
        english = data.get("english", "")
        japanese = data.get("japanese", "")

        if not english or not japanese:
            raise HTTPException(status_code=400, detail="Both english and japanese terms are required")

        translator = get_translator()
        translator.add_glossary_term(english, japanese)

        return JSONResponse({
            "success": True,
            "message": "Term added to glossary",
            "term": {english: japanese}
        })

    except Exception as e:
        logger.error(f"Glossary add error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Glossary add error: {str(e)}")


@app.get("/api/glossary")
async def get_glossary():
    """
    現在の用語集を取得

    Returns:
        用語集
    """
    try:
        translator = get_translator()

        return JSONResponse({
            "success": True,
            "glossary": translator.glossary,
            "count": len(translator.glossary)
        })

    except Exception as e:
        logger.error(f"Glossary get error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Glossary get error: {str(e)}")


def _generate_text_file(pages_data: List[Dict], format_type: str) -> str:
    """
    翻訳結果からテキストファイルを生成

    Args:
        pages_data: ページデータ
        format_type: "original", "translated", "both"

    Returns:
        テキストコンテンツ
    """
    lines = []
    lines.append("=" * 80)
    lines.append("PDF Translation Result")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)
    lines.append("")

    for page_data in pages_data:
        page_num = page_data.get("page", "?")
        lines.append(f"\n{'=' * 80}")
        lines.append(f"Page {page_num}")
        lines.append(f"{'=' * 80}\n")

        if format_type in ["original", "both"]:
            original_text = page_data.get("original", {}).get("text", "")
            if original_text:
                lines.append("[ORIGINAL]")
                lines.append("-" * 80)
                lines.append(original_text)
                lines.append("")

        if format_type in ["translated", "both"]:
            translated_text = page_data.get("translated", {}).get("text", "")
            if translated_text:
                lines.append("[TRANSLATION]")
                lines.append("-" * 80)
                lines.append(translated_text)
                lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
