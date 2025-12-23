import React, { useState, useEffect, useRef } from 'react';
import FileUpload from './components/FileUpload';
import PdfViewer from './components/PdfViewer';
import TranslationPanel from './components/TranslationPanel';
import ControlPanel from './components/ControlPanel';
import GlossaryPanel from './components/GlossaryPanel';
import QuestionPanel from './components/QuestionPanel';
import { uploadPDF, translatePages, getProgress, cancelTranslation, translatePagesApple, getAppleProgress, cancelAppleTranslation } from './api';
import { PageData, TranslatedPage } from './types';

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pagesData, setPagesData] = useState<PageData[]>([]);
  const [translatedPages, setTranslatedPages] = useState<TranslatedPage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedQuality, setSelectedQuality] = useState('fast');
  const [translationProgress, setTranslationProgress] = useState<{
    current: number;
    total: number;
    percentage: number;
  } | null>(null);
  const progressIntervalRef = useRef<number | null>(null);
  const [showQuestionPanel, setShowQuestionPanel] = useState(false);
  const [translationEngine, setTranslationEngine] = useState<'llm' | 'apple'>('llm');

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
          const progress = translationEngine === 'apple'
            ? await getAppleProgress()
            : await getProgress();
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
        response = await translatePagesApple(pagesData);
        console.log('Translation completed with Apple translator');
      } else {
        response = await translatePages(pagesData, selectedQuality);
        console.log('Translation completed with quality:', selectedQuality);
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
      } else {
        await cancelTranslation();
      }
      setIsTranslating(false);
      setError('翻訳を中断しました');
    } catch (err) {
      console.error('Cancel error:', err);
      setError('翻訳の中断に失敗しました');
    }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleRetranslate = async () => {
    if (pagesData.length === 0) {
      return;
    }

    const engineName = translationEngine === 'apple' ? '軽量翻訳' : `LLM(${selectedQuality})`;
    if (!window.confirm(`現在の設定(${engineName})で再翻訳しますか？`)) {
      return;
    }

    setIsTranslating(true);
    setError(null);
    setTranslatedPages([]); // 既存の翻訳をクリア

    try {
      let response;
      if (translationEngine === 'apple') {
        response = await translatePagesApple(pagesData);
      } else {
        response = await translatePages(pagesData, selectedQuality);
      }
      setTranslatedPages(response.pages);
      console.log('Re-translation completed');
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
          {/* 翻訳エンジン選択 */}
          <select
            value={translationEngine}
            onChange={(e) => setTranslationEngine(e.target.value as 'llm' | 'apple')}
            style={styles.engineSelect}
            disabled={isTranslating}
          >
            <option value="llm">LLM翻訳</option>
            <option value="apple">軽量翻訳</option>
          </select>
          {translationEngine === 'llm' && (
            <span style={styles.badge}>
              {selectedQuality === 'high' ? 'Qwen3-14B' : selectedQuality === 'balanced' ? 'Qwen2.5-7B' : 'Qwen2.5-3B'}
            </span>
          )}
          {translationEngine === 'apple' && (
            <span style={{...styles.badge, backgroundColor: '#38a169'}}>Apple翻訳</span>
          )}
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
          <FileUpload onFileSelect={handleFileSelect} isLoading={isUploading} />
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
                  onQualityChange={setSelectedQuality}
                  selectedQuality={selectedQuality}
                  translationProgress={translationProgress}
                  isTranslating={isTranslating}
                  onRetranslate={handleRetranslate}
                />
              )}

              <TranslationPanel
                translatedPages={translatedPages}
                currentPage={currentPage}
                isTranslating={isTranslating}
                selectedQuality={selectedQuality}
              />
            </div>
          </>
        )}
      </div>

      {/* コントロールパネル */}
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

          {translatedPages.length > 0 && (
            <div style={styles.successMessage}>
              ✓ 翻訳完了 ({translatedPages.length} ページ)
            </div>
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
    padding: '16px 24px',
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
  badge: {
    padding: '4px 12px',
    backgroundColor: '#4a5568',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: 'bold' as const,
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
    padding: '16px',
    backgroundColor: 'white',
    borderTop: '2px solid #e2e8f0',
    boxShadow: '0 -2px 4px rgba(0,0,0,0.05)',
  } as React.CSSProperties,
  primaryButton: {
    padding: '12px 32px',
    backgroundColor: '#3182ce',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '16px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  } as React.CSSProperties,
  secondaryButton: {
    padding: '12px 24px',
    backgroundColor: '#718096',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  } as React.CSSProperties,
  cancelButton: {
    padding: '12px 24px',
    backgroundColor: '#e53e3e',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
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
    padding: '4px 12px',
    backgroundColor: '#48bb78',
    color: 'white',
    border: 'none',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  } as React.CSSProperties,
  engineSelect: {
    padding: '4px 8px',
    backgroundColor: '#4a5568',
    color: 'white',
    border: '1px solid #718096',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
  } as React.CSSProperties,
};

export default App;
