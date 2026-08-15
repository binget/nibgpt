import api from "./api";

import type {
  GeneratedTableDefinition,
  MetadataColumn,
  MetadataColumnUpdate,
  MetadataScanResponse,
  MetadataTableDetail,
  MetadataTableSummary,
  MetadataTableUpdate,
} from "../types/metadata";

export async function scanMetadata(
  dataSourceId: number
): Promise<MetadataScanResponse> {
  const response = await api.post<MetadataScanResponse>(
    `/api/metadata/data-sources/${dataSourceId}/scan`
  );

  return response.data;
}

export async function getMetadataTables(
  dataSourceId?: number,
  search?: string
): Promise<MetadataTableSummary[]> {
  const response = await api.get<MetadataTableSummary[]>(
    "/api/metadata/tables",
    {
      params: {
        data_source_id: dataSourceId,
        search: search?.trim() || undefined,
      },
    }
  );

  return response.data;
}

export async function getMetadataTable(
  tableId: number
): Promise<MetadataTableDetail> {
  const response = await api.get<MetadataTableDetail>(
    `/api/metadata/tables/${tableId}`
  );

  return response.data;
}

export async function updateMetadataTable(
  tableId: number,
  payload: MetadataTableUpdate
): Promise<MetadataTableDetail> {
  const response = await api.put<MetadataTableDetail>(
    `/api/metadata/tables/${tableId}`,
    payload
  );

  return response.data;
}

export async function updateMetadataColumn(
  columnId: number,
  payload: MetadataColumnUpdate
): Promise<MetadataColumn> {
  const response = await api.put<MetadataColumn>(
    `/api/metadata/columns/${columnId}`,
    payload
  );

  return response.data;
}

export async function generateTableDefinition(
  tableId: number
): Promise<GeneratedTableDefinition> {
  const response =
    await api.post<GeneratedTableDefinition>(
      `/api/metadata/tables/${tableId}/generate-definition`
    );

  return response.data;
}

export async function applyGeneratedDefinition(
  tableId: number
): Promise<MetadataTableDetail> {
  const response =
    await api.post<MetadataTableDetail>(
      `/api/metadata/tables/${tableId}/apply-generated-definition`
    );

  return response.data;
}

export async function approveGeneratedDefinition(
  tableId: number,
  approved: boolean
): Promise<MetadataTableDetail> {
  const response =
    await api.post<MetadataTableDetail>(
      `/api/metadata/tables/${tableId}/approve-definition`,
      {
        approved,
      }
    );

  return response.data;
}