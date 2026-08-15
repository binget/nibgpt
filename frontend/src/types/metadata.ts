export type DataClassification =
  | "public"
  | "internal"
  | "confidential"
  | "restricted";

export interface MetadataColumn {
  id: number;
  column_name: string;
  data_type: string;
  ordinal_position: number;
  is_nullable: boolean;
  is_primary_key: boolean;
  default_value: string | null;
  business_name: string | null;
  description: string | null;
  classification: DataClassification;
  ai_access_allowed: boolean;
  is_sensitive: boolean;
  is_enabled: boolean;
  synonyms: string | null;
  definition_status:
  | "not_generated"
  | "generated"
  | "approved"
  | "rejected";
}

export interface MetadataTableSummary {
  id: number;
  data_source_id: number;
  schema_name: string | null;
  table_name: string;
  object_type: "table" | "view";
  business_name: string | null;
  description: string | null;
  data_owner: string | null;
  department: string | null;
  classification: DataClassification;
  ai_access_allowed: boolean;
  is_enabled: boolean;
  discovered_at: string;
  synonyms: string | null;
  suggested_questions: string | null;
  definition_status:
  | "not_generated"
  | "generated"
  | "approved"
  | "rejected";
}

export interface MetadataTableDetail
  extends MetadataTableSummary {
  columns: MetadataColumn[];
}

export interface MetadataScanResponse {
  success: boolean;
  data_source_id: number;
  schemas_scanned: number;
  tables_discovered: number;
  views_discovered: number;
  columns_discovered: number;
  message: string;
}

export interface MetadataTableUpdate {
  business_name?: string | null;
  description?: string | null;
  data_owner?: string | null;
  department?: string | null;
  classification?: DataClassification;
  ai_access_allowed?: boolean;
  is_enabled?: boolean;
}

export interface MetadataColumnUpdate {
  business_name?: string | null;
  description?: string | null;
  classification?: DataClassification;
  ai_access_allowed?: boolean;
  is_sensitive?: boolean;
  is_enabled?: boolean;
}

export interface GeneratedColumnDefinition {
  column_id: number;
  technical_name: string;
  business_name: string;
  description: string;
  synonyms: string[];
  classification: DataClassification;
  is_sensitive: boolean;
}

export interface GeneratedTableDefinition {
  table_id: number;
  technical_name: string;
  business_name: string;
  description: string;
  synonyms: string[];
  suggested_questions: string[];
  columns: GeneratedColumnDefinition[];
}