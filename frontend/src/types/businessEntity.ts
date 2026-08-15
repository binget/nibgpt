export type EntityClassification =
  | "public"
  | "internal"
  | "confidential"
  | "restricted";

export type EntityApprovalStatus =
  | "draft"
  | "generated"
  | "approved"
  | "rejected";

export type EntityMappingType =
  | "primary"
  | "supporting"
  | "reference";


export interface BusinessDomain {
  id: number;
  name: string;
  description: string | null;
  department: string | null;
  owner: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}


export interface BusinessDomainCreate {
  name: string;
  description?: string | null;
  department?: string | null;
  owner?: string | null;
}


export interface BusinessDomainUpdate {
  name?: string;
  description?: string | null;
  department?: string | null;
  owner?: string | null;
  is_active?: boolean;
}


export interface EntityTableMapping {
  id: number;
  metadata_table_id: number;
  mapping_type: EntityMappingType;
  confidence: number;
  is_active: boolean;
  created_at: string;
}


export interface BusinessEntity {
  id: number;
  domain_id: number;
  name: string;
  description: string | null;
  synonyms: string | null;
  business_owner: string | null;
  classification: EntityClassification;
  ai_access_allowed: boolean;
  approval_status: EntityApprovalStatus;
  confidence: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  table_mappings: EntityTableMapping[];
}


export interface BusinessEntityCreate {
  domain_id: number;
  name: string;
  description?: string | null;
  synonyms: string[];
  business_owner?: string | null;
  classification: EntityClassification;
  ai_access_allowed: boolean;
  confidence: number;
}


export interface BusinessEntityUpdate {
  domain_id?: number;
  name?: string;
  description?: string | null;
  synonyms?: string[];
  business_owner?: string | null;
  classification?: EntityClassification;
  ai_access_allowed?: boolean;
  approval_status?: EntityApprovalStatus;
  confidence?: number;
  is_active?: boolean;
}


export interface EntityTableMappingCreate {
  metadata_table_id: number;
  mapping_type: EntityMappingType;
  confidence: number;
}


export interface BusinessEntitySuggestion {
  metadata_table_id: number;
  suggested_domain_name: string;
  suggested_entity_name: string;
  description: string;
  synonyms: string[];
  confidence: number;
  reasons: string[];
}
