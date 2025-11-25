import React, { useCallback } from 'react';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  isLoading: boolean;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFileSelect, isLoading }) => {
  const handleFileChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (file && file.type === 'application/pdf') {
        onFileSelect(file);
      } else {
        alert('PDFファイルを選択してください');
      }
    },
    [onFileSelect]
  );

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      const file = event.dataTransfer.files[0];
      if (file && file.type === 'application/pdf') {
        onFileSelect(file);
      } else {
        alert('PDFファイルを選択してください');
      }
    },
    [onFileSelect]
  );

  const handleDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  }, []);

  return (
    <div style={styles.container}>
      <div
        style={styles.dropzone}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <div style={styles.content}>
          <svg
            style={styles.icon}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <h3 style={styles.title}>PDF設備仕様書をアップロード</h3>
          <p style={styles.description}>
            ドラッグ&ドロップ または クリックしてファイルを選択
          </p>
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            style={styles.input}
            disabled={isLoading}
            id="file-upload"
          />
          <label htmlFor="file-upload" style={styles.button}>
            {isLoading ? '処理中...' : 'ファイルを選択'}
          </label>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100%',
    padding: '20px',
  } as React.CSSProperties,
  dropzone: {
    border: '2px dashed #cbd5e0',
    borderRadius: '8px',
    padding: '40px',
    textAlign: 'center' as const,
    backgroundColor: 'white',
    transition: 'all 0.3s ease',
    cursor: 'pointer',
    maxWidth: '500px',
    width: '100%',
  } as React.CSSProperties,
  content: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    gap: '16px',
  } as React.CSSProperties,
  icon: {
    width: '64px',
    height: '64px',
    color: '#4a5568',
  } as React.CSSProperties,
  title: {
    fontSize: '20px',
    fontWeight: 'bold' as const,
    color: '#2d3748',
  } as React.CSSProperties,
  description: {
    fontSize: '14px',
    color: '#718096',
  } as React.CSSProperties,
  input: {
    display: 'none',
  } as React.CSSProperties,
  button: {
    padding: '10px 24px',
    backgroundColor: '#3182ce',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '16px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  } as React.CSSProperties,
};

export default FileUpload;
