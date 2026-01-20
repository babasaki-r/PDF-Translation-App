# PDF翻訳システム - セットアップガイド

このドキュメントでは、他のMacでPDF翻訳システムをセットアップするために必要な環境とライブラリについて説明します。

## 目次
1. [システム要件](#システム要件)
2. [事前準備](#事前準備)
3. [セットアップ手順](#セットアップ手順)
4. [依存ライブラリ一覧](#依存ライブラリ一覧)
5. [トラブルシューティング](#トラブルシューティング)

---

## システム要件

### ハードウェア
| 項目 | 最小要件 | 推奨要件 |
|------|---------|---------|
| Mac | Apple Silicon (M1以降) | M1 Pro以上 |
| メモリ | 16GB | 32GB以上 |
| ストレージ | 20GB空き | 50GB以上 |

### ソフトウェア
| 項目 | バージョン | 備考 |
|------|-----------|------|
| macOS | 14.0 (Sonoma) 以上 | Apple翻訳は 15.0 (Sequoia) 以上 |
| Python | 3.9 以上 | 3.11 推奨 |
| Node.js | 18 以上 | 20 LTS 推奨 |
| Ollama | 最新版 | バランス翻訳に必要 |

---

## 事前準備

### 1. Homebrew のインストール
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Apple Silicon Macの場合、PATHを設定
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

### 2. Ollama のインストール（バランス翻訳に必要）
```bash
# Homebrewでインストール
brew install ollama

# または公式サイトからダウンロード
# https://ollama.ai/

# インストール後、モデルをダウンロード
ollama pull qwen3:4b
```

---

## セットアップ手順

### 自動セットアップ（推奨）
```bash
# プロジェクトディレクトリに移動
cd PDF_Translation_App

# セットアップスクリプトを実行
./setup.sh
```

### 手動セットアップ

#### 1. Python環境のセットアップ
```bash
# Python 3.11をインストール
brew install python@3.11

# バックエンドディレクトリに移動
cd backend

# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate

# 依存関係をインストール
pip install --upgrade pip
pip install -r requirements.txt

# データディレクトリを作成
mkdir -p data
```

#### 2. Node.js環境のセットアップ
```bash
# Node.js 20をインストール
brew install node@20

# フロントエンドディレクトリに移動
cd frontend

# 依存関係をインストール
npm install
```

#### 3. 起動スクリプトに実行権限を付与
```bash
chmod +x start.sh stop.sh setup.sh
```

---

## 依存ライブラリ一覧

### Backend (Python) - requirements.txt

```
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
aiofiles==23.2.1
python-dotenv==1.0.0

# PDF処理
PyPDF2==3.0.1
pdfplumber==0.10.3
PyMuPDF>=1.23.0

# LLM推論 (Swallow/日本語重視)
transformers>=4.36.0
torch>=2.1.0
accelerate==0.25.0
bitsandbytes>=0.41.0
sentencepiece>=0.1.99
protobuf==4.25.1
optimum>=1.16.0
```

### Frontend (Node.js) - package.json dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-pdf": "^7.5.1",
    "pdfjs-dist": "^3.11.174",
    "axios": "^1.6.2",
    "zustand": "^4.4.7"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@typescript-eslint/eslint-plugin": "^6.14.0",
    "@typescript-eslint/parser": "^6.14.0",
    "@vitejs/plugin-react": "^4.2.1",
    "eslint": "^8.55.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.5",
    "typescript": "^5.2.2",
    "vite": "^5.0.8"
  }
}
```

### 外部サービス

| サービス | 用途 | インストール方法 |
|---------|------|----------------|
| Ollama | バランス翻訳 (LLM推論) | `brew install ollama` |
| Xcode Command Line Tools | Swiftコンパイル (Apple翻訳) | `xcode-select --install` |

---

## Ollamaモデル

バランス翻訳で使用するモデルをダウンロードしてください。

```bash
# 推奨モデル（軽量・高速）
ollama pull qwen3:4b

# オプション：追加モデル
ollama pull qwen2.5:7b
ollama pull llama3.1:8b
ollama pull qwen3:14b
```

---

## ディレクトリ構造

セットアップ後のディレクトリ構造：

```
PDF_Translation_App/
├── backend/
│   ├── main.py              # FastAPI アプリケーション
│   ├── translator.py        # 翻訳エンジン
│   ├── pdf_processor.py     # PDF処理
│   ├── prompts.json         # 文書タイプ別プロンプト
│   ├── apple_translate.swift # Apple翻訳スクリプト
│   ├── requirements.txt     # Python依存関係
│   ├── data/
│   │   └── glossary.json    # 用語集データ（自動作成）
│   └── venv/                # Python仮想環境（自動作成）
├── frontend/
│   ├── src/                 # Reactソースコード
│   ├── public/              # 静的ファイル
│   ├── package.json         # Node.js依存関係
│   └── node_modules/        # npmパッケージ（自動作成）
├── docs/                    # ドキュメント
├── logs/                    # ログファイル（自動作成）
├── start.sh                 # 起動スクリプト
├── stop.sh                  # 停止スクリプト
└── setup.sh                 # セットアップスクリプト
```

---

## 起動と停止

### 起動
```bash
# Ollamaサーバーを起動（別ターミナルで実行）
ollama serve

# アプリを起動
./start.sh

# ブラウザで自動的に開きます: http://localhost:5173
```

### 停止
```bash
./stop.sh
```

---

## トラブルシューティング

### 1. pip install でエラーが発生する

**症状**: `bitsandbytes` や `torch` のインストールに失敗する

**解決策**:
```bash
# Apple Silicon用のPyTorchを明示的にインストール
pip install torch torchvision torchaudio

# その後、requirements.txtを再実行
pip install -r requirements.txt
```

### 2. Ollamaに接続できない

**症状**: 「バランスが利用できない」エラー

**解決策**:
```bash
# Ollamaサーバーが起動しているか確認
ollama serve

# モデルがダウンロードされているか確認
ollama list

# モデルをダウンロード
ollama pull qwen3:4b
```

### 3. Apple翻訳が動作しない

**症状**: 「簡易翻訳」でエラーが発生する

**解決策**:
- macOS 15.0 (Sequoia) 以上が必要です
- Xcode Command Line Toolsをインストール:
  ```bash
  xcode-select --install
  ```

### 4. メモリ不足エラー

**症状**: 翻訳中にクラッシュする

**解決策**:
- 「日本語重視」(Swallow) は約8GBのメモリを使用します
- メモリが不足する場合は「バランス」または「簡易翻訳」を使用してください
- エンジンを切り替えると自動的にメモリが解放されます

### 5. PDFが表示されない

**症状**: PDFをアップロードしても表示されない

**解決策**:
```bash
# フロントエンドを再ビルド
cd frontend
npm run build
```

---

## バージョン情報

- システムバージョン: 2.2.0
- 最終更新: 2026-01-14

## 変更履歴

### v2.2.0 (2026-01-14)
- 文書タイプ選択機能を追加
- 翻訳エンジン表示名を変更（バランス/日本語重視/簡易翻訳）
- ダウンロードファイルに文書タイプ・エンジン情報を追加
- PDFビューアのちらつき修正

### v2.1.0 (2025-12-25)
- Apple翻訳サポートを追加
- OCRサポートを追加
- メモリ最適化
