export type SupportedSqlDialect =
  | "mysql"
  | "postgresql"
  | "oracle"
  | "mssql";

export interface SqlCompilerRequest {
  prompt: string;
  domain_id: number | null;
  requested_limit: number;
  maximum_entities: number;
  maximum_path_depth: number;
  user_role: string;
}

export interface CompiledParameter {
  name: string;
  value: unknown;
  data_type: string;
}

export interface CompiledTable {
  metadata_table_id: number;
  data_source_id: number;
  schema_name: string | null;
  table_name: string;
  alias: string;
}

export interface CompiledJoin {
  join_mapping_id: number;
  relationship_id: number;
  join_type: string;

  source_table_alias: string;
  source_column_name: string;

  target_table_alias: string;
  target_column_name: string;

  expression: string;
}

export interface SqlCompilerResult {
  prompt: string;

  decision: string;
  is_compiled: boolean;

  dialect: SupportedSqlDialect | null;

  sql: string | null;

  parameters: CompiledParameter[];
  tables: CompiledTable[];
  joins: CompiledJoin[];

  approved_limit: number;
  overall_confidence: number;

  warnings: string[];
  errors: string[];
  explanation: string[];
}
