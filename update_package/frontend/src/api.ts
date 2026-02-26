import axios from 'axios';
import { UploadResponse, TranslationResponse, PageData, TranslatedPage, ProgressInfo, GlossaryResponse, TranslationDirection, DocumentType, DocumentTypesResponse } from './types';

const API_BASE_URL = 'http://localhost:8002';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5分（翻訳処理は長時間かかる場合がある）
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadPDF = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<UploadResponse>(
    '/api/pdf/upload',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 120000, // アップロードは2分タイムアウト
    }
  );

  return response.data;
};

export const healthCheck = async (): Promise<{ status: string; engines: string[] }> => {
  const response = await api.get('/health');
  return response.data;
};

// テキストファイルダウンロード
export const downloadTranslation = async (
  pages: TranslatedPage[],
  format: 'original' | 'translated' | 'both' = 'both',
  pageNumbers?: number[],
  documentType?: DocumentType,
  translationEngine?: 'mlx' | 'apple'
): Promise<Blob> => {
  const response = await api.post('/api/download/translation', {
    pages,
    format,
    pageNumbers,
    documentType,
    translationEngine,
  }, {
    responseType: 'blob',
  });

  return response.data;
};

// 用語集取得
export const getGlossary = async (): Promise<GlossaryResponse> => {
  const response = await api.get<GlossaryResponse>('/api/glossary');
  return response.data;
};

// 用語追加
export const addGlossaryTerm = async (english: string, japanese: string): Promise<{ success: boolean }> => {
  const response = await api.post('/api/glossary/add', { english, japanese });
  return response.data;
};

// 用語集更新
export const updateGlossary = async (glossary: Record<string, string>): Promise<{ success: boolean }> => {
  const response = await api.post('/api/glossary/update', { glossary });
  return response.data;
};

// ========== Apple翻訳 API ==========

// Apple翻訳（軽量翻訳）
export const translatePagesApple = async (pages: PageData[], direction: TranslationDirection = 'en-to-ja'): Promise<TranslationResponse> => {
  const response = await api.post<TranslationResponse>('/api/translate/apple', {
    pages,
    direction,
  });
  return response.data;
};

// Apple翻訳の進捗確認
export const getAppleProgress = async (): Promise<ProgressInfo> => {
  const response = await api.get<ProgressInfo>('/api/translate/apple/progress');
  return response.data;
};

// Apple翻訳キャンセル
export const cancelAppleTranslation = async (): Promise<{ success: boolean; message: string }> => {
  const response = await api.post('/api/translate/apple/cancel');
  return response.data;
};

// ========== MLX翻訳 API ==========

// MLXステータス型
export interface MLXStatus {
  success: boolean;
  available: boolean;
  model: string;
  base_url: string;
}

// MLXステータス取得
export const getMLXStatus = async (): Promise<MLXStatus> => {
  const response = await api.get<MLXStatus>('/api/mlx/status');
  return response.data;
};

// MLX翻訳
export const translatePagesMLX = async (
  pages: PageData[],
  direction: TranslationDirection = 'en-to-ja',
  documentType: DocumentType = 'steel_technical'
): Promise<TranslationResponse> => {
  const response = await api.post<TranslationResponse>('/api/translate/mlx', {
    pages,
    direction,
    document_type: documentType,
  });
  return response.data;
};

// MLX翻訳の進捗確認
export const getMLXProgress = async (): Promise<ProgressInfo> => {
  const response = await api.get<ProgressInfo>('/api/translate/mlx/progress');
  return response.data;
};

// MLX翻訳キャンセル
export const cancelMLXTranslation = async (): Promise<{ success: boolean; message: string }> => {
  const response = await api.post('/api/translate/mlx/cancel');
  return response.data;
};

// MLXで質問
export const askQuestionMLX = async (question: string, context: string): Promise<{
  success: boolean;
  question: string;
  answer: string;
  model: string;
}> => {
  const response = await api.post('/api/ask/mlx', { question, context });
  return response.data;
};

// ========== 文書タイプ API ==========

// 文書タイプ一覧取得
export const getDocumentTypes = async (): Promise<DocumentTypesResponse> => {
  const response = await api.get<DocumentTypesResponse>('/api/document-types');
  return response.data;
};
