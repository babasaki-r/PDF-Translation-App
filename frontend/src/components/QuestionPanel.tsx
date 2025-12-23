import React, { useState } from 'react';
import { askQuestion } from '../api';

interface QuestionPanelProps {
  pdfContent: string;
  isVisible: boolean;
  onClose: () => void;
}

interface QAItem {
  question: string;
  answer: string;
  timestamp: Date;
}

const QuestionPanel: React.FC<QuestionPanelProps> = ({
  pdfContent,
  isVisible,
  onClose,
}) => {
  const [question, setQuestion] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const [qaHistory, setQaHistory] = useState<QAItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleAsk = async () => {
    if (!question.trim() || !pdfContent) return;

    setIsAsking(true);
    setError(null);

    try {
      const result = await askQuestion(question, pdfContent);

      setQaHistory(prev => [{
        question: question,
        answer: result.answer,
        timestamp: new Date(),
      }, ...prev]);

      setQuestion('');
    } catch (err) {
      console.error('Question failed:', err);
      setError('質問の処理に失敗しました');
    } finally {
      setIsAsking(false);
    }
  };

  if (!isVisible) return null;

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.panel} onClick={(e) => e.stopPropagation()}>
        <div style={styles.header}>
          <h3 style={styles.title}>PDF内容について質問</h3>
          <button onClick={onClose} style={styles.closeButton}>×</button>
        </div>

        <div style={styles.content}>
          {/* 質問入力エリア */}
          <div style={styles.inputSection}>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="PDFの内容について質問してください..."
              style={styles.textarea}
              disabled={isAsking}
            />
            <button
              onClick={handleAsk}
              disabled={isAsking || !question.trim()}
              style={{
                ...styles.askButton,
                ...(isAsking || !question.trim() ? styles.askButtonDisabled : {})
              }}
            >
              {isAsking ? '回答中...' : '質問する'}
            </button>
          </div>

          {error && (
            <div style={styles.error}>{error}</div>
          )}

          {/* Q&A履歴 */}
          <div style={styles.historySection}>
            {qaHistory.length === 0 ? (
              <div style={styles.emptyHistory}>
                質問履歴がありません。PDFの内容について質問してください。
              </div>
            ) : (
              qaHistory.map((item, index) => (
                <div key={index} style={styles.qaItem}>
                  <div style={styles.questionBlock}>
                    <span style={styles.label}>Q:</span>
                    <span style={styles.questionText}>{item.question}</span>
                  </div>
                  <div style={styles.answerBlock}>
                    <span style={styles.label}>A:</span>
                    <div style={styles.answerText}>{item.answer}</div>
                  </div>
                  <div style={styles.timestamp}>
                    {item.timestamp.toLocaleTimeString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const styles = {
  overlay: {
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
  panel: {
    backgroundColor: 'white',
    borderRadius: '12px',
    width: '700px',
    maxWidth: '90vw',
    maxHeight: '80vh',
    display: 'flex',
    flexDirection: 'column' as const,
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)',
  } as React.CSSProperties,
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderBottom: '2px solid #e2e8f0',
    backgroundColor: '#f7fafc',
    borderRadius: '12px 12px 0 0',
  } as React.CSSProperties,
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 'bold' as const,
    color: '#2d3748',
  } as React.CSSProperties,
  closeButton: {
    background: 'none',
    border: 'none',
    fontSize: '24px',
    cursor: 'pointer',
    color: '#718096',
    padding: '4px 8px',
  } as React.CSSProperties,
  content: {
    flex: 1,
    overflow: 'auto',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '16px',
  } as React.CSSProperties,
  inputSection: {
    display: 'flex',
    gap: '12px',
    alignItems: 'flex-start',
  } as React.CSSProperties,
  textarea: {
    flex: 1,
    padding: '12px',
    border: '2px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '14px',
    resize: 'none' as const,
    minHeight: '60px',
    fontFamily: 'inherit',
  } as React.CSSProperties,
  askButton: {
    padding: '12px 24px',
    backgroundColor: '#3182ce',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    whiteSpace: 'nowrap' as const,
  } as React.CSSProperties,
  askButtonDisabled: {
    backgroundColor: '#a0aec0',
    cursor: 'not-allowed',
  } as React.CSSProperties,
  error: {
    padding: '12px',
    backgroundColor: '#fed7d7',
    color: '#c53030',
    borderRadius: '6px',
    fontSize: '14px',
  } as React.CSSProperties,
  historySection: {
    flex: 1,
    overflow: 'auto',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '16px',
  } as React.CSSProperties,
  emptyHistory: {
    textAlign: 'center' as const,
    color: '#718096',
    padding: '40px 20px',
    fontSize: '14px',
  } as React.CSSProperties,
  qaItem: {
    padding: '16px',
    backgroundColor: '#f7fafc',
    borderRadius: '8px',
    border: '1px solid #e2e8f0',
  } as React.CSSProperties,
  questionBlock: {
    display: 'flex',
    gap: '8px',
    marginBottom: '12px',
  } as React.CSSProperties,
  label: {
    fontWeight: 'bold' as const,
    color: '#3182ce',
    fontSize: '14px',
    flexShrink: 0,
  } as React.CSSProperties,
  questionText: {
    fontSize: '14px',
    color: '#2d3748',
  } as React.CSSProperties,
  answerBlock: {
    display: 'flex',
    gap: '8px',
  } as React.CSSProperties,
  answerText: {
    fontSize: '14px',
    color: '#2d3748',
    lineHeight: '1.6',
    whiteSpace: 'pre-wrap' as const,
  } as React.CSSProperties,
  timestamp: {
    fontSize: '11px',
    color: '#a0aec0',
    textAlign: 'right' as const,
    marginTop: '8px',
  } as React.CSSProperties,
};

export default QuestionPanel;
