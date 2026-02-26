export interface PageData {
  page: number;
  text: string;
}

export interface TranslatedPage {
  page: number;
  original: {
    text: string;
  };
  translated: {
    text: string;
  };
}

export interface PDFInfo {
  pages: number;
  metadata: any;
  first_page_size: {
    width: number;
    height: number;
  } | null;
}

export interface UploadResponse {
  success: boolean;
  filename: string;
  info: PDFInfo;
  pages: PageData[];
  contains_japanese?: boolean;
}

export type TranslationDirection = 'en-to-ja' | 'ja-to-en';

export type DocumentType =
  | 'steel_technical'
  | 'general_technical'
  | 'academic_paper'
  | 'contract'
  | 'general_document'
  | 'order_acceptance';

export interface DocumentTypeInfo {
  id: DocumentType;
  name: string;
  description: string;
}

export interface DocumentTypesResponse {
  success: boolean;
  document_types: DocumentTypeInfo[];
}

export interface TranslationResponse {
  success: boolean;
  pages: TranslatedPage[];
  quality?: string;
}

export interface ProgressInfo {
  success: boolean;
  progress: {
    current: number;
    total: number;
    percentage: number;
  };
}

export interface GlossaryResponse {
  success: boolean;
  glossary: Record<string, string>;
  count: number;
}
