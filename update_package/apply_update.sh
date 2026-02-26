#!/bin/bash
# ===================================================
# PDF Translation App - MLX移行アップデート適用スクリプト
#
# 変更内容:
#   1. Swallow/Ollama翻訳エンジンを廃止
#   2. MLXサーバー(Qwen2.5-7B-Instruct-4bit)に統一
#   3. エンジン選択を「AI翻訳」と「簡易翻訳」に簡素化
#   4. 不要な依存パッケージ(torch, transformers等)を削除
# ===================================================

set -e

# 色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  PDF Translation App MLX移行アップデート"
echo "=========================================="
echo ""

# このスクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# PDF_Translation_Appのルートディレクトリを探す
if [ -f "$SCRIPT_DIR/../backend/main.py" ]; then
    PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ -f "$SCRIPT_DIR/backend/main.py" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
else
    echo -e "${YELLOW}PDF_Translation_Appのフォルダパスを入力してください:${NC}"
    read -r PROJECT_DIR
    if [ ! -f "$PROJECT_DIR/backend/main.py" ]; then
        echo -e "${RED}エラー: 指定されたパスにPDF Translation Appが見つかりません${NC}"
        exit 1
    fi
fi

echo -e "プロジェクトフォルダ: ${GREEN}$PROJECT_DIR${NC}"
echo ""

# バックアップ作成
BACKUP_DIR="$PROJECT_DIR/backup_$(date +%Y%m%d_%H%M%S)"
echo -e "${YELLOW}[1/5] バックアップ作成中...${NC}"
mkdir -p "$BACKUP_DIR/backend" "$BACKUP_DIR/frontend/src/components"
cp "$PROJECT_DIR/backend/main.py" "$BACKUP_DIR/backend/" 2>/dev/null || true
cp "$PROJECT_DIR/backend/translator.py" "$BACKUP_DIR/backend/" 2>/dev/null || true
cp "$PROJECT_DIR/backend/requirements.txt" "$BACKUP_DIR/backend/" 2>/dev/null || true
cp "$PROJECT_DIR/frontend/src/App.tsx" "$BACKUP_DIR/frontend/src/" 2>/dev/null || true
cp "$PROJECT_DIR/frontend/src/api.ts" "$BACKUP_DIR/frontend/src/" 2>/dev/null || true
cp "$PROJECT_DIR/frontend/src/types.ts" "$BACKUP_DIR/frontend/src/" 2>/dev/null || true
cp "$PROJECT_DIR/frontend/src/components/ControlPanel.tsx" "$BACKUP_DIR/frontend/src/components/" 2>/dev/null || true
cp "$PROJECT_DIR/frontend/src/components/TranslationPanel.tsx" "$BACKUP_DIR/frontend/src/components/" 2>/dev/null || true
cp "$PROJECT_DIR/frontend/src/components/QuestionPanel.tsx" "$BACKUP_DIR/frontend/src/components/" 2>/dev/null || true
echo -e "  バックアップ先: ${GREEN}$BACKUP_DIR${NC}"

# 不要ファイルの削除
echo ""
echo -e "${YELLOW}[2/5] 不要ファイルを削除中...${NC}"
if [ -f "$PROJECT_DIR/backend/translator_mlx.py" ]; then
    rm "$PROJECT_DIR/backend/translator_mlx.py"
    echo "  - backend/translator_mlx.py 削除完了"
fi

# ファイルコピー
echo ""
echo -e "${YELLOW}[3/5] ファイルを更新中...${NC}"
cp "$SCRIPT_DIR/backend/main.py" "$PROJECT_DIR/backend/main.py"
echo "  - backend/main.py 更新完了"
cp "$SCRIPT_DIR/backend/translator.py" "$PROJECT_DIR/backend/translator.py"
echo "  - backend/translator.py 更新完了"
cp "$SCRIPT_DIR/backend/requirements.txt" "$PROJECT_DIR/backend/requirements.txt"
echo "  - backend/requirements.txt 更新完了"
cp "$SCRIPT_DIR/frontend/src/App.tsx" "$PROJECT_DIR/frontend/src/App.tsx"
echo "  - frontend/src/App.tsx 更新完了"
cp "$SCRIPT_DIR/frontend/src/api.ts" "$PROJECT_DIR/frontend/src/api.ts"
echo "  - frontend/src/api.ts 更新完了"
cp "$SCRIPT_DIR/frontend/src/types.ts" "$PROJECT_DIR/frontend/src/types.ts"
echo "  - frontend/src/types.ts 更新完了"
cp "$SCRIPT_DIR/frontend/src/components/ControlPanel.tsx" "$PROJECT_DIR/frontend/src/components/ControlPanel.tsx"
echo "  - frontend/src/components/ControlPanel.tsx 更新完了"
cp "$SCRIPT_DIR/frontend/src/components/TranslationPanel.tsx" "$PROJECT_DIR/frontend/src/components/TranslationPanel.tsx"
echo "  - frontend/src/components/TranslationPanel.tsx 更新完了"
cp "$SCRIPT_DIR/frontend/src/components/QuestionPanel.tsx" "$PROJECT_DIR/frontend/src/components/QuestionPanel.tsx"
echo "  - frontend/src/components/QuestionPanel.tsx 更新完了"

# フロントエンドビルド
echo ""
echo -e "${YELLOW}[4/5] フロントエンドをビルド中...${NC}"
cd "$PROJECT_DIR/frontend"
if command -v npm &> /dev/null; then
    npm run build 2>&1 | tail -5
    echo -e "  ${GREEN}ビルド完了${NC}"
else
    echo -e "  ${RED}npmが見つかりません。手動でビルドしてください: cd frontend && npm run build${NC}"
fi

echo ""
echo -e "${YELLOW}[5/5] 完了${NC}"
echo ""
echo "=========================================="
echo -e "  ${GREEN}MLX移行アップデート適用完了！${NC}"
echo "=========================================="
echo ""
echo "重要: MLXサーバーの起動が必要です："
echo "  mlx_lm.server --model mlx-community/Qwen2.5-7B-Instruct-4bit"
echo ""
echo "バックエンドを再起動してください。"
echo "  例: バックエンドのターミナルでCtrl+Cで停止後、再度起動"
echo ""
echo "問題が発生した場合はバックアップから復元できます:"
echo "  cp $BACKUP_DIR/backend/* $PROJECT_DIR/backend/"
echo "  cp $BACKUP_DIR/frontend/src/* $PROJECT_DIR/frontend/src/"
echo "  cp $BACKUP_DIR/frontend/src/components/* $PROJECT_DIR/frontend/src/components/"
echo ""
