export type CapabilityType =
  | "strategic"
  | "core"
  | "operational"
  | "supporting"
  | "control";

export type CapabilityMaturityLevel =
  | "initial"
  | "developing"
  | "defined"
  | "managed"
  | "optimized";

export type CapabilityApprovalStatus =
  | "draft"
  | "generated"
  | "approved"
  | "rejected";

export type CapabilityEntityMappingRole =
  | "primary"
  | "supporting"
  | "reference"
  | "output";

export interface CapabilityEntityMapping {
  id: number;
  capability_id: number;
  business_entity_id: number;
  mapping_role: CapabilityEntityMappingRole;
  confidence: number;
  is_active: boolean;
  created_at: string;
}

export interface BusinessCapability {
  id: number;
  domain_id: number;
  parent_capability_id: number | null;

  name: string;
  description: string | null;
  business_owner: string | null;

  capability_type: CapabilityType;
  maturity_level: CapabilityMaturityLevel;
  approval_status: CapabilityApprovalStatus;

  confidence: number;
  is_active: boolean;

  created_at: string;
  updated_at: string;

  entity_mappings: CapabilityEntityMapping[];
}

export interface BusinessCapabilityCreate {
  domain_id: number;
  parent_capability_id?: number | null;

  name: string;
  description?: string | null;
  business_owner?: string | null;

  capability_type: CapabilityType;
  maturity_level: CapabilityMaturityLevel;

  confidence: number;
}

export interface BusinessCapabilityUpdate {
  domain_id?: number;
  parent_capability_id?: number | null;

  name?: string;
  description?: string | null;
  business_owner?: string | null;

  capability_type?: CapabilityType;
  maturity_level?: CapabilityMaturityLevel;
  approval_status?: CapabilityApprovalStatus;

  confidence?: number;
  is_active?: boolean;
}

export interface CapabilityEntityMappingCreate {
  business_entity_id: number;
  mapping_role: CapabilityEntityMappingRole;
  confidence: number;
}

export interface CapabilitySuggestion {
  domain_id: number;
  suggested_name: string;
  description: string;
  capability_type: CapabilityType;
  maturity_level: CapabilityMaturityLevel;

  suggested_entity_ids: number[];

  confidence: number;
  reasons: string[];
}
