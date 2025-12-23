#!/bin/bash
# RAG Chatbot Service - Start Script

# ======== 設定 ========
PROJECT_DIR="/Users/altair/PoC/speech_to_minutes"  # ← 環境に合わせて変更
# ======================

cd "$PROJECT_DIR"
source .venv/bin/activate

cd backend

echo "speech_to_minutes server starting..."
echo "URL: http://localhost:8000"
echo "Ctrl+C to stop"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000