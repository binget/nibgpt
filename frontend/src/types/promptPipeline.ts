export type PromptIntent =
  | "select"
  | "count"
  | "aggregation"
  | "ranking"
  | "trend"
  | "comparison"
  | "expiry_monitoring"
  | "blocked"
  | "unknown";

export interface ExtractedEntity {
  value: string;
  entity_type:
    | "business_term"
    | "time"
    | "status"
    | "aggregation"
    | string;
  confidence: number;
}

export interface ResolvedColumn {
  id: number;
  column_name: string;
  business_name: string | null;
  description: string | null;
  data_type: string;
  classification: string;
  is_sensitive: boolean;
  ai_access_allowed: boolean;
  score: number;
  confidence: number;
  matched_terms: string[];
  reasons: string[];
}

export interface ResolvedTable {
  id: number;
  data_source_id: number;
  schema_name: string | null;
  table_name: string;
  business_name: string | null;
  description: string | null;
  department: string | null;
  data_owner: string | null;
  classification: string;
  definition_status: string;
  ai_access_allowed: boolean;
  score: number;
  confidence: number;
  matched_terms: string[];
  reasons: string[];
  columns: ResolvedColumn[];
}

export interface PromptPipelineResponse {
  prompt: string;
  normalized_prompt: string;

  intent: PromptIntent;
  intent_confidence: number;

  entities: ExtractedEntity[];
  keywords: string[];
  time_expressions: string[];
  status_terms: string[];
  aggregation_terms: string[];

  is_safe: boolean;
  blocked_reason: string | null;

  metadata_confidence: number;
  overall_confidence: number;

  matched_tables: ResolvedTable[];

  warnings: string[];
  explanation: string[];
}
