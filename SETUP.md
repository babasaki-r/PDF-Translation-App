# PDF Translation App - セットアップガイド

## 新しいMacでのセットアップ手順

### クイックスタート（3ステップ）

```bash
# 1. プロジェクトをコピー（USBメモリ、AirDrop、Git等）
# 例: USBメモリからコピーした場合
cp -r /Volumes/USBメモリ/PDF_Translation_App ~/PDF_Translation_App

# 2. セットアップ実行
cd ~/PDF_Translation_App
./setup.sh

# 3. アプリ起動
./start.sh
```

これだけでセットアップ完了です！

---

## 詳細説明

### 動作環境

- **OS**: macOS (Apple Silicon M1/M2/M3/M4 推奨)
- **メモリ**: 16GB以上推奨（8GBでも動作可能）
- **ストレージ**: 20GB以上の空き容量

### セットアップスクリプトが自動でインストールするもの

1. **Homebrew** - macOSのパッケージマネージャー
2. **Python 3.11** - バックエンド用
3. **Node.js 20** - フロントエンド用
4. **Pythonパッケージ** - PyTorch, Transformers等
5. **npmパッケージ** - React, Vite等

### 初回起動時の注意

初回起動時にAIモデル（Qwen2.5-7B、約14GB）を自動ダウンロードします。
- ダウンロード時間: 10〜30分程度（回線速度による）
- ダウンロード先: `~/.cache/huggingface/`

### コマンド一覧

| コマンド | 説明 |
|---------|------|
| `./setup.sh` | 初回セットアップ |
| `./start.sh` | アプリ起動 |
| `./stop.sh` | アプリ停止 |

### 起動後のアクセス

- **フロントエンド**: http://localhost:5173
- **バックエンドAPI**: http://localhost:8002

---

## LLMモデルごと移植する方法（推奨）

モデルのダウンロードをスキップしたい場合は、Hugging Faceのキャッシュも一緒にコピーします。

### コピーするもの

| 項目 | パス | サイズ |
|------|------|--------|
| プロジェクト | `~/PDF_Translation_App/` | 約500MB |
| LLMモデル（balanced） | `~/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct` | 約14GB |

### 手順

#### 移行元PC（このPC）での作業

```bash
# USBメモリにコピー（約15GB必要）

# 1. プロジェクトフォルダをコピー
cp -r ~/PDF_Translation_App /Volumes/USBメモリ/

# 2. LLMモデルをコピー（balancedモードのみ）
mkdir -p /Volumes/USBメモリ/huggingface_cache/hub
cp -r ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct \
      /Volumes/USBメモリ/huggingface_cache/hub/
```

#### 移行先PC（新しいMac）での作業

```bash
# 1. プロジェクトをコピー
cp -r /Volumes/USBメモリ/PDF_Translation_App ~/

# 2. LLMモデルを配置
mkdir -p ~/.cache/huggingface/hub
cp -r /Volumes/USBメモリ/huggingface_cache/hub/models--Qwen--Qwen2.5-7B-Instruct \
      ~/.cache/huggingface/hub/

# 3. セットアップ実行（Pythonパッケージのみインストール）
cd ~/PDF_Translation_App
./setup.sh

# 4. アプリ起動（モデルダウンロードがスキップされる）
./start.sh
```

### 全モデルをコピーする場合（high/balanced/fast全対応）

全ての品質モードに対応したい場合は、キャッシュ全体をコピーします。

```bash
# 移行元PC
cp -r ~/.cache/huggingface /Volumes/USBメモリ/huggingface_cache

# 移行先PC
cp -r /Volumes/USBメモリ/huggingface_cache ~/.cache/huggingface
```

※ 全キャッシュは約88GBあります

### モデルサイズ一覧

| 品質モード | モデル名 | サイズ |
|-----------|---------|--------|
| fast | Qwen2.5-3B-Instruct | 約6GB |
| balanced | Qwen2.5-7B-Instruct | 約14GB |
| high | Qwen3-14B | 約28GB |

---

## トラブルシューティング

### セットアップが失敗する場合

```bash
# Homebrewを手動でインストール
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# その後、再度セットアップ
./setup.sh
```

### 起動しない場合

```bash
# プロセスを強制停止
./stop.sh

# ログを確認
cat logs/backend.log
cat logs/frontend.log
```

### ポートが使用中の場合

```bash
# ポート8002を使用しているプロセスを確認・停止
lsof -i :8002
kill -9 <PID>

# ポート5173を使用しているプロセスを確認・停止
lsof -i :5173
kill -9 <PID>
```

---

## ファイル構成

```
PDF_Translation_App/
├── setup.sh          # セットアップスクリプト
├── start.sh          # 起動スクリプト
├── stop.sh           # 停止スクリプト
├── SETUP.md          # このファイル
├── backend/          # バックエンド（Python/FastAPI）
│   ├── main.py
│   ├── translator.py
│   ├── requirements.txt
│   └── data/         # 用語集等のデータ
├── frontend/         # フロントエンド（React/TypeScript）
│   ├── src/
│   └── package.json
└── logs/             # ログファイル
```

---

## 別のMacへの移行チェックリスト

- [ ] プロジェクトフォルダをコピー
- [ ] LLMモデルキャッシュをコピー（オプション）
- [ ] 新しいMacで `./setup.sh` を実行
- [ ] `./start.sh` で起動確認
- [ ] 用語集（`backend/data/glossary.json`）が引き継がれていることを確認
