import React, { useState, useEffect } from 'react';
import { getQualityInfo, downloadTranslation } from '../api';
import { TranslatedPage, QualityInfo } from '../types';

interface ControlPanelProps {
  translatedPages: TranslatedPage[];
  currentPage: number;
  onQualityChange: (quality: string) => void;
  selectedQuality: string;
  translationProgress?: {
    current: number;
    total: number;
    percentage: number;
  } | null;
  isTranslating: boolean;
}

const ControlPanel: React.FC<ControlPanelProps> = ({
  translatedPages,
  currentPage,
  onQualityChange,
  selectedQuality,
  translationProgress,
  isTranslating,
}) => {
  const [qualityInfo, setQualityInfo] = useState<QualityInfo | null>(null);
  const [downloadFormat, setDownloadFormat] = useState<'original' | 'translated' | 'both'>('both');
  const [isDownloading, setIsDownloading] = useState(false);

  useEffect(() => {
    loadQualityInfo();
  }, []);

  const loadQualityInfo = async () => {
    try {
      const info = await getQualityInfo();
      setQualityInfo(info);
    } catch (error) {
      console.error('Failed to load quality info:', error);
    }
  };

  const handleDownload = async (type: 'all' | 'current') => {
    if (translatedPages.length === 0) return;

    // 確認ポップアップ
    const pageCount = type === 'current' ? 1 : translatedPages.length;
    const formatText = downloadFormat === 'both' ? '原文と翻訳' : downloadFormat === 'original' ? '原文のみ' : '翻訳のみ';
    const message = `${pageCount}ページ（${formatText}）をダウンロードしますか？`;

    if (!window.confirm(message)) {
      return;
    }

    setIsDownloading(true);
    try {
      const pageNumbers = type === 'current' ? [currentPage] : undefined;
      const blob = await downloadTranslation(translatedPages, downloadFormat, pageNumbers);

      // ダウンロード処理
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = type === 'current'
        ? `translation_page${currentPage}_${Date.now()}.txt`
        : `translation_${Date.now()}.txt`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
      alert('ダウンロードに失敗しました');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div style={styles.container}>
      {/* 品質選択 */}
      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>翻訳品質</h3>
        <div style={styles.qualityButtons}>
          {qualityInfo && Object.entries(qualityInfo.options).map(([key, option]) => (
            <button
              key={key}
              onClick={() => onQualityChange(key)}
              style={{
                ...styles.qualityButton,
                ...(selectedQuality === key ? styles.qualityButtonActive : {}),
              }}
              disabled={isTranslating}
            >
              <div style={styles.qualityLabel}>{option.description}</div>
              <div style={styles.qualityDetails}>
                速度: {option.speed} | 品質: {option.quality}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* 翻訳進捗 */}
      {isTranslating && translationProgress && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>翻訳進捗</h3>
          <div style={styles.progressContainer}>
            <div style={styles.progressBar}>
              <div
                style={{
                  ...styles.progressFill,
                  width: `${translationProgress.percentage}%`,
                }}
              />
            </div>
            <div style={styles.progressText}>
              {translationProgress.current} / {translationProgress.total} ページ
              ({translationProgress.percentage.toFixed(1)}%)
            </div>
          </div>
        </div>
      )}

      {/* ダウンロード */}
      {translatedPages.length > 0 && !isTranslating && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>ダウンロード</h3>

          {/* フォーマット選択 */}
          <div style={styles.formatSelector}>
            <label style={styles.formatLabel}>
              <input
                type="radio"
                value="both"
                checked={downloadFormat === 'both'}
                onChange={(e) => setDownloadFormat(e.target.value as any)}
                style={styles.radio}
              />
              原文と翻訳
            </label>
            <label style={styles.formatLabel}>
              <input
                type="radio"
                value="original"
                checked={downloadFormat === 'original'}
                onChange={(e) => setDownloadFormat(e.target.value as any)}
                style={styles.radio}
              />
              原文のみ
            </label>
            <label style={styles.formatLabel}>
              <input
                type="radio"
                value="translated"
                checked={downloadFormat === 'translated'}
                onChange={(e) => setDownloadFormat(e.target.value as any)}
                style={styles.radio}
              />
              翻訳のみ
            </label>
          </div>

          {/* ダウンロードボタン */}
          <div style={styles.downloadButtons}>
            <button
              onClick={() => handleDownload('current')}
              style={styles.downloadButton}
              disabled={isDownloading}
            >
              📄 現在のページ
            </button>
            <button
              onClick={() => handleDownload('all')}
              style={styles.downloadButtonPrimary}
              disabled={isDownloading}
            >
              📚 全ページ ({translatedPages.length}ページ)
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    padding: '20px',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
    marginBottom: '20px',
  } as React.CSSProperties,
  section: {
    marginBottom: '24px',
  } as React.CSSProperties,
  sectionTitle: {
    fontSize: '16px',
    fontWeight: 'bold' as const,
    marginBottom: '12px',
    color: '#2d3748',
  } as React.CSSProperties,
  qualityButtons: {
    display: 'flex',
    gap: '12px',
  } as React.CSSProperties,
  qualityButton: {
    flex: 1,
    padding: '12px',
    backgroundColor: 'white',
    border: '2px solid #e2e8f0',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    textAlign: 'left' as const,
  } as React.CSSProperties,
  qualityButtonActive: {
    borderColor: '#3182ce',
    backgroundColor: '#ebf8ff',
  } as React.CSSProperties,
  qualityLabel: {
    fontWeight: 'bold' as const,
    fontSize: '14px',
    marginBottom: '4px',
  } as React.CSSProperties,
  qualityDetails: {
    fontSize: '12px',
    color: '#718096',
  } as React.CSSProperties,
  progressContainer: {
    padding: '12px',
    backgroundColor: 'white',
    borderRadius: '8px',
  } as React.CSSProperties,
  progressBar: {
    width: '100%',
    height: '24px',
    backgroundColor: '#e2e8f0',
    borderRadius: '12px',
    overflow: 'hidden',
    marginBottom: '8px',
  } as React.CSSProperties,
  progressFill: {
    height: '100%',
    backgroundColor: '#3182ce',
    transition: 'width 0.3s',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontSize: '12px',
    fontWeight: 'bold' as const,
  } as React.CSSProperties,
  progressText: {
    textAlign: 'center' as const,
    fontSize: '14px',
    color: '#4a5568',
    fontWeight: 'bold' as const,
  } as React.CSSProperties,
  formatSelector: {
    display: 'flex',
    gap: '16px',
    marginBottom: '12px',
    padding: '12px',
    backgroundColor: 'white',
    borderRadius: '8px',
  } as React.CSSProperties,
  formatLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '14px',
    cursor: 'pointer',
  } as React.CSSProperties,
  radio: {
    cursor: 'pointer',
  } as React.CSSProperties,
  downloadButtons: {
    display: 'flex',
    gap: '12px',
  } as React.CSSProperties,
  downloadButton: {
    flex: 1,
    padding: '12px 20px',
    backgroundColor: 'white',
    border: '2px solid #3182ce',
    color: '#3182ce',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    transition: 'all 0.2s',
  } as React.CSSProperties,
  downloadButtonPrimary: {
    flex: 1,
    padding: '12px 20px',
    backgroundColor: '#3182ce',
    border: 'none',
    color: 'white',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    transition: 'all 0.2s',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  } as React.CSSProperties,
};

export default ControlPanel;
