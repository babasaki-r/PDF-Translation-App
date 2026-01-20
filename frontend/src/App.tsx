import React, { useState, useEffect, useRef, useCallback } from 'react';
import FileUpload from './components/FileUpload';
import PdfViewer from './components/PdfViewer';
import TranslationPanel from './components/TranslationPanel';
import ControlPanel from './components/ControlPanel';
import GlossaryPanel from './components/GlossaryPanel';
import QuestionPanel from './components/QuestionPanel';
import {
  uploadPDF,
  translatePagesApple, getAppleProgress, cancelAppleTranslation,
  translatePagesOllama, getOllamaProgress, cancelOllamaTranslation,
  translatePagesSwallow, getSwallowProgress, cancelSwallowTranslation,
  getOllamaModels, OllamaModel,
  switchEngine,
  getSwallowStatus, SwallowStatus,
  getOllamaStatus, OllamaStatus
} from './api';
import { PageData, TranslatedPage, TranslationDirection, DocumentType } from './types';

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pagesData, setPagesData] = useState<PageData[]>([]);
  const [translatedPages, setTranslatedPages] = useState<TranslatedPage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [translationProgress, setTranslationProgress] = useState<{
    current: number;
    total: number;
    percentage: number;
  } | null>(null);
  const progressIntervalRef = useRef<number | null>(null);
  const [showQuestionPanel, setShowQuestionPanel] = useState(false);
  const [translationEngine, setTranslationEngine] = useState<'apple' | 'ollama' | 'swallow'>('ollama');
  const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([]);
  const [selectedOllamaModel, setSelectedOllamaModel] = useState<string>('qwen3:4b-instruct');
  const [translationDirection, setTranslationDirection] = useState<TranslationDirection>('en-to-ja');
  const [documentType, setDocumentType] = useState<DocumentType>('steel_technical');
  const [swallowStatus, setSwallowStatus] = useState<SwallowStatus | null>(null);
  const swallowStatusIntervalRef = useRef<number | null>(null);
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus | null>(null);
  const ollamaStatusIntervalRef = useRef<number | null>(null);

  // Ollamaモデル一覧を取得
  useEffect(() => {
    const fetchOllamaModels = async () => {
      try {
        const response = await getOllamaModels();
        if (response.success && response.models.length > 0) {
          setOllamaModels(response.models);
          setSelectedOllamaModel(response.current_model);
        }
      } catch (error) {
        console.log('Ollama not available:', error);
      }
    };
    fetchOllamaModels();
  }, []);

  // Ollamaステータスを取得（Ollamaエンジン選択時のみポーリング）
  useEffect(() => {
    const fetchOllamaStatus = async () => {
      try {
        const status = await getOllamaStatus();
        setOllamaStatus(status);
      } catch (error) {
        console.log('Failed to get Ollama status:', error);
        setOllamaStatus({ success: false, available: false, current_model: '', base_url: '' });
      }
    };

    if (translationEngine === 'ollama') {
      // 初回取得
      fetchOllamaStatus();

      // ポーリング（5秒ごと）
      ollamaStatusIntervalRef.current = window.setInterval(() => {
        fetchOllamaStatus();
      }, 5000);
    } else {
      // Ollama以外のエンジン選択時はステータスをクリア
      setOllamaStatus(null);
      if (ollamaStatusIntervalRef.current) {
        clearInterval(ollamaStatusIntervalRef.current);
        ollamaStatusIntervalRef.current = null;
      }
    }

    return () => {
      if (ollamaStatusIntervalRef.current) {
        clearInterval(ollamaStatusIntervalRef.current);
      }
    };
  }, [translationEngine]);

  // Swallowステータスを取得（Swallowエンジン選択時のみポーリング）
  useEffect(() => {
    const fetchSwallowStatus = async () => {
      try {
        const status = await getSwallowStatus();
        setSwallowStatus(status);
      } catch (error) {
        console.log('Failed to get Swallow status:', error);
        setSwallowStatus({ success: false, loaded: false, loading: false, error: 'ステータス取得失敗' });
      }
    };

    if (translationEngine === 'swallow') {
      // 初回取得
      fetchSwallowStatus();

      // ポーリング（ロード中は頻繁に、それ以外は低頻度）
      swallowStatusIntervalRef.current = window.setInterval(() => {
        fetchSwallowStatus();
      }, swallowStatus?.loading ? 1000 : 5000);
    } else {
      // Swallow以外のエンジン選択時はステータスをクリア
      setSwallowStatus(null);
      if (swallowStatusIntervalRef.current) {
        clearInterval(swallowStatusIntervalRef.current);
        swallowStatusIntervalRef.current = null;
      }
    }

    return () => {
      if (swallowStatusIntervalRef.current) {
        clearInterval(swallowStatusIntervalRef.current);
      }
    };
  }, [translationEngine, swallowStatus?.loading]);

  // エンジン切り替えハンドラー（モデル解放を含む）
  const handleEngineChange = async (engine: 'apple' | 'ollama' | 'swallow') => {
    setTranslationEngine(engine);

    // バックエンドにエンジン切り替えを通知（Swallowモデルを解放）
    try {
      await switchEngine(engine);
      console.log(`Engine switched to: ${engine}`);
    } catch (error) {
      console.error('Failed to switch engine:', error);
    }
  };

  const handleFileSelect = async (selectedFile: File) => {
    setFile(selectedFile);
    setIsUploading(true);
    setError(null);
    setPagesData([]);
    setTranslatedPages([]);
    setCurrentPage(1);

    try {
      const response = await uploadPDF(selectedFile);
      setPagesData(response.pages);
      console.log(`PDF uploaded: ${response.info.pages} pages`);

      // 日本語が含まれている場合は日→英、そうでなければ英→日を初期選択
      if (response.contains_japanese) {
        setTranslationDirection('ja-to-en');
        console.log('Japanese detected, setting direction to ja-to-en');
      } else {
        setTranslationDirection('en-to-ja');
        console.log('No Japanese detected, setting direction to en-to-ja');
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError('PDFのアップロードに失敗しました');
      setFile(null);
    } finally {
      setIsUploading(false);
    }
  };

  // 進捗ポーリング
  useEffect(() => {
    if (isTranslating) {
      // 進捗を定期的に取得（エンジンに応じて異なるAPIを呼び出す）
      progressIntervalRef.current = window.setInterval(async () => {
        try {
          let progress;
          if (translationEngine === 'apple') {
            progress = await getAppleProgress();
          } else if (translationEngine === 'ollama') {
            progress = await getOllamaProgress();
          } else if (translationEngine === 'swallow') {
            progress = await getSwallowProgress();
          } else {
            progress = await getOllamaProgress(); // デフォルト
          }
          setTranslationProgress(progress.progress);
        } catch (error) {
          console.error('Failed to get progress:', error);
        }
      }, 500);
    } else {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      setTranslationProgress(null);
    }

    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, [isTranslating, translationEngine]);

  const handleTranslate = async () => {
    if (pagesData.length === 0) {
      return;
    }

    setIsTranslating(true);
    setError(null);

    try {
      let response;
      if (translationEngine === 'apple') {
        // Apple翻訳はシステムAPIを使用するため文書タイプは適用されない
        response = await translatePagesApple(pagesData, translationDirection);
        console.log('Translation completed with Apple translator, direction:', translationDirection);
      } else if (translationEngine === 'ollama') {
        response = await translatePagesOllama(pagesData, selectedOllamaModel, translationDirection, documentType);
        console.log('Translation completed with Ollama:', selectedOllamaModel, 'direction:', translationDirection, 'docType:', documentType);
      } else if (translationEngine === 'swallow') {
        response = await translatePagesSwallow(pagesData, translationDirection, documentType);
        console.log('Translation completed with Swallow, direction:', translationDirection, 'docType:', documentType);
      } else {
        response = await translatePagesOllama(pagesData, selectedOllamaModel, translationDirection, documentType);
        console.log('Translation completed with Ollama (default):', selectedOllamaModel, 'direction:', translationDirection, 'docType:', documentType);
      }
      setTranslatedPages(response.pages);
    } catch (err) {
      console.error('Translation error:', err);
      setError('翻訳に失敗しました。バックエンドが起動しているか確認してください。');
    } finally {
      setIsTranslating(false);
    }
  };

  const handleCancelTranslation = async () => {
    try {
      if (translationEngine === 'apple') {
        await cancelAppleTranslation();
      } else if (translationEngine === 'ollama') {
        await cancelOllamaTranslation();
      } else if (translationEngine === 'swallow') {
        await cancelSwallowTranslation();
      } else {
        await cancelOllamaTranslation();
      }
      setIsTranslating(false);
      setError('翻訳を中断しました');
    } catch (err) {
      console.error('Cancel error:', err);
      setError('翻訳の中断に失敗しました');
    }
  };

  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  const handleRetranslate = async () => {
    if (pagesData.length === 0) {
      return;
    }

    let engineName;
    if (translationEngine === 'apple') {
      engineName = 'Apple翻訳';
    } else if (translationEngine === 'ollama') {
      engineName = `Ollama(${selectedOllamaModel})`;
    } else if (translationEngine === 'swallow') {
      engineName = 'Swallow';
    } else {
      engineName = 'Ollama';
    }

    const directionLabel = translationDirection === 'en-to-ja' ? '英→日' : '日→英';
    if (!window.confirm(`現在の設定(${engineName}, ${directionLabel})で再翻訳しますか？`)) {
      return;
    }

    setIsTranslating(true);
    setError(null);
    setTranslatedPages([]); // 既存の翻訳をクリア

    try {
      let response;
      if (translationEngine === 'apple') {
        response = await translatePagesApple(pagesData, translationDirection);
      } else if (translationEngine === 'ollama') {
        response = await translatePagesOllama(pagesData, selectedOllamaModel, translationDirection, documentType);
      } else if (translationEngine === 'swallow') {
        response = await translatePagesSwallow(pagesData, translationDirection, documentType);
      } else {
        response = await translatePagesOllama(pagesData, selectedOllamaModel, translationDirection, documentType);
      }
      setTranslatedPages(response.pages);
      console.log('Re-translation completed with direction:', translationDirection, 'docType:', documentType);
    } catch (err) {
      console.error('Re-translation error:', err);
      setError('再翻訳に失敗しました。');
    } finally {
      setIsTranslating(false);
    }
  };

  return (
    <div style={styles.app}>
      {/* ヘッダー */}
      <header style={styles.header}>
        <h1 style={styles.headerTitle}>PDF技術文書 翻訳システム</h1>
        <div style={styles.headerInfo}>
          <button
            onClick={() => window.open('/docs/manual-slides.html', '_blank')}
            style={styles.helpButton}
            title="ヘルプを開く"
          >
            ヘルプ
          </button>
        </div>
      </header>

      {/* メインコンテンツ */}
      <div style={!file ? styles.mainCenter : styles.main}>
        {!file ? (
          // ファイルアップロード画面
          <FileUpload
            onFileSelect={handleFileSelect}
            isLoading={isUploading}
            documentType={documentType}
            onDocumentTypeChange={setDocumentType}
          />
        ) : (
          // 並列表示画面
          <>
            {/* 左側: PDFビューア */}
            <div style={styles.leftPanel}>
              <PdfViewer
                file={file}
                currentPage={currentPage}
                onPageChange={handlePageChange}
              />
            </div>

            {/* 右側: 翻訳パネル */}
            <div style={styles.rightPanel}>
              {/* コントロールパネル */}
              {pagesData.length > 0 && (
                <ControlPanel
                  translatedPages={translatedPages}
                  currentPage={currentPage}
                  translationProgress={translationProgress}
                  isTranslating={isTranslating}
                  translationEngine={translationEngine}
                  onEngineChange={handleEngineChange}
                  translationDirection={translationDirection}
                  onDirectionChange={setTranslationDirection}
                  ollamaModels={ollamaModels}
                  selectedOllamaModel={selectedOllamaModel}
                  onOllamaModelChange={setSelectedOllamaModel}
                  documentType={documentType}
                  onDocumentTypeChange={setDocumentType}
                  swallowStatus={swallowStatus}
                  ollamaStatus={ollamaStatus}
                />
              )}

              <TranslationPanel
                translatedPages={translatedPages}
                currentPage={currentPage}
                isTranslating={isTranslating}
                translationEngine={translationEngine}
                ollamaModel={selectedOllamaModel}
                translationDirection={translationDirection}
              />
            </div>
          </>
        )}
      </div>

      {/* 下部コントロール */}
      {file && (
        <div style={styles.controls}>
          <button
            onClick={() => {
              setFile(null);
              setPagesData([]);
              setTranslatedPages([]);
              setCurrentPage(1);
              setError(null);
            }}
            style={styles.secondaryButton}
          >
            別のファイルを選択
          </button>

          {pagesData.length > 0 && translatedPages.length === 0 && !isTranslating && (
            <button
              onClick={handleTranslate}
              style={styles.primaryButton}
              disabled={isTranslating}
            >
              翻訳を開始
            </button>
          )}

          {isTranslating && (
            <button
              onClick={handleCancelTranslation}
              style={styles.cancelButton}
            >
              処理中止
            </button>
          )}

          {translatedPages.length > 0 && !isTranslating && (
            <>
              <div style={styles.successMessage}>
                ✓ 翻訳完了 ({translatedPages.length} ページ)
              </div>
              <button
                onClick={handleRetranslate}
                style={styles.retranslateButton}
                title="現在の設定で再翻訳"
              >
                再翻訳
              </button>
            </>
          )}
        </div>
      )}

      {/* 用語集パネル */}
      <GlossaryPanel />

      {/* 質問ボタン */}
      {pagesData.length > 0 && (
        <button
          onClick={() => setShowQuestionPanel(true)}
          style={styles.questionButton}
          title="PDFの内容について質問"
        >
          ?
        </button>
      )}

      {/* 質問パネル */}
      <QuestionPanel
        pdfContent={pagesData.map(p => p.text).join('\n\n')}
        isVisible={showQuestionPanel}
        onClose={() => setShowQuestionPanel(false)}
      />

      {/* エラー表示 */}
      {error && (
        <div style={styles.error}>
          <strong>エラー:</strong> {error}
        </div>
      )}
    </div>
  );
}

const styles = {
  app: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100vh',
    backgroundColor: '#f5f5f5',
  } as React.CSSProperties,
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 24px',
    backgroundColor: '#2d3748',
    color: 'white',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  } as React.CSSProperties,
  headerTitle: {
    fontSize: '20px',
    fontWeight: 'bold' as const,
    margin: 0,
  } as React.CSSProperties,
  headerInfo: {
    display: 'flex',
    gap: '8px',
  } as React.CSSProperties,
  main: {
    flex: 1,
    display: 'flex',
    overflow: 'auto',
    minHeight: 0,
  } as React.CSSProperties,
  mainCenter: {
    flex: 1,
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'auto',
    minHeight: 0,
  } as React.CSSProperties,
  leftPanel: {
    flex: 1,
    borderRight: '2px solid #e2e8f0',
    overflow: 'hidden',
  } as React.CSSProperties,
  rightPanel: {
    flex: 1,
    overflow: 'auto',
    display: 'flex',
    flexDirection: 'column' as const,
  } as React.CSSProperties,
  controls: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '16px',
    padding: '12px 16px',
    backgroundColor: 'white',
    borderTop: '2px solid #e2e8f0',
    boxShadow: '0 -2px 4px rgba(0,0,0,0.05)',
  } as React.CSSProperties,
  primaryButton: {
    padding: '10px 28px',
    backgroundColor: '#3182ce',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '15px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  } as React.CSSProperties,
  secondaryButton: {
    padding: '10px 20px',
    backgroundColor: '#718096',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  } as React.CSSProperties,
  cancelButton: {
    padding: '10px 20px',
    backgroundColor: '#e53e3e',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  } as React.CSSProperties,
  retranslateButton: {
    padding: '10px 16px',
    backgroundColor: '#dd6b20',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  } as React.CSSProperties,
  successMessage: {
    color: '#38a169',
    fontWeight: 'bold' as const,
    fontSize: '14px',
  } as React.CSSProperties,
  error: {
    position: 'fixed' as const,
    bottom: '80px',
    left: '50%',
    transform: 'translateX(-50%)',
    padding: '16px',
    backgroundColor: '#fc8181',
    color: 'white',
    borderRadius: '6px',
    boxShadow: '0 4px 8px rgba(0,0,0,0.2)',
    maxWidth: '400px',
    zIndex: 1100,
  } as React.CSSProperties,
  questionButton: {
    position: 'fixed' as const,
    bottom: '100px',
    right: '30px',
    width: '50px',
    height: '50px',
    borderRadius: '50%',
    backgroundColor: '#805ad5',
    color: 'white',
    border: 'none',
    fontSize: '24px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    boxShadow: '0 4px 12px rgba(128, 90, 213, 0.4)',
    transition: 'all 0.2s',
    zIndex: 900,
  } as React.CSSProperties,
  helpButton: {
    padding: '6px 14px',
    backgroundColor: '#48bb78',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  } as React.CSSProperties,
};

export default App;
