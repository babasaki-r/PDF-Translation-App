import axios from 'axios';
import { UploadResponse, TranslationResponse, PageData, TranslatedPage, QualityInfo, ProgressInfo, GlossaryResponse, TranslationDirection, DocumentType, DocumentTypesResponse } from './types';

const API_BASE_URL = 'http://localhost:8002';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadPDF = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await axios.post<UploadResponse>(
    `${API_BASE_URL}/api/pdf/upload`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );

  return response.data;
};

export const translatePages = async (pages: PageData[], quality: string = 'balanced', direction: TranslationDirection = 'en-to-ja'): Promise<TranslationResponse> => {
  const response = await api.post<TranslationResponse>('/api/translate/pages', {
    pages,
    quality,
    direction,
  });

  return response.data;
};

export const healthCheck = async (): Promise<{ status: string; model_loaded: boolean }> => {
  const response = await api.get('/health');
  return response.data;
};

// 進捗確認
export const getProgress = async (): Promise<ProgressInfo> => {
  const response = await api.get<ProgressInfo>('/api/translate/progress');
  return response.data;
};

// 翻訳キャンセル
export const cancelTranslation = async (): Promise<{ success: boolean; message: string }> => {
  const response = await api.post('/api/translate/cancel');
  return response.data;
};

// 品質情報取得
export const getQualityInfo = async (): Promise<QualityInfo> => {
  const response = await api.get<QualityInfo>('/api/quality/info');
  return response.data;
};

// 品質設定変更
export const setQuality = async (quality: string): Promise<{ success: boolean; quality: string }> => {
  const response = await api.post('/api/quality/set', { quality });
  return response.data;
};

// テキストファイルダウンロード
export const downloadTranslation = async (
  pages: TranslatedPage[],
  format: 'original' | 'translated' | 'both' = 'both',
  pageNumbers?: number[],
  documentType?: DocumentType,
  translationEngine?: 'ollama' | 'swallow' | 'apple',
  ollamaModel?: string
): Promise<Blob> => {
  const response = await api.post('/api/download/translation', {
    pages,
    format,
    pageNumbers,
    documentType,
    translationEngine,
    ollamaModel,
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

// PDFの内容について質問
export const askQuestion = async (question: string, context: string): Promise<{
  success: boolean;
  question: string;
  answer: string;
}> => {
  const response = await api.post('/api/ask', { question, context });
  return response.data;
};

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

// ========== Ollama翻訳 API ==========

// Ollamaモデル情報の型
export interface OllamaModel {
  id: string;
  name: string;
  description: string;
  size: string;
}

// Ollamaステータス型
export interface OllamaStatus {
  success: boolean;
  available: boolean;
  current_model: string;
  base_url: string;
}

// Ollamaステータス取得
export const getOllamaStatus = async (): Promise<OllamaStatus> => {
  const response = await api.get<OllamaStatus>('/api/ollama/status');
  return response.data;
};

// Ollamaモデル一覧取得
export const getOllamaModels = async (): Promise<{
  success: boolean;
  models: OllamaModel[];
  current_model: string;
}> => {
  const response = await api.get('/api/ollama/models');
  return response.data;
};

// Ollamaモデル変更
export const setOllamaModel = async (model: string): Promise<{
  success: boolean;
  model: string;
  message: string;
}> => {
  const response = await api.post('/api/ollama/model/set', { model });
  return response.data;
};

// Ollama翻訳
export const translatePagesOllama = async (
  pages: PageData[],
  model?: string,
  direction: TranslationDirection = 'en-to-ja',
  documentType: DocumentType = 'steel_technical'
): Promise<TranslationResponse> => {
  const response = await api.post<TranslationResponse>('/api/translate/ollama', {
    pages,
    model,
    direction,
    document_type: documentType,
  });
  return response.data;
};

// Ollama翻訳の進捗確認
export const getOllamaProgress = async (): Promise<ProgressInfo> => {
  const response = await api.get<ProgressInfo>('/api/translate/ollama/progress');
  return response.data;
};

// Ollama翻訳キャンセル
export const cancelOllamaTranslation = async (): Promise<{ success: boolean; message: string }> => {
  const response = await api.post('/api/translate/ollama/cancel');
  return response.data;
};

// Ollamaで質問
export const askQuestionOllama = async (question: string, context: string, model?: string): Promise<{
  success: boolean;
  question: string;
  answer: string;
  model: string;
}> => {
  const response = await api.post('/api/ask/ollama', { question, context, model });
  return response.data;
};

// ========== Swallow翻訳 API ==========

// Swallowモデルのステータス型
export interface SwallowStatus {
  success: boolean;
  loaded: boolean;
  loading: boolean;
  error: string | null;
}

// Swallowモデルステータス取得
export const getSwallowStatus = async (): Promise<SwallowStatus> => {
  const response = await api.get<SwallowStatus>('/api/swallow/status');
  return response.data;
};

// Swallow翻訳
export const translatePagesSwallow = async (
  pages: PageData[],
  direction: TranslationDirection = 'en-to-ja',
  documentType: DocumentType = 'steel_technical'
): Promise<TranslationResponse> => {
  const response = await api.post<TranslationResponse>('/api/translate/swallow', {
    pages,
    direction,
    document_type: documentType,
  });
  return response.data;
};

// Swallow翻訳の進捗確認
export const getSwallowProgress = async (): Promise<ProgressInfo> => {
  const response = await api.get<ProgressInfo>('/api/translate/swallow/progress');
  return response.data;
};

// Swallow翻訳キャンセル
export const cancelSwallowTranslation = async (): Promise<{ success: boolean; message: string }> => {
  const response = await api.post('/api/translate/swallow/cancel');
  return response.data;
};

// ========== 文書タイプ API ==========

// 文書タイプ一覧取得
export const getDocumentTypes = async (): Promise<DocumentTypesResponse> => {
  const response = await api.get<DocumentTypesResponse>('/api/document-types');
  return response.data;
};

// ========== エンジン切り替え API ==========

// エンジン切り替え（モデル解放）
export const switchEngine = async (engine: 'ollama' | 'swallow' | 'apple'): Promise<{
  success: boolean;
  engine: string;
  message: string;
}> => {
  const response = await api.post('/api/engine/switch', { engine });
  return response.data;
};
