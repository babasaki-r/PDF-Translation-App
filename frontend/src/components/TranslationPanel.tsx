import React from 'react';
import { TranslatedPage } from '../types';

interface TranslationPanelProps {
  translatedPages: TranslatedPage[];
  currentPage: number;
  isTranslating: boolean;
  selectedQuality?: string;
}

const TranslationPanel: React.FC<TranslationPanelProps> = ({
  translatedPages,
  currentPage,
  isTranslating,
  selectedQuality = 'balanced',
}) => {
  const currentTranslation = translatedPages.find(p => p.page === currentPage);

  // モデル名の取得
  const getModelName = (quality: string) => {
    const modelMap: Record<string, string> = {
      'high': 'Qwen3-14B',
      'balanced': 'Qwen2.5-7B',
      'fast': 'Qwen2.5-3B'
    };
    return modelMap[quality] || 'Qwen2.5-7B';
  };

  if (isTranslating) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>
          <div style={styles.spinner}></div>
          <p>翻訳中... ({getModelName(selectedQuality)}で処理しています)</p>
          <p style={styles.loadingNote}>
            この処理には時間がかかる場合があります
          </p>
        </div>
      </div>
    );
  }

  if (!currentTranslation) {
    return (
      <div style={styles.container}>
        <div style={styles.empty}>
          <p>翻訳を開始してください</p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>日本語翻訳 (ページ {currentPage})</h3>
      </div>
      <div style={styles.content}>
        {/* オリジナルテキスト */}
        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>英語 (原文)</h4>
          <div style={styles.textBox}>
            <pre style={styles.text}>{currentTranslation.original.text}</pre>
          </div>
        </div>

        <div style={styles.divider}></div>

        {/* 翻訳テキスト */}
        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>日本語 (翻訳)</h4>
          <div style={styles.textBox}>
            <pre style={styles.text}>{currentTranslation.translated.text}</pre>
          </div>
        </div>

        {/* セクション別翻訳（オプション表示） */}
        {currentTranslation.translated.sections.length > 0 && (
          <details style={styles.details}>
            <summary style={styles.summary}>
              セクション別翻訳を表示 ({currentTranslation.translated.sections.length}件)
            </summary>
            <div style={styles.sectionsContainer}>
              {currentTranslation.translated.sections.map((section, index) => (
                <div key={index} style={styles.sectionItem}>
                  <div style={styles.sectionNumber}>セクション {index + 1}</div>
                  <div style={styles.sectionContent}>
                    <div style={styles.miniSection}>
                      <strong>原文:</strong>
                      <p style={styles.miniText}>{section.original}</p>
                    </div>
                    <div style={styles.miniSection}>
                      <strong>翻訳:</strong>
                      <p style={styles.miniText}>{section.translated}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100%',
    backgroundColor: 'white',
  } as React.CSSProperties,
  header: {
    padding: '16px',
    borderBottom: '2px solid #e2e8f0',
    backgroundColor: '#f7fafc',
  } as React.CSSProperties,
  title: {
    fontSize: '18px',
    fontWeight: 'bold' as const,
    color: '#2d3748',
  } as React.CSSProperties,
  content: {
    flex: 1,
    overflow: 'auto',
    padding: '20px',
  } as React.CSSProperties,
  section: {
    marginBottom: '24px',
  } as React.CSSProperties,
  sectionTitle: {
    fontSize: '14px',
    fontWeight: 'bold' as const,
    color: '#4a5568',
    marginBottom: '8px',
  } as React.CSSProperties,
  textBox: {
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    padding: '16px',
    backgroundColor: '#f7fafc',
    minHeight: '200px',
    overflow: 'auto',
  } as React.CSSProperties,
  text: {
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-word' as const,
    fontSize: '14px',
    lineHeight: '1.6',
    color: '#2d3748',
    fontFamily: 'inherit',
  } as React.CSSProperties,
  divider: {
    height: '1px',
    backgroundColor: '#e2e8f0',
    margin: '24px 0',
  } as React.CSSProperties,
  loading: {
    display: 'flex',
    flexDirection: 'column' as const,
    justifyContent: 'center',
    alignItems: 'center',
    height: '100%',
    color: '#718096',
  } as React.CSSProperties,
  spinner: {
    width: '40px',
    height: '40px',
    border: '4px solid #e2e8f0',
    borderTop: '4px solid #3182ce',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    marginBottom: '16px',
  } as React.CSSProperties,
  loadingNote: {
    fontSize: '12px',
    color: '#a0aec0',
    marginTop: '8px',
  } as React.CSSProperties,
  empty: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100%',
    color: '#718096',
    fontSize: '16px',
  } as React.CSSProperties,
  details: {
    marginTop: '24px',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    padding: '16px',
  } as React.CSSProperties,
  summary: {
    cursor: 'pointer',
    fontWeight: 'bold' as const,
    color: '#3182ce',
    marginBottom: '12px',
  } as React.CSSProperties,
  sectionsContainer: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '12px',
  } as React.CSSProperties,
  sectionItem: {
    border: '1px solid #e2e8f0',
    borderRadius: '4px',
    padding: '12px',
    backgroundColor: '#f7fafc',
  } as React.CSSProperties,
  sectionNumber: {
    fontSize: '12px',
    fontWeight: 'bold' as const,
    color: '#718096',
    marginBottom: '8px',
  } as React.CSSProperties,
  sectionContent: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
  } as React.CSSProperties,
  miniSection: {
    fontSize: '13px',
  } as React.CSSProperties,
  miniText: {
    marginTop: '4px',
    color: '#4a5568',
    lineHeight: '1.5',
  } as React.CSSProperties,
};

// スピナーアニメーション用のグローバルスタイル
const styleSheet = document.createElement('style');
styleSheet.textContent = `
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;
document.head.appendChild(styleSheet);

export default TranslationPanel;
