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
from translator import (
    get_apple_translator,
    get_apple_progress_safe,
    cancel_apple_safe,
    get_mlx_translator,
    get_mlx_status,
    get_mlx_progress_safe,
    cancel_mlx_safe,
    get_document_types,
    load_glossary_from_file,
    save_glossary_to_file
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# アプリケーション起動時の初期化
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時
    logger.info("PDF Translation API starting...")
    logger.info("Translation engines: MLX (AI翻訳), Apple (簡易翻訳)")
    yield
    # 終了時
    logger.info("Shutting down...")


app = FastAPI(
    title="PDF Translation API",
    description="Technical document translation with MLX and Apple Translation",
    version="3.0.0",
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
    """詳細なヘルスチェック（トランスレータの生成を誘発しない）"""
    return {
        "status": "healthy",
        "engines": ["mlx", "apple"]
    }


@app.get("/api/document-types")
async def get_document_types_api():
    """
    利用可能な文書タイプの一覧を取得

    Returns:
        文書タイプのリスト
    """
    try:
        document_types = get_document_types()
        return JSONResponse({
            "success": True,
            "document_types": document_types
        })
    except Exception as e:
        logger.error(f"Error getting document types: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting document types: {str(e)}")


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

        # 日本語が含まれているかを検出（最初の数ページをチェック）
        contains_japanese = False
        sample_text = ""
        for page in pages_data[:3]:  # 最初の3ページをサンプル
            sample_text += page.get("text", "")

        # 日本語文字（ひらがな、カタカナ、漢字）の検出
        import re
        japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]')
        japanese_chars = japanese_pattern.findall(sample_text)
        # 日本語文字が一定数以上あれば日本語文書と判定
        contains_japanese = len(japanese_chars) > 10

        logger.info(f"Japanese detection: {len(japanese_chars)} characters found, contains_japanese={contains_japanese}")

        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "info": pdf_info,
            "pages": pages_data,
            "contains_japanese": contains_japanese
        })

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@app.post("/api/download/translation")
async def download_translation(data: Dict):
    """
    翻訳結果をテキストファイルとしてダウンロード

    Args:
        data: {
            "pages": [翻訳済みページデータ],
            "format": "original"|"translated"|"both",
            "pageNumbers": [1, 2, 3] (オプション、指定ページのみダウンロード),
            "documentType": 文書タイプ (オプション),
            "translationEngine": 翻訳エンジン (オプション)
        }

    Returns:
        テキストファイル
    """
    try:
        pages_data = data.get("pages", [])
        download_format = data.get("format", "both")
        page_numbers = data.get("pageNumbers", None)
        document_type = data.get("documentType", None)
        translation_engine = data.get("translationEngine", None)

        if not pages_data:
            raise HTTPException(status_code=400, detail="Pages data is required")

        # 特定ページのみフィルタリング
        if page_numbers:
            pages_data = [p for p in pages_data if p.get("page") in page_numbers]
            if not pages_data:
                raise HTTPException(status_code=400, detail="No matching pages found")

        # テキストファイルの生成
        text_content = _generate_text_file(
            pages_data,
            download_format,
            document_type=document_type,
            translation_engine=translation_engine
        )

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


# ========== 用語集 API ==========

@app.get("/api/glossary")
async def get_glossary():
    """
    現在の用語集を取得

    Returns:
        用語集
    """
    try:
        glossary = load_glossary_from_file()

        return JSONResponse({
            "success": True,
            "glossary": glossary,
            "count": len(glossary)
        })

    except Exception as e:
        logger.error(f"Glossary get error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Glossary get error: {str(e)}")


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

        save_glossary_to_file(glossary)

        # 各翻訳エンジンの用語集を更新
        try:
            mlx = get_mlx_translator()
            mlx.update_glossary(glossary)
        except:
            pass

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

        # 既存の用語集を読み込み
        glossary = load_glossary_from_file()
        glossary[english] = japanese
        save_glossary_to_file(glossary)

        # 各翻訳エンジンの用語集を更新
        try:
            mlx = get_mlx_translator()
            mlx.update_glossary(glossary)
        except:
            pass

        return JSONResponse({
            "success": True,
            "message": "Term added to glossary",
            "term": {english: japanese}
        })

    except Exception as e:
        logger.error(f"Glossary add error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Glossary add error: {str(e)}")


