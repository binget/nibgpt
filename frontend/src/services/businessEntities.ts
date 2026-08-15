import api from "./api";

import type {
  BusinessDomain,
  BusinessDomainCreate,
  BusinessDomainUpdate,
  BusinessEntity,
  BusinessEntityCreate,
  BusinessEntitySuggestion,
  BusinessEntityUpdate,
  EntityTableMapping,
  EntityTableMappingCreate,
} from "../types/businessEntity";


export async function getBusinessDomains():
  Promise<BusinessDomain[]> {
  const response = await api.get<BusinessDomain[]>(
    "/api/business-entities/domains"
  );

  return response.data;
}


export async function createBusinessDomain(
  payload: BusinessDomainCreate
): Promise<BusinessDomain> {
  const response = await api.post<BusinessDomain>(
    "/api/business-entities/domains",
    payload
  );

  return response.data;
}


export async function updateBusinessDomain(
  domainId: number,
  payload: BusinessDomainUpdate
): Promise<BusinessDomain> {
  const response = await api.put<BusinessDomain>(
    `/api/business-entities/domains/${domainId}`,
    payload
  );

  return response.data;
}


export async function getBusinessEntities(
  domainId?: number
): Promise<BusinessEntity[]> {
  const response = await api.get<BusinessEntity[]>(
    "/api/business-entities",
    {
      params: {
        domain_id: domainId,
      },
    }
  );

  return response.data;
}


export async function createBusinessEntity(
  payload: BusinessEntityCreate
): Promise<BusinessEntity> {
  const response = await api.post<BusinessEntity>(
    "/api/business-entities",
    payload
  );

  return response.data;
}


export async function updateBusinessEntity(
  entityId: number,
  payload: BusinessEntityUpdate
): Promise<BusinessEntity> {
  const response = await api.put<BusinessEntity>(
    `/api/business-entities/${entityId}`,
    payload
  );

  return response.data;
}


export async function createEntityTableMapping(
  entityId: number,
  payload: EntityTableMappingCreate
): Promise<EntityTableMapping> {
  const response = await api.post<EntityTableMapping>(
    `/api/business-entities/${entityId}/table-mappings`,
    payload
  );

  return response.data;
}


export async function deleteEntityTableMapping(
  mappingId: number
): Promise<void> {
  await api.delete(
    `/api/business-entities/table-mappings/${mappingId}`
  );
}


export async function suggestEntityFromTable(
  tableId: number
): Promise<BusinessEntitySuggestion> {
  const response =
    await api.get<BusinessEntitySuggestion>(
      `/api/business-entities/suggestions/from-table/${tableId}`
    );

  return response.data;
}
