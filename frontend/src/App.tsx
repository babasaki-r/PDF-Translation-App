import React, { useState, useEffect, useRef } from 'react';
import FileUpload from './components/FileUpload';
import PdfViewer from './components/PdfViewer';
import TranslationPanel from './components/TranslationPanel';
import ControlPanel from './components/ControlPanel';
import GlossaryPanel from './components/GlossaryPanel';
import { uploadPDF, translatePages, getProgress, cancelTranslation } from './api';
import { PageData, TranslatedPage } from './types';

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pagesData, setPagesData] = useState<PageData[]>([]);
  const [translatedPages, setTranslatedPages] = useState<TranslatedPage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedQuality, setSelectedQuality] = useState('balanced');
  const [translationProgress, setTranslationProgress] = useState<{
    current: number;
    total: number;
    percentage: number;
  } | null>(null);
  const progressIntervalRef = useRef<number | null>(null);

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
      // 進捗を定期的に取得
      progressIntervalRef.current = window.setInterval(async () => {
        try {
          const progress = await getProgress();
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
  }, [isTranslating]);

  const handleTranslate = async () => {
    if (pagesData.length === 0) {
      return;
    }

    setIsTranslating(true);
    setError(null);

    try {
      const response = await translatePages(pagesData, selectedQuality);
      setTranslatedPages(response.pages);
      console.log('Translation completed with quality:', selectedQuality);
    } catch (err) {
      console.error('Translation error:', err);
      setError('翻訳に失敗しました。バックエンドが起動しているか確認してください。');
    } finally {
      setIsTranslating(false);
    }
  };

  const handleCancelTranslation = async () => {
    try {
      await cancelTranslation();
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

    if (!window.confirm(`現在の品質設定(${selectedQuality})で再翻訳しますか？`)) {
      return;
    }

    setIsTranslating(true);
    setError(null);
    setTranslatedPages([]); // 既存の翻訳をクリア

    try {
      const response = await translatePages(pagesData, selectedQuality);
      setTranslatedPages(response.pages);
      console.log('Re-translation completed with quality:', selectedQuality);
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
          <span style={styles.badge}>{selectedQuality === 'high' ? 'Qwen3-14B' : selectedQuality === 'balanced' ? 'Qwen2.5-7B' : 'Qwen2.5-3B'}</span>
          <span style={styles.badge}>M4 Pro Optimized</span>
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
};

export default App;
