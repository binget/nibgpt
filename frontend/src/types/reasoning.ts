export interface ReasoningRequest {
  prompt: string;
  domain_id: number | null;
  maximum_entities: number;
  maximum_path_depth: number;
}

export interface ReasoningDomain {
  id: number;
  name: string;
  description: string | null;
  confidence: number;
  reasons: string[];
}

export interface ReasoningCapability {
  id: number;
  domain_id: number;
  name: string;
  description: string | null;
  capability_type: string;
  maturity_level: string;
  confidence: number;
  reasons: string[];
}

export interface ReasoningEntity {
  id: number;
  domain_id: number;
  name: string;
  description: string | null;
  classification: string;
  confidence: number;
  matched_terms: string[];
  reasons: string[];
}

export interface ReasoningRelationshipStep {
  relationship_id: number;

  source_entity_id: number;
  source_entity_name: string;

  relationship_name: string;

  target_entity_id: number;
  target_entity_name: string;

  confidence: number;
}

export interface ReasoningPath {
  start_entity_id: number;
  end_entity_id: number;

  steps: ReasoningRelationshipStep[];

  confidence: number;
  explanation: string;
}

export interface ReasoningColumn {
  id: number;
  column_name: string;
  business_name: string | null;
  description: string | null;
  data_type: string;
  classification: string;
  is_sensitive: boolean;
  confidence: number;
  matched_terms: string[];
}

export interface ReasoningTable {
  id: number;
  data_source_id: number;

  schema_name: string | null;
  table_name: string;
  business_name: string | null;
  description: string | null;

  entity_id: number;
  entity_name: string;

  mapping_type: string;
  mapping_confidence: number;

  columns: ReasoningColumn[];
}

export interface ReasoningPlan {
  prompt: string;
  normalized_prompt: string;

  intent: string;
  intent_confidence: number;

  selected_domain: ReasoningDomain | null;

  matched_capabilities: ReasoningCapability[];
  matched_entities: ReasoningEntity[];
  relationship_paths: ReasoningPath[];
  physical_tables: ReasoningTable[];

  overall_confidence: number;

  requires_clarification: boolean;
  clarification_questions: string[];

  warnings: string[];
  explanation: string[];
}
