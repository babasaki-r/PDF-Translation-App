import React from 'react';
import { TranslatedPage, TranslationDirection } from '../types';

interface TranslationPanelProps {
  translatedPages: TranslatedPage[];
  currentPage: number;
  isTranslating: boolean;
  translationEngine?: 'apple' | 'ollama' | 'swallow';
  ollamaModel?: string;
  translationDirection?: TranslationDirection;
}

const TranslationPanel: React.FC<TranslationPanelProps> = ({
  translatedPages,
  currentPage,
  isTranslating,
  translationEngine = 'ollama',
  ollamaModel = 'qwen3:4b-instruct',
  translationDirection = 'en-to-ja',
}) => {
  const currentTranslation = translatedPages.find(p => p.page === currentPage);

  // 翻訳方向に応じたラベル
  const sourceLabel = translationDirection === 'ja-to-en' ? '日本語 (原文)' : '英語 (原文)';
  const targetLabel = translationDirection === 'ja-to-en' ? '英語 (翻訳)' : '日本語 (翻訳)';
  const headerTitle = translationDirection === 'ja-to-en'
    ? `英語翻訳 (ページ ${currentPage})`
    : `日本語翻訳 (ページ ${currentPage})`;

  // 使用中のエンジン・モデル名を取得
  const getEngineDisplayName = () => {
    if (translationEngine === 'apple') {
      return 'Apple翻訳';
    } else if (translationEngine === 'ollama') {
      // Ollamaモデル名を整形
      const modelDisplayNames: Record<string, string> = {
        'qwen3:4b-instruct': 'Ollama (Qwen3 4B)',
        'qwen2.5:7b-instruct': 'Ollama (Qwen2.5 7B)',
        'llama3.1:8b': 'Ollama (Llama 3.1 8B)',
        'qwen3-vl:8b-instruct': 'Ollama (Qwen3-VL 8B)',
        'qwen3:14b': 'Ollama (Qwen3 14B)',
        'qwen2.5:14b': 'Ollama (Qwen2.5 14B)',
      };
      return modelDisplayNames[ollamaModel] || `Ollama (${ollamaModel})`;
    } else if (translationEngine === 'swallow') {
      return 'Swallow (Llama-3.1-8B)';
    } else {
      return 'Ollama';
    }
  };

  if (isTranslating) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>
          <div style={styles.spinner}></div>
          <p>翻訳中... ({getEngineDisplayName()}で処理しています)</p>
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
        <h3 style={styles.title}>{headerTitle}</h3>
      </div>
      <div style={styles.content}>
        {/* オリジナルテキスト */}
        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>{sourceLabel}</h4>
          <div style={styles.textBox}>
            <pre style={styles.text}>{currentTranslation.original.text}</pre>
          </div>
        </div>

        <div style={styles.divider}></div>

        {/* 翻訳テキスト */}
        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>{targetLabel}</h4>
          <div style={styles.textBox}>
            <pre style={styles.text}>{currentTranslation.translated.text}</pre>
          </div>
        </div>
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
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
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
