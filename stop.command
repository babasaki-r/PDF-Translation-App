#!/bin/bash

# PDF Translation App - 停止スクリプト
# 起動中のバックエンドとフロントエンドを停止します

set -e

# カラー出力用
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PDF Translation App - 停止中...${NC}"
echo -e "${BLUE}========================================${NC}"

# カレントディレクトリをスクリプトの場所に変更
cd "$(dirname "$0")"

STOPPED=0

# PIDファイルから停止
if [ -d ".pids" ]; then
    if [ -f ".pids/backend.pid" ]; then
        BACKEND_PID=$(cat .pids/backend.pid)
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            echo -e "${YELLOW}バックエンド (PID: $BACKEND_PID) を停止中...${NC}"
            kill $BACKEND_PID 2>/dev/null || true
            STOPPED=1
        fi
        rm .pids/backend.pid
    fi

    if [ -f ".pids/frontend.pid" ]; then
        FRONTEND_PID=$(cat .pids/frontend.pid)
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            echo -e "${YELLOW}フロントエンド (PID: $FRONTEND_PID) を停止中...${NC}"
            kill $FRONTEND_PID 2>/dev/null || true
            STOPPED=1
        fi
        rm .pids/frontend.pid
    fi
fi

# ポートベースで停止（念のため）
if lsof -ti:8002 > /dev/null 2>&1; then
    echo -e "${YELLOW}ポート8002で実行中のプロセスを停止中...${NC}"
    lsof -ti:8002 | xargs kill -9 2>/dev/null || true
    STOPPED=1
fi

if lsof -ti:5173 > /dev/null 2>&1; then
    echo -e "${YELLOW}ポート5173で実行中のプロセスを停止中...${NC}"
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true
    STOPPED=1
fi

# 結果表示
echo -e "\n${BLUE}========================================${NC}"
if [ $STOPPED -eq 1 ]; then
    echo -e "${GREEN}✓ 停止完了！${NC}"
else
    echo -e "${YELLOW}実行中のプロセスは見つかりませんでした${NC}"
fi
echo -e "${BLUE}========================================${NC}"
