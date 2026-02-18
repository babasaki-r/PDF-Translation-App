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
    get_ollama_translator,
    get_ollama_progress_safe,
    cancel_ollama_safe,
    get_swallow_translator,
    get_swallow_status,
    get_swallow_progress_safe,
    cancel_swallow_safe,
    unload_swallow_translator,
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
    logger.info("Translation engines: Ollama (バランス), Swallow (日本語重視), Apple (簡易翻訳)")
    yield
    # 終了時
    logger.info("Shutting down...")


app = FastAPI(
    title="PDF Translation API",
    description="Technical document translation with Ollama, Swallow, and Apple Translation",
    version="2.2.0",
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
        "engines": ["ollama", "swallow", "apple"]
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
            "translationEngine": 翻訳エンジン (オプション),
            "ollamaModel": Ollamaモデル名 (オプション)
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
        ollama_model = data.get("ollamaModel", None)

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
            translation_engine=translation_engine,
            ollama_model=ollama_model
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
            ollama = get_ollama_translator()
            ollama.update_glossary(glossary)
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
            ollama = get_ollama_translator()
            ollama.update_glossary(glossary)
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


# ========== Ollama翻訳 API ==========

@app.get("/api/ollama/status")
async def get_ollama_status():
    """
    Ollamaの接続状態を確認

    Returns:
        Ollamaのステータス情報
    """
    try:
        translator = get_ollama_translator()

        return JSONResponse({
            "success": True,
            "available": translator.ollama_available,
            "current_model": translator.model,
            "base_url": translator.base_url
        })

    except Exception as e:
        logger.error(f"Ollama status error: {str(e)}")
        return JSONResponse({
            "success": False,
            "available": False,
            "error": str(e)
        })


@app.get("/api/ollama/models")
async def get_ollama_models():
    """
    利用可能なOllamaモデル一覧を取得

    Returns:
        モデル一覧
    """
    try:
        translator = get_ollama_translator()
        models = translator.get_available_models()

        return JSONResponse({
            "success": True,
            "models": models,
            "current_model": translator.model
        })

    except Exception as e:
        logger.error(f"Ollama models error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ollama models error: {str(e)}")


@app.post("/api/ollama/model/set")
async def set_ollama_model(data: Dict):
    """
    使用するOllamaモデルを変更

    Args:
        data: {"model": "モデル名"}

    Returns:
        設定結果
    """
    try:
        model = data.get("model", "")

        if not model:
            raise HTTPException(status_code=400, detail="Model name is required")

        translator = get_ollama_translator(model=model)

        return JSONResponse({
            "success": True,
            "model": translator.model,
            "message": f"Model set to {translator.model}"
        })

    except Exception as e:
        logger.error(f"Ollama model set error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ollama model set error: {str(e)}")


@app.post("/api/translate/ollama")
async def translate_pages_ollama(data: Dict):
    """
    Ollamaを使用したページ翻訳

    Args:
        data: {
            "pages": [ページデータのリスト],
            "model": "モデル名（オプション）",
            "direction": "en-to-ja"|"ja-to-en" (オプション),
            "document_type": "文書タイプ（オプション）"
        }

    Returns:
        翻訳されたページデータ
    """
    try:
        pages_data = data.get("pages", [])
        model = data.get("model", None)
        direction = data.get("direction", "en-to-ja")
        document_type = data.get("document_type", "steel_technical")

        if not pages_data:
            raise HTTPException(status_code=400, detail="Pages data is required")

        logger.info(f"[Ollama] Translating {len(pages_data)} pages with model: {model or 'default'}, direction: {direction}, doc_type: {document_type}...")

        translator = get_ollama_translator(model=model)

        if not translator.ollama_available:
            raise HTTPException(status_code=503, detail="Ollama is not available. Please ensure Ollama is running.")

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
            "engine": "ollama",
            "model": translator.model,
            "direction": direction
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ollama translation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ollama translation error: {str(e)}")


@app.get("/api/translate/ollama/progress")
async def get_ollama_translation_progress():
    """
    Ollama翻訳の進捗状況を取得
    注意: トランスレータの生成を誘発しないように安全な関数を使用

    Returns:
        進捗情報
    """
    try:
        progress = get_ollama_progress_safe()
        return JSONResponse({
            "success": True,
            "progress": progress
        })

    except Exception as e:
        logger.error(f"Ollama progress error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Progress error: {str(e)}")


@app.post("/api/translate/ollama/cancel")
async def cancel_ollama_translation():
    """
    Ollama翻訳処理をキャンセル
    注意: トランスレータの生成を誘発しないように安全な関数を使用

    Returns:
        キャンセル結果
    """
    try:
        cancelled = cancel_ollama_safe()

        return JSONResponse({
            "success": True,
            "message": "Ollama translation cancellation requested" if cancelled else "No active Ollama translation to cancel"
        })

    except Exception as e:
        logger.error(f"Ollama cancel error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cancel error: {str(e)}")


@app.post("/api/ask/ollama")
async def ask_question_ollama(data: Dict):
    """
    Ollamaを使用してPDFの内容について質問する

    Args:
        data: {
            "question": "質問テキスト",
            "context": "PDFのテキスト内容",
            "model": "モデル名（オプション）"
        }

    Returns:
        AIからの回答
    """
    try:
        question = data.get("question", "")
        context = data.get("context", "")
        model = data.get("model", None)

        if not question:
            raise HTTPException(status_code=400, detail="Question is required")

        if not context:
            raise HTTPException(status_code=400, detail="Context (PDF content) is required")

        logger.info(f"[Ollama] Answering question: {question[:50]}...")

        translator = get_ollama_translator(model=model)

        if not translator.ollama_available:
            raise HTTPException(status_code=503, detail="Ollama is not available")

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
            "model": translator.model
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ollama question error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Question error: {str(e)}")


# ========== Swallow翻訳 API ==========

@app.get("/api/swallow/status")
async def get_swallow_model_status():
    """
    Swallowモデルのロード状態を取得

    Returns:
        ステータス情報 {"loaded": bool, "loading": bool, "error": str|None}
    """
    try:
        status = get_swallow_status()
        return JSONResponse({
            "success": True,
            **status
        })
    except Exception as e:
        logger.error(f"Swallow status error: {str(e)}")
        return JSONResponse({
            "success": False,
            "loaded": False,
            "loading": False,
            "error": str(e)
        })


@app.post("/api/translate/swallow")
async def translate_pages_swallow(data: Dict):
    """
    Swallow (Llama-3.1-Swallow-8B) を使用したページ翻訳
    日本語に特化したLlamaベースのモデル

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

        logger.info(f"[Swallow] Translating {len(pages_data)} pages with direction: {direction}, doc_type: {document_type}...")

        translator = get_swallow_translator()

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
            "engine": "swallow",
            "model": "Llama-3.1-Swallow-8B-Instruct-v0.5",
            "direction": direction
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Swallow translation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Swallow translation error: {str(e)}")


@app.get("/api/translate/swallow/progress")
async def get_swallow_translation_progress():
    """
    Swallow翻訳の進捗状況を取得
    注意: モデルのロードを誘発しないように安全な関数を使用

    Returns:
        進捗情報
    """
    try:
        progress = get_swallow_progress_safe()
        return JSONResponse({
            "success": True,
            "progress": progress
        })

    except Exception as e:
        logger.error(f"Swallow progress error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Progress error: {str(e)}")


@app.post("/api/translate/swallow/cancel")
async def cancel_swallow_translation():
    """
    Swallow翻訳処理をキャンセル
    注意: モデルのロードを誘発しないように安全な関数を使用

    Returns:
        キャンセル結果
    """
    try:
        cancelled = cancel_swallow_safe()

        return JSONResponse({
            "success": True,
            "message": "Swallow translation cancellation requested" if cancelled else "No active Swallow translation to cancel"
        })

    except Exception as e:
        logger.error(f"Swallow cancel error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cancel error: {str(e)}")


# ========== エンジン切り替え API ==========

@app.post("/api/engine/switch")
async def switch_translation_engine(data: Dict):
    """
    翻訳エンジンを切り替える
    現在のエンジンのモデルを解放してメモリを開放

    Args:
        data: {"engine": "ollama"|"swallow"|"apple"}

    Returns:
        切り替え結果
    """
    try:
        new_engine = data.get("engine", "ollama")

        logger.info(f"Switching translation engine to: {new_engine}")

        # Swallowモデルを解放（新しいエンジンがSwallow以外の場合）
        if new_engine != "swallow":
            unloaded = unload_swallow_translator()
            if unloaded:
                logger.info("Swallow model unloaded to free memory")

        return JSONResponse({
            "success": True,
            "engine": new_engine,
            "message": f"Engine switched to {new_engine}"
        })

    except Exception as e:
        logger.error(f"Engine switch error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Engine switch error: {str(e)}")


# ========== ヘルパー関数 ==========

def _generate_text_file(
    pages_data: List[Dict],
    format_type: str,
    document_type: str = None,
    translation_engine: str = None,
    ollama_model: str = None
) -> str:
    """
    翻訳結果からテキストファイルを生成

    Args:
        pages_data: ページデータ
        format_type: "original", "translated", "both"
        document_type: 文書タイプ
        translation_engine: 翻訳エンジン
        ollama_model: Ollamaモデル名

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
        'ollama': 'バランス',
        'swallow': '日本語重視',
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
        if translation_engine == 'ollama' and ollama_model:
            lines.append(f"Translation Engine: {engine_display} ({ollama_model})")
        else:
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