# ========== Apple翻訳 API ==========

@app.post("/api/translate/apple")
async def translate_pages_apple(data: Dict):
    """
    Apple翻訳を使用したページ翻訳

    Args:
        data: {
            "pages": [ページデータのリスト],
            "direction": "en-to-ja"|"ja-to-en" (オプション)
        }

    Returns:
        翻訳されたページデータ
    """
    try:
        pages_data = data.get("pages", [])
        direction = data.get("direction", "en-to-ja")

        if not pages_data:
            raise HTTPException(status_code=400, detail="Pages data is required")

        logger.info(f"[Apple] Translating {len(pages_data)} pages with direction: {direction}...")

        translator = get_apple_translator()

        # 翻訳処理（非同期で実行）
        loop = asyncio.get_event_loop()
        translated_pages = await loop.run_in_executor(
            None,
            lambda: translator.translate_pages(pages_data, direction=direction)
        )

        # オリジナルと翻訳をマージ
        merged_data = PDFTextMerger.merge_translations(pages_data, translated_pages)

        return JSONResponse({
            "success": True,
            "pages": merged_data,
            "engine": "apple",
            "direction": direction
        })

    except Exception as e:
        logger.error(f"Apple translation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Apple translation error: {str(e)}")


@app.get("/api/translate/apple/progress")
async def get_apple_translation_progress():
    """
    Apple翻訳の進捗状況を取得
    注意: トランスレータの生成を誘発しないように安全な関数を使用

    Returns:
        進捗情報
    """
    try:
        progress = get_apple_progress_safe()
        return JSONResponse({
            "success": True,
            "progress": progress
        })

    except Exception as e:
        logger.error(f"Apple progress error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Progress error: {str(e)}")


@app.post("/api/translate/apple/cancel")
async def cancel_apple_translation():
    """
    Apple翻訳処理をキャンセル
    注意: トランスレータの生成を誘発しないように安全な関数を使用

    Returns:
        キャンセル結果
    """
    try:
        cancelled = cancel_apple_safe()

        return JSONResponse({
            "success": True,
            "message": "Apple translation cancellation requested" if cancelled else "No active Apple translation to cancel"
        })

    except Exception as e:
        logger.error(f"Apple cancel error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cancel error: {str(e)}")


# ========== MLX翻訳 API ==========

@app.get("/api/mlx/status")
async def get_mlx_server_status():
    """
    MLXサーバーの接続状態を確認

    Returns:
        MLXサーバーのステータス情報
    """
    try:
        status = get_mlx_status()
        return JSONResponse({
            "success": True,
            **status
        })

    except Exception as e:
        logger.error(f"MLX status error: {str(e)}")
        return JSONResponse({
            "success": False,
            "available": False,
            "error": str(e)
        })


