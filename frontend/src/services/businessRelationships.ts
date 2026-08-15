import api from "./api";

import type {
  BusinessRelationship,
  BusinessRelationshipCreate,
  BusinessRelationshipUpdate,
  RelationshipSuggestion,
} from "../types/businessRelationship";

export async function getBusinessRelationships(
  entityId?: number,
  approvalStatus?: string
): Promise<BusinessRelationship[]> {
  const response = await api.get<BusinessRelationship[]>(
    "/api/business-relationships",
    {
      params: {
        entity_id: entityId,
        approval_status: approvalStatus || undefined,
      },
    }
  );

  return response.data;
}

export async function createBusinessRelationship(
  payload: BusinessRelationshipCreate
): Promise<BusinessRelationship> {
  const response = await api.post<BusinessRelationship>(
    "/api/business-relationships",
    payload
  );

  return response.data;
}

export async function updateBusinessRelationship(
  relationshipId: number,
  payload: BusinessRelationshipUpdate
): Promise<BusinessRelationship> {
  const response = await api.put<BusinessRelationship>(
    `/api/business-relationships/${relationshipId}`,
    payload
  );

  return response.data;
}

export async function deleteBusinessRelationship(
  relationshipId: number
): Promise<void> {
  await api.delete(
    `/api/business-relationships/${relationshipId}`
  );
}

export async function suggestBusinessRelationship(
  sourceEntityId: number,
  targetEntityId: number
): Promise<RelationshipSuggestion> {
  const response = await api.get<RelationshipSuggestion>(
    "/api/business-relationships/suggest",
    {
      params: {
        source_entity_id: sourceEntityId,
        target_entity_id: targetEntityId,
      },
    }
  );

  return response.data;
}
