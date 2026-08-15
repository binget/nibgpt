export type BusinessRuleApprovalStatus =
  | "draft"
  | "generated"
  | "approved"
  | "rejected";

export type BusinessRuleOperator =
  | "="
  | "!="
  | ">"
  | ">="
  | "<"
  | "<="
  | "like"
  | "not like"
  | "between_or_between";

export interface BusinessRuleEntity {
  id: number;
  name: string;
  classification: string;
  approval_status: string;
}

export interface BusinessRuleColumn {
  id: number;
  metadata_table_id: number;
  column_name: string;
  business_name: string | null;
  data_type: string;
  classification: string;
  is_sensitive: boolean;
}

export interface BusinessRule {
  id: number;

  business_entity_id: number;
  metadata_column_id: number;

  name: string;
  trigger_phrase: string;

  synonyms: string | null;

  operator: BusinessRuleOperator;
  rule_value: string;

  description: string | null;

  confidence: number;

  approval_status: BusinessRuleApprovalStatus;
  is_active: boolean;

  created_at: string;
  updated_at: string;

  entity: BusinessRuleEntity;
  column: BusinessRuleColumn;
}

export interface BusinessRuleCreate {
  business_entity_id: number;
  metadata_column_id: number;

  name: string;
  trigger_phrase: string;

  synonyms?: string | null;

  operator: BusinessRuleOperator;
  rule_value: string;

  description?: string | null;

  confidence: number;

  approval_status: BusinessRuleApprovalStatus;
  is_active: boolean;
}

export interface BusinessRuleUpdate {
  business_entity_id?: number;
  metadata_column_id?: number;

  name?: string;
  trigger_phrase?: string;

  synonyms?: string | null;

  operator?: BusinessRuleOperator;
  rule_value?: string;

  description?: string | null;

  confidence?: number;

  approval_status?: BusinessRuleApprovalStatus;
  is_active?: boolean;
}