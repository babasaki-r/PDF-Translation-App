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

export interface QualityOption {
  model: string;
  description: string;
  speed: string;
  quality: string;
}

export interface QualityInfo {
  success: boolean;
  current: string;
  options: {
    high: QualityOption;
    balanced: QualityOption;
    fast: QualityOption;
  };
}

export interface GlossaryResponse {
  success: boolean;
  glossary: Record<string, string>;
  count: number;
}
