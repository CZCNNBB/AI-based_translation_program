export interface TranslationRequest {
  text: string;
  target_lang?: string;
  domain?: string;
  glossary?: string;
  summary?: boolean;
}

export interface BatchTranslationRequest {
  input_dir: string;
  output_dir: string;
  target_lang?: string;
  domain?: string;
  glossary?: string;
  summary?: boolean;
  file_pattern?: string;
  delete_after?: boolean;
  batch_config?: string;
}

export interface Result<T> {
  code: number;
  msg: string;
  data: T;
}

export interface TranslationResponse {
  original_text: string;
  translated_text: string;
  source_lang?: string;
  target_lang?: string;
  summary?: string;
  [key: string]: any;
}

export interface BatchTranslationResponse {
  total_files: number;
  success_count: number;
  failed_count: number;
  results: Array<{
    input_file: string;
    status: string;
    error?: string;
  }>;
}
