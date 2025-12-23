#!/bin/bash

# PDF Translation App - セットアップスクリプト
# 新しいMacでワンクリックでセットアップを完了します

set -e

# カラー出力用
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PDF Translation App - セットアップ${NC}"
echo -e "${BLUE}========================================${NC}"

# カレントディレクトリをスクリプトの場所に変更
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "作業ディレクトリ: $SCRIPT_DIR"

# ログディレクトリ作成
mkdir -p logs

# ====================================
# 1. Homebrewの確認とインストール
# ====================================
echo -e "\n${GREEN}[1/5] Homebrewを確認中...${NC}"
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Homebrewをインストール中...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Apple Silicon Macの場合、PATHを設定
    if [[ $(uname -m) == 'arm64' ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
    echo -e "${GREEN}✓ Homebrewをインストールしました${NC}"
else
    echo -e "${GREEN}✓ Homebrew: インストール済み${NC}"
fi

# ====================================
# 2. Python確認とインストール
# ====================================
echo -e "\n${GREEN}[2/5] Python環境を確認中...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python 3をインストール中...${NC}"
    brew install python@3.11
    echo -e "${GREEN}✓ Python 3をインストールしました${NC}"
else
    echo -e "${GREEN}✓ Python3: $(python3 --version)${NC}"
fi

# ====================================
# 3. Node.js確認とインストール
# ====================================
echo -e "\n${GREEN}[3/5] Node.js環境を確認中...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}Node.jsをインストール中...${NC}"
    brew install node@20
    echo -e "${GREEN}✓ Node.jsをインストールしました${NC}"
else
    echo -e "${GREEN}✓ Node.js: $(node --version)${NC}"
    echo -e "${GREEN}✓ npm: $(npm --version)${NC}"
fi

# ====================================
# 4. バックエンドセットアップ
# ====================================
echo -e "\n${GREEN}[4/5] バックエンドをセットアップ中...${NC}"
cd backend

# 仮想環境作成
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}仮想環境を作成中...${NC}"
    python3 -m venv venv
fi

# データディレクトリ作成
mkdir -p data

# 依存関係インストール
echo -e "${YELLOW}Pythonパッケージをインストール中...${NC}"
echo -e "${YELLOW}（初回は10〜30分程度かかります）${NC}"
./venv/bin/pip install --upgrade pip > /dev/null 2>&1
./venv/bin/pip install -r requirements.txt

echo -e "${GREEN}✓ バックエンドのセットアップ完了${NC}"
cd ..

# ====================================
# 5. フロントエンドセットアップ
# ====================================
echo -e "\n${GREEN}[5/5] フロントエンドをセットアップ中...${NC}"
cd frontend

echo -e "${YELLOW}npmパッケージをインストール中...${NC}"
npm install

echo -e "${GREEN}✓ フロントエンドのセットアップ完了${NC}"
cd ..

# 実行権限を付与
chmod +x start.sh stop.sh setup.sh 2>/dev/null || true

# ====================================
# セットアップ完了
# ====================================
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✓ セットアップ完了！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "アプリを起動するには:"
echo -e "  ${GREEN}./start.sh${NC}"
echo ""
echo -e "停止するには:"
echo -e "  ${GREEN}./stop.sh${NC}"
echo ""
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}注意:${NC}"
echo -e "  初回起動時にAIモデル（約14GB）をダウンロードします"
echo -e "  ダウンロードには10〜30分程度かかる場合があります"
echo ""
