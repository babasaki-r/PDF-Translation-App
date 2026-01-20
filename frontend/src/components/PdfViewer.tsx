import React from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// PDF.js workerの設定（ローカルファイルを使用）
pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js';

// 日本語PDFの表示に必要なCMaps設定（ローカルファイルを使用）
const cMapUrl = '/cmaps/';
const cMapPacked = true;
const standardFontDataUrl = '/standard_fonts/';

interface PdfViewerProps {
  file: File | null;
  currentPage: number;
  onPageChange: (page: number) => void;
}

const PdfViewer: React.FC<PdfViewerProps> = ({
  file,
  currentPage,
  onPageChange,
}) => {
  const [numPages, setNumPages] = React.useState<number>(0);
  const [scale, setScale] = React.useState<number>(1.0);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [fileUrl, setFileUrl] = React.useState<string | null>(null);

  // FileオブジェクトをBlobURLに変換
  React.useEffect(() => {
    if (file) {
      const url = URL.createObjectURL(file);
      setFileUrl(url);
      setLoadError(null);
      console.log('PDF file URL created:', url);

      // クリーンアップ
      return () => {
        URL.revokeObjectURL(url);
        setFileUrl(null);
      };
    } else {
      setFileUrl(null);
    }
  }, [file]);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    console.log('PDF loaded successfully, numPages:', numPages);
    setNumPages(numPages);
    setLoadError(null);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF load error:', error);
    setLoadError(`PDFの読み込みに失敗しました: ${error.message}`);
  };

  const onPageLoadSuccess = () => {
    console.log('Page loaded successfully:', currentPage);
  };

  const onPageLoadError = (error: Error) => {
    console.error('Page load error:', error);
  };

  const onPageRenderSuccess = () => {
    console.log('Page rendered successfully:', currentPage);
  };

  const onPageRenderError = (error: Error) => {
    console.error('Page render error:', error);
  };

  const handleZoomIn = () => {
    setScale(prev => Math.min(prev + 0.25, 3.0));
  };

  const handleZoomOut = () => {
    setScale(prev => Math.max(prev - 0.25, 0.5));
  };

  const handleResetZoom = () => {
    setScale(1.0);
  };

  if (!file || !fileUrl) {
    return (
      <div style={styles.empty}>
        <p>PDFファイルをアップロードしてください</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        <button
          onClick={() => onPageChange(Math.max(1, currentPage - 1))}
          disabled={currentPage <= 1}
          style={styles.button}
        >
          ← 前へ
        </button>
        <span style={styles.pageInfo}>
          {currentPage} / {numPages}
        </span>
        <button
          onClick={() => onPageChange(Math.min(numPages, currentPage + 1))}
          disabled={currentPage >= numPages}
          style={styles.button}
        >
          次へ →
        </button>

        <div style={styles.divider}></div>

        <button
          onClick={handleZoomOut}
          disabled={scale <= 0.5}
          style={styles.zoomButton}
          title="縮小"
        >
          −
        </button>
        <span style={styles.zoomInfo}>
          {Math.round(scale * 100)}%
        </span>
        <button
          onClick={handleZoomIn}
          disabled={scale >= 3.0}
          style={styles.zoomButton}
          title="拡大"
        >
          +
        </button>
        <button
          onClick={handleResetZoom}
          style={styles.resetButton}
          title="リセット"
        >
          リセット
        </button>
      </div>
      <div style={styles.pdfContainer}>
        <Document
          file={fileUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={onDocumentLoadError}
          loading={<div style={styles.loading}>PDFを読み込み中...</div>}
          error={<div style={styles.error}>{loadError || 'PDFの読み込みに失敗しました'}</div>}
          options={{
            cMapUrl: cMapUrl,
            cMapPacked: cMapPacked,
            standardFontDataUrl: standardFontDataUrl,
            disableFontFace: false,
            useSystemFonts: true,
          }}
        >
          <Page
            pageNumber={currentPage}
            scale={scale}
            renderTextLayer={true}
            renderAnnotationLayer={true}
            onLoadSuccess={onPageLoadSuccess}
            onLoadError={onPageLoadError}
            onRenderSuccess={onPageRenderSuccess}
            onRenderError={onPageRenderError}
          />
        </Document>
      </div>
    </div>
  );
};

// React.memoで不要な再レンダリングを防止
export default React.memo(PdfViewer, (prevProps, nextProps) => {
  // file, currentPage, onPageChangeが同じなら再レンダリングしない
  return (
    prevProps.file === nextProps.file &&
    prevProps.currentPage === nextProps.currentPage &&
    prevProps.onPageChange === nextProps.onPageChange
  );
});

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100%',
    backgroundColor: '#f7fafc',
  } as React.CSSProperties,
  toolbar: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '16px',
    padding: '12px',
    backgroundColor: 'white',
    borderBottom: '1px solid #e2e8f0',
  } as React.CSSProperties,
  button: {
    padding: '8px 16px',
    backgroundColor: '#3182ce',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    transition: 'background-color 0.2s',
  } as React.CSSProperties,
  pageInfo: {
    fontSize: '14px',
    fontWeight: 'bold' as const,
    minWidth: '80px',
    textAlign: 'center' as const,
  } as React.CSSProperties,
  divider: {
    width: '1px',
    height: '24px',
    backgroundColor: '#e2e8f0',
    margin: '0 8px',
  } as React.CSSProperties,
  zoomButton: {
    width: '32px',
    height: '32px',
    padding: '0',
    backgroundColor: '#3182ce',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '18px',
    fontWeight: 'bold' as const,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'background-color 0.2s',
  } as React.CSSProperties,
  zoomInfo: {
    fontSize: '14px',
    fontWeight: 'bold' as const,
    minWidth: '60px',
    textAlign: 'center' as const,
    color: '#2d3748',
  } as React.CSSProperties,
  resetButton: {
    padding: '6px 12px',
    backgroundColor: '#718096',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
    transition: 'background-color 0.2s',
  } as React.CSSProperties,
  pdfContainer: {
    flex: 1,
    overflow: 'auto',
    display: 'flex',
    justifyContent: 'center',
    padding: '20px',
  } as React.CSSProperties,
  empty: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100%',
    color: '#718096',
    fontSize: '16px',
  } as React.CSSProperties,
  loading: {
    padding: '20px',
    textAlign: 'center' as const,
    color: '#718096',
  } as React.CSSProperties,
  error: {
    padding: '20px',
    textAlign: 'center' as const,
    color: '#e53e3e',
    backgroundColor: '#fed7d7',
    borderRadius: '8px',
    margin: '20px',
  } as React.CSSProperties,
};