@app.post("/api/translate/mlx")
async def translate_pages_mlx(data: Dict):
    """
    MLXサーバーを使用したページ翻訳

    Args:
        data: {
            "pages": [ページデータのリスト],
            "direction": "en-to-ja"|"ja-to-en" (オプション),
            "document_type": "文書タイプ（オプション）"
        }

    Returns:
        翻訳されたページデータ
    """
    try:
        pages_data = data.get("pages", [])
        direction = data.get("direction", "en-to-ja")
        document_type = data.get("document_type", "steel_technical")

        if not pages_data:
            raise HTTPException(status_code=400, detail="Pages data is required")

        logger.info(f"[MLX] Translating {len(pages_data)} pages with direction: {direction}, doc_type: {document_type}...")

        translator = get_mlx_translator()

        if not translator.server_available:
            raise HTTPException(status_code=503, detail="MLX Server is not available. Please ensure mlx_lm.server is running.")

        # 翻訳処理（非同期で実行）
        loop = asyncio.get_event_loop()
        translated_pages = await loop.run_in_executor(
            None,
            lambda: translator.translate_pages(pages_data, direction=direction, document_type=document_type)
        )

        # オリジナルと翻訳をマージ
        merged_data = PDFTextMerger.merge_translations(pages_data, translated_pages)

        return JSONResponse({
            "success": True,
            "pages": merged_data,
            "engine": "mlx",
            "model": translator.MODEL_NAME,
            "direction": direction
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MLX translation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"MLX translation error: {str(e)}")


@app.get("/api/translate/mlx/progress")
async def get_mlx_translation_progress():
    """
    MLX翻訳の進捗状況を取得
    注意: トランスレータの生成を誘発しないように安全な関数を使用

    Returns:
        進捗情報
    """
    try:
        progress = get_mlx_progress_safe()
        return JSONResponse({
            "success": True,
            "progress": progress
        })

    except Exception as e:
        logger.error(f"MLX progress error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Progress error: {str(e)}")


@app.post("/api/translate/mlx/cancel")
async def cancel_mlx_translation():
    """
    MLX翻訳処理をキャンセル
    注意: トランスレータの生成を誘発しないように安全な関数を使用

    Returns:
        キャンセル結果
    """
    try:
        cancelled = cancel_mlx_safe()

        return JSONResponse({
            "success": True,
            "message": "MLX translation cancellation requested" if cancelled else "No active MLX translation to cancel"
        })

    except Exception as e:
        logger.error(f"MLX cancel error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cancel error: {str(e)}")


@app.post("/api/ask/mlx")
async def ask_question_mlx(data: Dict):
    """
    MLXサーバーを使用してPDFの内容について質問する

    Args:
        data: {
            "question": "質問テキスト",
            "context": "PDFのテキスト内容"
        }

    Returns:
        AIからの回答
    """
    try:
        question = data.get("question", "")
        context = data.get("context", "")

        if not question:
            raise HTTPException(status_code=400, detail="Question is required")

        if not context:
            raise HTTPException(status_code=400, detail="Context (PDF content) is required")

        logger.info(f"[MLX] Answering question: {question[:50]}...")

        translator = get_mlx_translator()

        if not translator.server_available:
            raise HTTPException(status_code=503, detail="MLX Server is not available")

        # 非同期で質問回答を実行
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(
            None,
            translator.ask_question,
            question,
            context
        )

        return JSONResponse({
            "success": True,
            "question": question,
            "answer": answer,
            "model": translator.MODEL_NAME
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MLX question error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Question error: {str(e)}")


# ========== ヘルパー関数 ==========

def _generate_text_file(
    pages_data: List[Dict],
    format_type: str,
    document_type: str = None,
    translation_engine: str = None
) -> str:
    """
    翻訳結果からテキストファイルを生成

    Args:
        pages_data: ページデータ
        format_type: "original", "translated", "both"
        document_type: 文書タイプ
        translation_engine: 翻訳エンジン

    Returns:
        テキストコンテンツ
    """
    # 文書タイプの表示名マッピング
    document_type_names = {
        'steel_technical': '鉄鋼業における技術文書',
        'general_technical': '一般的な技術文書',
        'academic_paper': '技術論文',
        'contract': '契約書',
        'general_document': '一般的な文書',
        'order_acceptance': '注文書・検収書',
    }

    # 翻訳エンジンの表示名マッピング
    engine_names = {
        'mlx': 'AI翻訳',
        'apple': '簡易翻訳',
    }

    lines = []
    lines.append("=" * 80)
    lines.append("PDF Translation Result")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 文書タイプを追加
    if document_type:
        doc_type_display = document_type_names.get(document_type, document_type)
        lines.append(f"Document Type: {doc_type_display}")

    # 翻訳エンジンを追加
    if translation_engine:
        engine_display = engine_names.get(translation_engine, translation_engine)
        lines.append(f"Translation Engine: {engine_display}")

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
