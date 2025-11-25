import axios from 'axios';
import { UploadResponse, TranslationResponse, PageData, TranslatedPage, QualityInfo, ProgressInfo, GlossaryResponse } from './types';

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

export const translatePages = async (pages: PageData[], quality: string = 'balanced'): Promise<TranslationResponse> => {
  const response = await api.post<TranslationResponse>('/api/translate/pages', {
    pages,
    quality,
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
  pageNumbers?: number[]
): Promise<Blob> => {
  const response = await api.post('/api/download/translation', {
    pages,
    format,
    pageNumbers,
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
