import React, { useState } from 'react';
import { TranslatedPage } from '../types';
import { proofreadTranslation } from '../api';

interface TranslationPanelProps {
  translatedPages: TranslatedPage[];
  currentPage: number;
  isTranslating: boolean;
  selectedQuality?: string;
}

interface ProofreadResult {
  has_issues: boolean;
  corrected_text: string;
  issues: Array<{ type: string; description: string; suggestion: string }>;
}

const TranslationPanel: React.FC<TranslationPanelProps> = ({
  translatedPages,
  currentPage,
  isTranslating,
  selectedQuality = 'balanced',
}) => {
  const currentTranslation = translatedPages.find(p => p.page === currentPage);
  const [isProofreading, setIsProofreading] = useState(false);
  const [proofreadResult, setProofreadResult] = useState<ProofreadResult | null>(null);
  const [showProofreadModal, setShowProofreadModal] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  // モデル名の取得
  const getModelName = (quality: string) => {
    const modelMap: Record<string, string> = {
      'high': 'Qwen3-14B',
      'balanced': 'Qwen2.5-7B',
      'fast': 'Qwen2.5-3B'
    };
    return modelMap[quality] || 'Qwen2.5-7B';
  };

  // 経過時間のトラッキング
  React.useEffect(() => {
    let intervalId: number | undefined;

    if (isProofreading) {
      setElapsedTime(0);
      intervalId = window.setInterval(() => {
        setElapsedTime(prev => prev + 1);
      }, 1000);
    } else {
      setElapsedTime(0);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [isProofreading]);

  // 校正キャンセル
  const handleCancelProofread = () => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
    }
    setIsProofreading(false);
    setElapsedTime(0);
  };

  // 校正実行
  const handleProofread = async () => {
    if (!currentTranslation) return;

    const controller = new AbortController();
    setAbortController(controller);
    setIsProofreading(true);

    try {
      const result = await proofreadTranslation(
        currentTranslation.original.text,
        currentTranslation.translated.text,
        currentPage
      );

      if (!controller.signal.aborted) {
        setProofreadResult(result);
        setShowProofreadModal(true);
      }
    } catch (error: any) {
      if (error.name === 'AbortError' || controller.signal.aborted) {
        console.log('Proofreading was cancelled');
      } else {
        console.error('Proofread failed:', error);
        alert('校正に失敗しました');
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsProofreading(false);
        setAbortController(null);
      }
    }
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
        {currentTranslation && (
          <div style={styles.proofreadControls}>
            {!isProofreading ? (
              <button
                onClick={handleProofread}
                style={styles.proofreadButton}
              >
                ✓ 校正
              </button>
            ) : (
              <>
                <button
                  onClick={handleCancelProofread}
                  style={styles.cancelProofreadButton}
                >
                  ✕ キャンセル
                </button>
                <div style={styles.elapsedTimeDisplay}>
                  経過時間: {elapsedTime}秒
                </div>
              </>
            )}
          </div>
        )}
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

      {/* 校正結果モーダル */}
      {showProofreadModal && proofreadResult && (
        <div style={styles.modal} onClick={() => setShowProofreadModal(false)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>校正結果 (ページ {currentPage})</h3>
              <button
                onClick={() => setShowProofreadModal(false)}
                style={styles.modalCloseButton}
              >
                ×
              </button>
            </div>
            <div style={styles.modalBody}>
              {proofreadResult.has_issues ? (
                <>
                  <div style={styles.issuesAlert}>
                    ⚠️ {proofreadResult.issues.length}件の問題が見つかりました
                  </div>
                  <div style={styles.issuesList}>
                    {proofreadResult.issues.map((issue, index) => (
                      <div key={index} style={styles.issueItem}>
                        <div style={styles.issueType}>{issue.type}</div>
                        <div style={styles.issueDescription}>{issue.description}</div>
                        <div style={styles.issueSuggestion}>
                          <strong>提案:</strong> {issue.suggestion}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div style={styles.correctedSection}>
                    <h4 style={styles.correctedTitle}>修正後の翻訳:</h4>
                    <div style={styles.correctedTextBox}>
                      <pre style={styles.correctedText}>
                        {proofreadResult.corrected_text}
                      </pre>
                    </div>
                  </div>
                </>
              ) : (
                <div style={styles.successAlert}>
                  ✓ 問題は見つかりませんでした。翻訳は正確です。
                </div>
              )}
            </div>
          </div>
        </div>
      )}
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
  proofreadControls: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  } as React.CSSProperties,
  proofreadButton: {
    padding: '8px 16px',
    backgroundColor: '#48bb78',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  } as React.CSSProperties,
  cancelProofreadButton: {
    padding: '8px 16px',
    backgroundColor: '#e53e3e',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  } as React.CSSProperties,
  elapsedTimeDisplay: {
    fontSize: '14px',
    color: '#4a5568',
    fontWeight: 'bold' as const,
    padding: '4px 12px',
    backgroundColor: '#f7fafc',
    borderRadius: '6px',
    border: '1px solid #e2e8f0',
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
  modal: {
    position: 'fixed' as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  } as React.CSSProperties,
  modalContent: {
    backgroundColor: 'white',
    borderRadius: '12px',
    maxWidth: '800px',
    width: '90%',
    maxHeight: '80vh',
    overflow: 'auto',
    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)',
  } as React.CSSProperties,
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderBottom: '2px solid #e2e8f0',
  } as React.CSSProperties,
  modalTitle: {
    fontSize: '18px',
    fontWeight: 'bold' as const,
    color: '#2d3748',
    margin: 0,
  } as React.CSSProperties,
  modalCloseButton: {
    fontSize: '24px',
    border: 'none',
    background: 'none',
    cursor: 'pointer',
    color: '#718096',
    padding: '4px 8px',
  } as React.CSSProperties,
  modalBody: {
    padding: '20px',
  } as React.CSSProperties,
  issuesAlert: {
    padding: '12px',
    backgroundColor: '#fff5f5',
    border: '1px solid #fc8181',
    borderRadius: '6px',
    color: '#c53030',
    fontSize: '14px',
    fontWeight: 'bold' as const,
    marginBottom: '16px',
  } as React.CSSProperties,
  successAlert: {
    padding: '16px',
    backgroundColor: '#f0fff4',
    border: '1px solid #68d391',
    borderRadius: '6px',
    color: '#22543d',
    fontSize: '16px',
    fontWeight: 'bold' as const,
    textAlign: 'center' as const,
  } as React.CSSProperties,
  issuesList: {
    marginBottom: '20px',
  } as React.CSSProperties,
  issueItem: {
    padding: '12px',
    backgroundColor: '#f7fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    marginBottom: '12px',
  } as React.CSSProperties,
  issueType: {
    fontSize: '12px',
    fontWeight: 'bold' as const,
    color: '#e53e3e',
    marginBottom: '4px',
  } as React.CSSProperties,
  issueDescription: {
    fontSize: '14px',
    color: '#2d3748',
    marginBottom: '4px',
  } as React.CSSProperties,
  issueSuggestion: {
    fontSize: '13px',
    color: '#4a5568',
    marginTop: '8px',
  } as React.CSSProperties,
  correctedSection: {
    marginTop: '20px',
  } as React.CSSProperties,
  correctedTitle: {
    fontSize: '16px',
    fontWeight: 'bold' as const,
    color: '#2d3748',
    marginBottom: '8px',
  } as React.CSSProperties,
  correctedTextBox: {
    border: '2px solid #48bb78',
    borderRadius: '6px',
    padding: '16px',
    backgroundColor: '#f0fff4',
  } as React.CSSProperties,
  correctedText: {
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-word' as const,
    fontSize: '14px',
    lineHeight: '1.6',
    color: '#2d3748',
    fontFamily: 'inherit',
    margin: 0,
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
