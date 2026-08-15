export type RelationshipType =
  | "business"
  | "reference"
  | "dependency"
  | "hierarchical"
  | "process";

export type RelationshipCardinality =
  | "one_to_one"
  | "one_to_many"
  | "many_to_one"
  | "many_to_many";

export type RelationshipApprovalStatus =
  | "draft"
  | "generated"
  | "approved"
  | "rejected";

export interface RelationshipEntitySummary {
  id: number;
  domain_id: number;
  name: string;
  description: string | null;
  classification: string;
  approval_status: string;
}

export interface BusinessRelationship {
  id: number;

  source_entity_id: number;
  target_entity_id: number;

  relationship_name: string;
  inverse_relationship_name: string | null;

  relationship_type: RelationshipType;
  cardinality: RelationshipCardinality;

  description: string | null;

  confidence: number;
  approval_status: RelationshipApprovalStatus;
  is_active: boolean;

  created_at: string;
  updated_at: string;

  source_entity: RelationshipEntitySummary;
  target_entity: RelationshipEntitySummary;
}

export interface BusinessRelationshipCreate {
  source_entity_id: number;
  target_entity_id: number;

  relationship_name: string;
  inverse_relationship_name?: string | null;

  relationship_type: RelationshipType;
  cardinality: RelationshipCardinality;

  description?: string | null;
  confidence: number;
}

export interface BusinessRelationshipUpdate {
  relationship_name?: string;
  inverse_relationship_name?: string | null;

  relationship_type?: RelationshipType;
  cardinality?: RelationshipCardinality;

  description?: string | null;
  confidence?: number;

  approval_status?: RelationshipApprovalStatus;
  is_active?: boolean;
}

export interface RelationshipSuggestion {
  source_entity_id: number;
  target_entity_id: number;

  relationship_name: string;
  inverse_relationship_name: string | null;

  relationship_type: RelationshipType;
  cardinality: RelationshipCardinality;

  description: string;
  confidence: number;
  reasons: string[];
}
