# PDF技術文書 翻訳システム

M4 Pro Mac mini (Apple Silicon)に最適化された、Qwen3/Qwen2.5モデルを使用したPDF技術文書翻訳システムです。

## 主な機能

- **高品質AI翻訳**: Qwen3-14B、Qwen2.5-14B、Qwen2.5-7Bモデルによる3段階の品質設定
- **PDFビューア**: リアルタイムPDFプレビューと翻訳結果の並列表示
- **用語集管理**: カスタム用語集による翻訳精度の向上
- **進捗追跡**: リアルタイム翻訳進捗表示とキャンセル機能
- **ダウンロード機能**: 原文・翻訳・両方の形式でテキストファイル出力
- **Apple Silicon最適化**: MPSデバイスによるGPU高速処理

## 技術スタック

### Frontend
- React 18
- TypeScript
- Vite
- Axios
- react-pdf

### Backend
- Python 3.11+
- FastAPI
- PyTorch (MPS対応)
- Transformers (Hugging Face)
- pdfplumber

## システム要件

- macOS (Apple Silicon推奨)
- Python 3.11以上
- Node.js 18以上
- 16GB以上のメモリ（32GB推奨）

## インストール

### Backend セットアップ

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend セットアップ

```bash
cd frontend
npm install
```

## 起動方法

### Backend起動

```bash
cd backend
source venv/bin/activate
python main.py
```

サーバーは `http://localhost:8002` で起動します。

### Frontend起動

```bash
cd frontend
npm run dev
```

フロントエンドは `http://localhost:5173` で起動します。

## 使い方

1. ブラウザで `http://localhost:5173` にアクセス
2. PDFファイルをドラッグ&ドロップまたは選択してアップロード
3. 翻訳品質を選択（高品質/バランス/高速）
4. 「翻訳を開始」ボタンをクリック
5. 翻訳結果をページごとに確認
6. 必要に応じてテキストファイルとしてダウンロード

## 翻訳品質設定

| 品質 | モデル | 速度 | 品質 | 推奨用途 |
|------|--------|------|------|----------|
| 高品質 | Qwen3-14B | ★☆☆ | ★★★ | 重要文書、公式翻訳 |
| バランス | Qwen2.5-14B | ★★☆ | ★★☆ | 一般的な技術文書 |
| 高速 | Qwen2.5-7B | ★★★ | ★☆☆ | 大量文書、下書き |

## 用語集機能

カスタム用語集により、専門用語や固有名詞の翻訳精度を向上できます。

1. 画面右下の「📚 用語集を開く」ボタンをクリック
2. 英語と日本語のペアを入力して「+ 追加」
3. 翻訳時に自動的に適用されます

## プロジェクト構造

```
PDF_Translation_App/
├── backend/
│   ├── main.py              # FastAPI メインアプリケーション
│   ├── translator.py        # Qwen翻訳エンジン
│   ├── pdf_processor.py     # PDF処理・テキスト抽出
│   ├── requirements.txt     # Python依存パッケージ
│   └── glossary.json        # 用語集データ
├── frontend/
│   ├── src/
│   │   ├── components/      # Reactコンポーネント
│   │   ├── api.ts          # APIクライアント
│   │   └── types.ts        # TypeScript型定義
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## 開発履歴

- Instruct modeサポート
- 文字化け修正機能
- ダウンロード機能（原文/翻訳/両方）
- 用語集管理システム
- 進捗追跡とキャンセル機能
- 品質選択（3モデル対応）
- メモリ最適化（モデル自動アンロード）
- Qwen3思考モード無効化

## ライセンス

MIT License

## 注意事項

- 初回起動時、モデルのダウンロードに時間がかかります（10-20GB）
- Apple Silicon (MPS) での実行を推奨します
- 大容量PDFの翻訳には時間がかかる場合があります
- モデルの切り替え時、古いモデルは自動的にメモリから解放されます
