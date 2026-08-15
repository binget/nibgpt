import api from "./api";

import type {
  BusinessCapability,
  BusinessCapabilityCreate,
  BusinessCapabilityUpdate,
  CapabilityEntityMapping,
  CapabilityEntityMappingCreate,
  CapabilitySuggestion,
} from "../types/businessCapability";

export async function getBusinessCapabilities(
  domainId?: number,
  approvalStatus?: string
): Promise<BusinessCapability[]> {
  const response = await api.get<BusinessCapability[]>(
    "/api/business-capabilities",
    {
      params: {
        domain_id: domainId,
        approval_status: approvalStatus || undefined,
      },
    }
  );

  return response.data;
}

export async function createBusinessCapability(
  payload: BusinessCapabilityCreate
): Promise<BusinessCapability> {
  const response = await api.post<BusinessCapability>(
    "/api/business-capabilities",
    payload
  );

  return response.data;
}

export async function updateBusinessCapability(
  capabilityId: number,
  payload: BusinessCapabilityUpdate
): Promise<BusinessCapability> {
  const response = await api.put<BusinessCapability>(
    `/api/business-capabilities/${capabilityId}`,
    payload
  );

  return response.data;
}

export async function deleteBusinessCapability(
  capabilityId: number
): Promise<void> {
  await api.delete(
    `/api/business-capabilities/${capabilityId}`
  );
}

export async function createCapabilityEntityMapping(
  capabilityId: number,
  payload: CapabilityEntityMappingCreate
): Promise<CapabilityEntityMapping> {
  const response =
    await api.post<CapabilityEntityMapping>(
      `/api/business-capabilities/${capabilityId}/entity-mappings`,
      payload
    );

  return response.data;
}

export async function deleteCapabilityEntityMapping(
  mappingId: number
): Promise<void> {
  await api.delete(
    `/api/business-capabilities/entity-mappings/${mappingId}`
  );
}

export async function suggestBusinessCapability(
  domainId: number,
  entityIds: number[]
): Promise<CapabilitySuggestion> {
  const response = await api.get<CapabilitySuggestion>(
    "/api/business-capabilities/suggest",
    {
      params: {
        domain_id: domainId,
        entity_ids: entityIds,
      },
      paramsSerializer: {
        indexes: null,
      },
    }
  );

  return response.data;
}
