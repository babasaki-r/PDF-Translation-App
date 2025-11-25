#!/bin/bash

# PDF Translation App - セットアップスクリプト
# 初回セットアップ用：依存関係のインストールを行います

set -e

# カラー出力用
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PDF Translation App - セットアップ${NC}"
echo -e "${BLUE}========================================${NC}"

# カレントディレクトリをスクリプトの場所に変更
cd "$(dirname "$0")"

# ログディレクトリ作成
echo -e "\n${GREEN}ログディレクトリを作成中...${NC}"
mkdir -p logs

# Python確認
echo -e "\n${GREEN}[1/4] Python環境を確認中...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}エラー: Python3が見つかりません${NC}"
    echo -e "${YELLOW}Python3をインストールしてください${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python3: $(python3 --version)${NC}"

# Node.js確認
echo -e "\n${GREEN}[2/4] Node.js環境を確認中...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}エラー: Node.jsが見つかりません${NC}"
    echo -e "${YELLOW}Node.jsをインストールしてください${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js: $(node --version)${NC}"
echo -e "${GREEN}✓ npm: $(npm --version)${NC}"

# バックエンドセットアップ
echo -e "\n${GREEN}[3/4] バックエンドをセットアップ中...${NC}"
cd backend

# 仮想環境作成
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}仮想環境を作成中...${NC}"
    python3 -m venv venv
fi

# 依存関係インストール
echo -e "${YELLOW}依存関係をインストール中... (時間がかかります)${NC}"
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo -e "${GREEN}✓ バックエンドのセットアップ完了${NC}"
cd ..

# フロントエンドセットアップ
echo -e "\n${GREEN}[4/4] フロントエンドをセットアップ中...${NC}"
cd frontend

# 依存関係インストール
echo -e "${YELLOW}依存関係をインストール中...${NC}"
npm install

echo -e "${GREEN}✓ フロントエンドのセットアップ完了${NC}"
cd ..

# セットアップ完了
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✓ セットアップ完了！${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e ""
echo -e "${YELLOW}次のコマンドでアプリケーションを起動してください:${NC}"
echo -e "  ${GREEN}./start.sh${NC}"
echo -e ""
echo -e "${BLUE}========================================${NC}"
