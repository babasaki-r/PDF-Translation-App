export interface PageData {
  page: number;
  text: string;
  sections: Section[];
  tables: any[];
  metadata: {
    width: number;
    height: number;
    has_tables: boolean;
  };
}

export interface Section {
  text: string;
  metadata: {
    index: number;
    is_heading: boolean;
    is_list: boolean;
    length: number;
  };
}

export interface TranslatedPage {
  page: number;
  original: {
    text: string;
    sections: Section[];
  };
  translated: {
    text: string;
    sections: Array<{
      original: string;
      translated: string;
      metadata: any;
    }>;
  };
  metadata: any;
  tables: any[];
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
