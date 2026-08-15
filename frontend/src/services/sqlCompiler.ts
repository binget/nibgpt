import api from "./api";

import type {
  SqlCompilerRequest,
  SqlCompilerResult,
} from "../types/sqlCompiler";

export async function compileSemanticSql(
  payload: SqlCompilerRequest
): Promise<SqlCompilerResult> {
  const response = await api.post<SqlCompilerResult>(
    "/api/sql-compiler/compile",
    payload
  );

  return response.data;
}
