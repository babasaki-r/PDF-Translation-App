import React from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// PDF.js workerの設定
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

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

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
  };

  if (!file) {
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
      </div>
      <div style={styles.pdfContainer}>
        <Document
          file={file}
          onLoadSuccess={onDocumentLoadSuccess}
          loading={<div style={styles.loading}>PDFを読み込み中...</div>}
        >
          <Page
            pageNumber={currentPage}
            width={600}
            renderTextLayer={true}
            renderAnnotationLayer={true}
          />
        </Document>
      </div>
    </div>
  );
};

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
};

export default PdfViewer;
