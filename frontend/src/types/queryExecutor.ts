export interface QueryExecutionRequest {
  prompt: string;
  domain_id?: number | null;
  requested_limit?: number;
  maximum_entities?: number;
  maximum_path_depth?: number;
  user_role?: string;
}

export interface QueryExecutionRow {
  [key: string]: string | number | boolean | null;
}

export interface QueryExecutionResponse {
  success: boolean;

  answer: string | null;

  prompt: string;
  decision: string;

  data_source_id: number | null;
  data_source_name: string | null;

  sql: string | null;

  parameters: Record<string, unknown>;

  columns: string[];
  rows: QueryExecutionRow[];

  row_count: number;
  execution_time_ms: number | null;

  warnings: string[];
  errors: string[];
  explanation: string[];
}