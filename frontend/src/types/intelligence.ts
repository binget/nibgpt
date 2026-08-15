export interface IntelligenceColumnMatch {
  id: number;
  column_name: string;
  business_name: string | null;
  description: string | null;
  data_type: string;
  classification: string;
  is_sensitive: boolean;
  ai_access_allowed: boolean;
  score: number;
  matched_terms: string[];
}

export interface IntelligenceTableMatch {
  id: number;
  data_source_id: number;
  schema_name: string | null;
  table_name: string;
  business_name: string | null;
  description: string | null;
  department: string | null;
  data_owner: string | null;
  classification: string;
  ai_access_allowed: boolean;
  score: number;
  confidence: number;
  matched_terms: string[];
  reasons: string[];
  columns: IntelligenceColumnMatch[];
  suggested_questions: string[];
}

export interface PromptAnalysisResponse {
  prompt: string;
  normalized_prompt: string;
  intent: string;
  confidence: number;
  result_count: number;
  warnings: string[];
  matches: IntelligenceTableMatch[];
}
