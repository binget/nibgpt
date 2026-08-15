import api from "./api";

import type {
  ConnectionTestResponse,
  DataSource,
  DataSourceCreate,
} from "../types/dataSource";

export async function getDataSources(): Promise<DataSource[]> {
  const response = await api.get<DataSource[]>("/api/data-sources");
  return response.data;
}

export async function createDataSource(
  payload: DataSourceCreate
): Promise<DataSource> {
  const response = await api.post<DataSource>(
    "/api/data-sources",
    payload
  );

  return response.data;
}

export async function testDataSource(
  sourceId: number
): Promise<ConnectionTestResponse> {
  const response = await api.post<ConnectionTestResponse>(
    `/api/data-sources/${sourceId}/test`
  );

  return response.data;
}

export async function deleteDataSource(
  sourceId: number
): Promise<void> {
  await api.delete(`/api/data-sources/${sourceId}`);
}
