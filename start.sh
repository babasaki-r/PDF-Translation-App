#!/bin/bash

# PDF Translation App - 起動スクリプト
# このスクリプト1つで、バックエンドとフロントエンドを同時に起動します

set -e

# カラー出力用
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PDF Translation App - 起動中...${NC}"
echo -e "${BLUE}========================================${NC}"

# カレントディレクトリをスクリプトの場所に変更
cd "$(dirname "$0")"

# 既存のプロセスを確認して停止
echo -e "\n${YELLOW}既存のプロセスを確認中...${NC}"
if lsof -ti:8002 > /dev/null 2>&1; then
    echo -e "${YELLOW}ポート8002で実行中のプロセスを停止します...${NC}"
    lsof -ti:8002 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

if lsof -ti:5173 > /dev/null 2>&1; then
    echo -e "${YELLOW}ポート5173で実行中のプロセスを停止します...${NC}"
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# バックエンドの起動
echo -e "\n${GREEN}[1/2] バックエンドを起動中...${NC}"
cd backend

# 仮想環境の確認
if [ ! -d "venv" ]; then
    echo -e "${RED}エラー: 仮想環境が見つかりません${NC}"
    echo -e "${YELLOW}セットアップを実行してください: ./setup.sh${NC}"
    exit 1
fi

# バックエンド起動（バックグラウンド）
PORT=8002 ./venv/bin/python main.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}バックエンドを起動しました (PID: $BACKEND_PID, ポート: 8002)${NC}"

cd ..

# フロントエンドの起動
echo -e "\n${GREEN}[2/2] フロントエンドを起動中...${NC}"
cd frontend

# node_modulesの確認
if [ ! -d "node_modules" ]; then
    echo -e "${RED}エラー: node_modulesが見つかりません${NC}"
    echo -e "${YELLOW}セットアップを実行してください: ./setup.sh${NC}"
    exit 1
fi

# フロントエンド起動（バックグラウンド）
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}フロントエンドを起動しました (PID: $FRONTEND_PID, ポート: 5173)${NC}"

cd ..

# 起動完了メッセージ
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✓ 起動完了！${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e ""
echo -e "  📱 フロントエンド: ${GREEN}http://localhost:5173${NC}"
echo -e "  🔧 バックエンド:   ${GREEN}http://localhost:8002${NC}"
echo -e ""
echo -e "  プロセスID:"
echo -e "    バックエンド:  ${BACKEND_PID}"
echo -e "    フロントエンド: ${FRONTEND_PID}"
echo -e ""
echo -e "${YELLOW}停止するには: ./stop.sh を実行してください${NC}"
echo -e ""
echo -e "ログファイル:"
echo -e "  バックエンド:  logs/backend.log"
echo -e "  フロントエンド: logs/frontend.log"
echo -e ""
echo -e "${BLUE}========================================${NC}"

# PIDをファイルに保存（停止スクリプト用）
mkdir -p .pids
echo $BACKEND_PID > .pids/backend.pid
echo $FRONTEND_PID > .pids/frontend.pid
