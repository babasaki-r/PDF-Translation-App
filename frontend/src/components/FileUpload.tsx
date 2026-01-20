import React, { useCallback, useEffect, useState } from 'react';
import { DocumentType, DocumentTypeInfo } from '../types';
import { getDocumentTypes } from '../api';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  isLoading: boolean;
  documentType: DocumentType;
  onDocumentTypeChange: (type: DocumentType) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({
  onFileSelect,
  isLoading,
  documentType,
  onDocumentTypeChange,
}) => {
  const [documentTypes, setDocumentTypes] = useState<DocumentTypeInfo[]>([]);

  // 文書タイプ一覧を取得
  useEffect(() => {
    const fetchDocumentTypes = async () => {
      try {
        const response = await getDocumentTypes();
        if (response.success && response.document_types.length > 0) {
          setDocumentTypes(response.document_types);
        }
      } catch (error) {
        console.log('Failed to fetch document types:', error);
        // フォールバック: デフォルトの文書タイプ
        setDocumentTypes([
          { id: 'steel_technical', name: '鉄鋼業における技術文書', description: '鉄鋼業界の設備仕様書・技術文書向け' },
          { id: 'general_technical', name: '一般的な技術文書', description: 'IT・機械・電気など一般的な技術文書向け' },
          { id: 'academic_paper', name: '技術論文', description: '学術論文・研究報告書向け' },
          { id: 'contract', name: '契約書', description: '契約書・法的文書向け' },
          { id: 'general_document', name: '一般的な文書', description: '新聞・記事・ブログ・一般的な文書向け' },
          { id: 'order_acceptance', name: '注文書・検収書', description: '注文書・発注書・検収書・納品書向け' },
        ]);
      }
    };
    fetchDocumentTypes();
  }, []);

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

  const handleDocumentTypeChange = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) => {
      onDocumentTypeChange(event.target.value as DocumentType);
    },
    [onDocumentTypeChange]
  );

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
          <h3 style={styles.title}>翻訳したいPDF文書をアップロード</h3>

          {/* 文書タイプ選択 */}
          <div style={styles.documentTypeContainer}>
            <label style={styles.documentTypeLabel}>文書タイプ:</label>
            <select
              value={documentType}
              onChange={handleDocumentTypeChange}
              style={styles.documentTypeSelect}
              disabled={isLoading}
            >
              {documentTypes.map((type) => (
                <option key={type.id} value={type.id}>
                  {type.name}
                </option>
              ))}
            </select>
          </div>

          {/* 選択中の文書タイプの説明 */}
          {documentTypes.length > 0 && (
            <p style={styles.documentTypeDescription}>
              {documentTypes.find((t) => t.id === documentType)?.description || ''}
            </p>
          )}

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
  documentTypeContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginTop: '8px',
  } as React.CSSProperties,
  documentTypeLabel: {
    fontSize: '14px',
    fontWeight: '500' as const,
    color: '#4a5568',
  } as React.CSSProperties,
  documentTypeSelect: {
    padding: '8px 12px',
    fontSize: '14px',
    borderRadius: '6px',
    border: '1px solid #cbd5e0',
    backgroundColor: 'white',
    cursor: 'pointer',
    minWidth: '200px',
  } as React.CSSProperties,
  documentTypeDescription: {
    fontSize: '12px',
    color: '#718096',
    marginTop: '-8px',
    fontStyle: 'italic' as const,
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
