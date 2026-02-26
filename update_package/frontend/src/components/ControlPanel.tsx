import React, { useState, useEffect } from 'react';
import { downloadTranslation, getDocumentTypes, MLXStatus } from '../api';
import { TranslatedPage, TranslationDirection, DocumentType, DocumentTypeInfo } from '../types';

interface ControlPanelProps {
  translatedPages: TranslatedPage[];
  currentPage: number;
  translationProgress?: {
    current: number;
    total: number;
    percentage: number;
  } | null;
  isTranslating: boolean;
  translationEngine: 'mlx' | 'apple';
  onEngineChange: (engine: 'mlx' | 'apple') => void;
  translationDirection: TranslationDirection;
  onDirectionChange: (direction: TranslationDirection) => void;
  documentType: DocumentType;
  onDocumentTypeChange: (type: DocumentType) => void;
  mlxStatus?: MLXStatus | null;
}

const ControlPanel: React.FC<ControlPanelProps> = ({
  translatedPages,
  currentPage,
  translationProgress,
  isTranslating,
  translationEngine,
  onEngineChange,
  translationDirection,
  onDirectionChange,
  documentType,
  onDocumentTypeChange,
  mlxStatus,
}) => {
  const [downloadFormat, setDownloadFormat] = useState<'original' | 'translated' | 'both'>('both');
  const [isDownloading, setIsDownloading] = useState(false);
  const [isDownloadExpanded, setIsDownloadExpanded] = useState(false);
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
        // フォールバック
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
      const blob = await downloadTranslation(
        translatedPages,
        downloadFormat,
        pageNumbers,
        documentType,
        translationEngine
      );

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

  // エンジン表示名を取得
  const getEngineDisplayName = () => {
    return translationEngine === 'apple' ? '簡易翻訳' : 'AI翻訳';
  };

  return (
    <div style={styles.container}>
      {/* 翻訳設定セクション（常に表示） */}
      <div style={styles.settingsSection}>
        {/* 翻訳方向選択 */}
        <div style={styles.settingRow}>
          <label style={styles.settingLabel}>翻訳方向:</label>
          <div style={styles.directionButtons}>
            <button
              onClick={() => onDirectionChange('en-to-ja')}
              style={{
                ...styles.directionButton,
                ...(translationDirection === 'en-to-ja' ? styles.directionButtonActive : {}),
              }}
              disabled={isTranslating}
            >
              英語 → 日本語
            </button>
            <button
              onClick={() => onDirectionChange('ja-to-en')}
              style={{
                ...styles.directionButton,
                ...(translationDirection === 'ja-to-en' ? styles.directionButtonActive : {}),
              }}
              disabled={isTranslating}
            >
              日本語 → 英語
            </button>
          </div>
        </div>

        {/* 翻訳エンジン選択（2ボタン） */}
        <div style={styles.settingRow}>
          <label style={styles.settingLabel}>翻訳エンジン:</label>
          <div style={styles.engineButtons}>
            <button
              onClick={() => onEngineChange('mlx')}
              style={{
                ...styles.engineButton,
                ...(translationEngine === 'mlx' ? styles.engineButtonMLXActive : {}),
              }}
              disabled={isTranslating}
            >
              AI翻訳
            </button>
            <button
              onClick={() => onEngineChange('apple')}
              style={{
                ...styles.engineButton,
                ...(translationEngine === 'apple' ? styles.engineButtonAppleActive : {}),
              }}
              disabled={isTranslating}
            >
              簡易翻訳
            </button>
          </div>
        </div>

        {/* MLX接続状態（MLX選択時のみ表示） */}
        {translationEngine === 'mlx' && mlxStatus && (
          <div style={styles.settingRow}>
            <label style={styles.settingLabel}>状態:</label>
            <div style={styles.statusContainer}>
              {mlxStatus.available ? (
                <div style={styles.mlxStatusReady}>
                  <span>✓</span>
                  <span>接続OK (Qwen2.5-7B)</span>
                </div>
              ) : (
                <div style={styles.mlxStatusError}>
                  <span>✗</span>
                  <span>MLXサーバーに接続できません</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 文書タイプ選択（簡易翻訳以外のみ表示） */}
        {translationEngine !== 'apple' && (
          <div style={styles.settingRow}>
            <label style={styles.settingLabel}>文書タイプ:</label>
            <select
              value={documentType}
              onChange={(e) => onDocumentTypeChange(e.target.value as DocumentType)}
              style={styles.documentTypeSelect}
              disabled={isTranslating}
            >
              {documentTypes.map((type) => (
                <option key={type.id} value={type.id}>
                  {type.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* 現在の設定表示 */}
        <div style={styles.currentSettings}>
          <span style={styles.currentSettingsLabel}>現在の設定:</span>
          <span style={styles.currentSettingsValue}>
            {translationDirection === 'en-to-ja' ? '英→日' : '日→英'} / {getEngineDisplayName()}
          </span>
        </div>
      </div>

      {/* 翻訳進捗（翻訳中のみ表示） */}
      {isTranslating && translationProgress && (
        <div style={styles.section}>
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

      {/* ダウンロード（折りたたみ可能、翻訳完了後のみ表示） */}
      {translatedPages.length > 0 && !isTranslating && (
        <div style={styles.section}>
          <div
            style={styles.sectionHeader}
            onClick={() => setIsDownloadExpanded(!isDownloadExpanded)}
          >
            <h3 style={styles.sectionTitle}>
              {isDownloadExpanded ? '▼' : '▶'} ダウンロード
            </h3>
            <span style={styles.currentSelection}>
              {translatedPages.length}ページ準備完了
            </span>
          </div>
          {isDownloadExpanded && (
            <div style={styles.expandedContent}>
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
                  現在のページ
                </button>
                <button
                  onClick={() => handleDownload('all')}
                  style={styles.downloadButtonPrimary}
                  disabled={isDownloading}
                >
                  全ページ ({translatedPages.length}ページ)
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    padding: '12px',
    backgroundColor: '#f8f9fa',
    borderBottom: '1px solid #e2e8f0',
  } as React.CSSProperties,
  settingsSection: {
    padding: '12px',
    backgroundColor: 'white',
    borderRadius: '8px',
    border: '1px solid #e2e8f0',
    marginBottom: '12px',
  } as React.CSSProperties,
  settingRow: {
    display: 'flex',
    alignItems: 'center',
    marginBottom: '12px',
    gap: '12px',
  } as React.CSSProperties,
  settingLabel: {
    fontSize: '13px',
    fontWeight: 'bold' as const,
    color: '#4a5568',
    minWidth: '80px',
  } as React.CSSProperties,
  directionButtons: {
    display: 'flex',
    gap: '8px',
    flex: 1,
  } as React.CSSProperties,
  directionButton: {
    flex: 1,
    padding: '8px 12px',
    backgroundColor: 'white',
    border: '2px solid #e2e8f0',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    transition: 'all 0.2s',
    color: '#4a5568',
  } as React.CSSProperties,
  directionButtonActive: {
    borderColor: '#2b6cb0',
    backgroundColor: '#ebf8ff',
    color: '#2b6cb0',
  } as React.CSSProperties,
  engineButtons: {
    display: 'flex',
    gap: '8px',
    flex: 1,
  } as React.CSSProperties,
  engineButton: {
    flex: 1,
    padding: '8px 12px',
    backgroundColor: 'white',
    border: '2px solid #e2e8f0',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    transition: 'all 0.2s',
    color: '#4a5568',
  } as React.CSSProperties,
  engineButtonMLXActive: {
    borderColor: '#805ad5',
    backgroundColor: '#faf5ff',
    color: '#805ad5',
  } as React.CSSProperties,
  engineButtonAppleActive: {
    borderColor: '#38a169',
    backgroundColor: '#f0fff4',
    color: '#38a169',
  } as React.CSSProperties,
  statusContainer: {
    flex: 1,
  } as React.CSSProperties,
  mlxStatusReady: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 12px',
    backgroundColor: '#e9d8fd',
    border: '2px solid #805ad5',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: 'bold' as const,
    color: '#553c9a',
  } as React.CSSProperties,
  mlxStatusError: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 12px',
    backgroundColor: '#fed7d7',
    border: '2px solid #e53e3e',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: 'bold' as const,
    color: '#c53030',
  } as React.CSSProperties,
  documentTypeSelect: {
    flex: 1,
    padding: '8px 12px',
    backgroundColor: 'white',
    border: '2px solid #dd6b20',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: 'bold' as const,
    cursor: 'pointer',
    color: '#c05621',
  } as React.CSSProperties,
  currentSettings: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 12px',
    backgroundColor: '#f7fafc',
    borderRadius: '6px',
    marginTop: '4px',
  } as React.CSSProperties,
  currentSettingsLabel: {
    fontSize: '12px',
    color: '#718096',
  } as React.CSSProperties,
  currentSettingsValue: {
    fontSize: '13px',
    fontWeight: 'bold' as const,
    color: '#2d3748',
  } as React.CSSProperties,
  section: {
    marginBottom: '12px',
  } as React.CSSProperties,
  sectionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px',
    backgroundColor: 'white',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    border: '1px solid #e2e8f0',
  } as React.CSSProperties,
  sectionTitle: {
    fontSize: '14px',
    fontWeight: 'bold' as const,
    margin: 0,
    color: '#2d3748',
    userSelect: 'none' as const,
  } as React.CSSProperties,
  currentSelection: {
    fontSize: '12px',
    color: '#718096',
    fontWeight: 'normal' as const,
  } as React.CSSProperties,
  expandedContent: {
    marginTop: '8px',
    padding: '12px',
    backgroundColor: 'white',
    borderRadius: '6px',
    border: '1px solid #e2e8f0',
  } as React.CSSProperties,
  progressContainer: {
    padding: '12px',
    backgroundColor: 'white',
    borderRadius: '6px',
    border: '1px solid #e2e8f0',
  } as React.CSSProperties,
  progressBar: {
    width: '100%',
    height: '20px',
    backgroundColor: '#e2e8f0',
    borderRadius: '10px',
    overflow: 'hidden',
    marginBottom: '6px',
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
    backgroundColor: '#f7fafc',
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
