import api from "./api";

import type {
  QueryExecutionRequest,
  QueryExecutionResponse,
} from "../types/queryExecutor";


export async function executeNIBGPTQuery(
  payload: QueryExecutionRequest
): Promise<QueryExecutionResponse> {
  const response =
    await api.post<QueryExecutionResponse>(
      "/api/query-executor/execute",
      payload
    );

  return response.data;
}