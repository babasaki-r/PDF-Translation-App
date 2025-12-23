import React, { useState, useEffect, useMemo } from 'react';
import { getGlossary, addGlossaryTerm, updateGlossary } from '../api';

type SortType = 'english-asc' | 'english-desc' | 'japanese-asc' | 'japanese-desc' | 'recent';

const GlossaryPanel: React.FC = () => {
  const [glossary, setGlossary] = useState<Record<string, string>>({});
  const [isOpen, setIsOpen] = useState(false);
  const [newEnglish, setNewEnglish] = useState('');
  const [newJapanese, setNewJapanese] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortType, setSortType] = useState<SortType>('english-asc');

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

  // フィルター&ソートされた用語リスト
  const filteredAndSortedGlossary = useMemo(() => {
    const entries = Object.entries(glossary);

    // 検索フィルター
    const filtered = entries.filter(([english, japanese]) => {
      if (!searchQuery.trim()) return true;
      const query = searchQuery.toLowerCase();
      return (
        english.toLowerCase().includes(query) ||
        japanese.toLowerCase().includes(query)
      );
    });

    // ソート
    filtered.sort((a, b) => {
      switch (sortType) {
        case 'english-asc':
          return a[0].localeCompare(b[0]);
        case 'english-desc':
          return b[0].localeCompare(a[0]);
        case 'japanese-asc':
          return a[1].localeCompare(b[1], 'ja');
        case 'japanese-desc':
          return b[1].localeCompare(a[1], 'ja');
        case 'recent':
        default:
          return 0; // 追加順（デフォルト）
      }
    });

    return filtered;
  }, [glossary, searchQuery, sortType]);

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
          onKeyPress={(e) => e.key === 'Enter' && handleAddTerm()}
          style={styles.input}
        />
        <input
          type="text"
          placeholder="日本語"
          value={newJapanese}
          onChange={(e) => setNewJapanese(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleAddTerm()}
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

      {/* 検索とソート */}
      <div style={styles.controlsBar}>
        <input
          type="text"
          placeholder="🔍 検索..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={styles.searchInput}
        />
        <select
          value={sortType}
          onChange={(e) => setSortType(e.target.value as SortType)}
          style={styles.sortSelect}
        >
          <option value="english-asc">英語 A→Z</option>
          <option value="english-desc">英語 Z→A</option>
          <option value="japanese-asc">日本語 あ→ん</option>
          <option value="japanese-desc">日本語 ん→あ</option>
        </select>
      </div>

      {/* 用語リスト（テーブル形式） */}
      <div style={styles.tableContainer}>
        {Object.keys(glossary).length === 0 ? (
          <div style={styles.emptyMessage}>用語がありません</div>
        ) : filteredAndSortedGlossary.length === 0 ? (
          <div style={styles.emptyMessage}>検索結果がありません</div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr style={styles.tableHeaderRow}>
                <th style={styles.tableHeader}>英語</th>
                <th style={styles.tableHeader}>日本語</th>
                <th style={styles.tableHeaderAction}>操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSortedGlossary.map(([english, japanese], index) => (
                <tr
                  key={english}
                  style={{
                    ...styles.tableRow,
                    backgroundColor: index % 2 === 0 ? '#ffffff' : '#f7fafc'
                  }}
                >
                  <td style={styles.tableCell}>{english}</td>
                  <td style={styles.tableCell}>{japanese}</td>
                  <td style={styles.tableCellAction}>
                    <button
                      onClick={() => handleDeleteTerm(english)}
                      style={styles.deleteButton}
                      title="削除"
                    >
                      🗑️
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div style={styles.footer}>
        <div style={styles.count}>
          {filteredAndSortedGlossary.length !== Object.keys(glossary).length
            ? `${filteredAndSortedGlossary.length} / ${Object.keys(glossary).length} 件表示`
            : `登録数: ${Object.keys(glossary).length} 件`}
        </div>
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
    width: '600px',
    maxHeight: '700px',
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
  controlsBar: {
    display: 'flex',
    gap: '12px',
    padding: '12px 16px',
    borderBottom: '1px solid #e2e8f0',
    backgroundColor: '#fafafa',
  } as React.CSSProperties,
  searchInput: {
    flex: 1,
    padding: '8px 12px',
    border: '2px solid #e2e8f0',
    borderRadius: '6px',
    fontSize: '14px',
  } as React.CSSProperties,
  sortSelect: {
    padding: '8px 12px',
    border: '2px solid #e2e8f0',
    borderRadius: '6px',
    fontSize: '14px',
    backgroundColor: 'white',
    cursor: 'pointer',
    minWidth: '140px',
  } as React.CSSProperties,
  tableContainer: {
    flex: 1,
    overflowY: 'auto' as const,
    overflowX: 'auto' as const,
  } as React.CSSProperties,
  emptyMessage: {
    textAlign: 'center' as const,
    color: '#a0aec0',
    padding: '40px 20px',
    fontSize: '14px',
  } as React.CSSProperties,
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
  } as React.CSSProperties,
  tableHeaderRow: {
    backgroundColor: '#f7fafc',
    borderBottom: '2px solid #e2e8f0',
  } as React.CSSProperties,
  tableHeader: {
    padding: '12px 16px',
    textAlign: 'left' as const,
    fontSize: '13px',
    fontWeight: 'bold' as const,
    color: '#4a5568',
    position: 'sticky' as const,
    top: 0,
    backgroundColor: '#f7fafc',
    zIndex: 1,
  } as React.CSSProperties,
  tableHeaderAction: {
    padding: '12px 16px',
    textAlign: 'center' as const,
    fontSize: '13px',
    fontWeight: 'bold' as const,
    color: '#4a5568',
    width: '60px',
    position: 'sticky' as const,
    top: 0,
    backgroundColor: '#f7fafc',
    zIndex: 1,
  } as React.CSSProperties,
  tableRow: {
    borderBottom: '1px solid #e2e8f0',
    transition: 'background-color 0.1s',
  } as React.CSSProperties,
  tableCell: {
    padding: '12px 16px',
    fontSize: '14px',
    color: '#2d3748',
    wordBreak: 'break-word' as const,
  } as React.CSSProperties,
  tableCellAction: {
    padding: '12px 16px',
    textAlign: 'center' as const,
    width: '60px',
  } as React.CSSProperties,
  deleteButton: {
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    fontSize: '18px',
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
