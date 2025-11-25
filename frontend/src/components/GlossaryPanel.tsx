import React, { useState, useEffect } from 'react';
import { getGlossary, addGlossaryTerm, updateGlossary } from '../api';

const GlossaryPanel: React.FC = () => {
  const [glossary, setGlossary] = useState<Record<string, string>>({});
  const [isOpen, setIsOpen] = useState(false);
  const [newEnglish, setNewEnglish] = useState('');
  const [newJapanese, setNewJapanese] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadGlossary();
    }
  }, [isOpen]);

  const loadGlossary = async () => {
    try {
      const response = await getGlossary();
      setGlossary(response.glossary);
    } catch (error) {
      console.error('Failed to load glossary:', error);
    }
  };

  const handleAddTerm = async () => {
    if (!newEnglish.trim() || !newJapanese.trim()) {
      alert('英語と日本語の両方を入力してください');
      return;
    }

    setIsAdding(true);
    try {
      await addGlossaryTerm(newEnglish.trim(), newJapanese.trim());
      setNewEnglish('');
      setNewJapanese('');
      await loadGlossary();
    } catch (error) {
      console.error('Failed to add term:', error);
      alert('用語の追加に失敗しました');
    } finally {
      setIsAdding(false);
    }
  };

  const handleDeleteTerm = async (english: string) => {
    const newGlossary = { ...glossary };
    delete newGlossary[english];

    try {
      await updateGlossary(newGlossary);
      setGlossary(newGlossary);
    } catch (error) {
      console.error('Failed to delete term:', error);
      alert('用語の削除に失敗しました');
    }
  };

  if (!isOpen) {
    return (
      <button onClick={() => setIsOpen(true)} style={styles.toggleButton}>
        📚 用語集を開く
      </button>
    );
  }

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <h3 style={styles.title}>用語集管理</h3>
        <button onClick={() => setIsOpen(false)} style={styles.closeButton}>
          ✕
        </button>
      </div>

      {/* 新規追加フォーム */}
      <div style={styles.addForm}>
        <input
          type="text"
          placeholder="English"
          value={newEnglish}
          onChange={(e) => setNewEnglish(e.target.value)}
          style={styles.input}
        />
        <input
          type="text"
          placeholder="日本語"
          value={newJapanese}
          onChange={(e) => setNewJapanese(e.target.value)}
          style={styles.input}
        />
        <button
          onClick={handleAddTerm}
          disabled={isAdding}
          style={styles.addButton}
        >
          {isAdding ? '追加中...' : '+ 追加'}
        </button>
      </div>

      {/* 用語リスト */}
      <div style={styles.list}>
        {Object.keys(glossary).length === 0 ? (
          <div style={styles.emptyMessage}>用語がありません</div>
        ) : (
          Object.entries(glossary).map(([english, japanese]) => (
            <div key={english} style={styles.item}>
              <div style={styles.itemContent}>
                <div style={styles.itemEnglish}>{english}</div>
                <div style={styles.itemArrow}>→</div>
                <div style={styles.itemJapanese}>{japanese}</div>
              </div>
              <button
                onClick={() => handleDeleteTerm(english)}
                style={styles.deleteButton}
              >
                🗑️
              </button>
            </div>
          ))
        )}
      </div>

      <div style={styles.footer}>
        <div style={styles.count}>登録数: {Object.keys(glossary).length} 件</div>
      </div>
    </div>
  );
};

const styles = {
  toggleButton: {
    position: 'fixed' as const,
    bottom: '20px',
    right: '20px',
    padding: '12px 20px',
    backgroundColor: '#805ad5',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    boxShadow: '0 4px 8px rgba(0,0,0,0.2)',
    zIndex: 1000,
    transition: 'all 0.2s',
  } as React.CSSProperties,
  panel: {
    position: 'fixed' as const,
    bottom: '20px',
    right: '20px',
    width: '400px',
    maxHeight: '600px',
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
    zIndex: 1000,
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  } as React.CSSProperties,
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderBottom: '2px solid #e2e8f0',
    backgroundColor: '#805ad5',
    color: 'white',
  } as React.CSSProperties,
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 'bold' as const,
  } as React.CSSProperties,
  closeButton: {
    backgroundColor: 'transparent',
    border: 'none',
    color: 'white',
    fontSize: '20px',
    cursor: 'pointer',
    padding: '4px 8px',
  } as React.CSSProperties,
  addForm: {
    padding: '16px',
    borderBottom: '2px solid #e2e8f0',
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap' as const,
  } as React.CSSProperties,
  input: {
    flex: '1 1 120px',
    minWidth: '100px',
    padding: '8px 12px',
    border: '2px solid #e2e8f0',
    borderRadius: '6px',
    fontSize: '14px',
  } as React.CSSProperties,
  addButton: {
    padding: '8px 16px',
    backgroundColor: '#48bb78',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    whiteSpace: 'nowrap' as const,
  } as React.CSSProperties,
  list: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '12px',
  } as React.CSSProperties,
  emptyMessage: {
    textAlign: 'center' as const,
    color: '#a0aec0',
    padding: '40px 20px',
    fontSize: '14px',
  } as React.CSSProperties,
  item: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px',
    marginBottom: '8px',
    backgroundColor: '#f7fafc',
    borderRadius: '8px',
    border: '1px solid #e2e8f0',
  } as React.CSSProperties,
  itemContent: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  } as React.CSSProperties,
  itemEnglish: {
    fontWeight: 'bold' as const,
    color: '#2d3748',
    fontSize: '14px',
  } as React.CSSProperties,
  itemArrow: {
    color: '#a0aec0',
    fontSize: '14px',
  } as React.CSSProperties,
  itemJapanese: {
    color: '#4a5568',
    fontSize: '14px',
  } as React.CSSProperties,
  deleteButton: {
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    fontSize: '16px',
    padding: '4px',
    opacity: 0.6,
    transition: 'opacity 0.2s',
  } as React.CSSProperties,
  footer: {
    padding: '12px 16px',
    borderTop: '2px solid #e2e8f0',
    backgroundColor: '#f7fafc',
  } as React.CSSProperties,
  count: {
    fontSize: '12px',
    color: '#718096',
    textAlign: 'center' as const,
  } as React.CSSProperties,
};

export default GlossaryPanel;
