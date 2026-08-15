import api from "./api";

import type {
  ExecutiveDashboard,
} from "../types/executiveDashboard";

export async function getExecutiveDashboard():
  Promise<ExecutiveDashboard> {
  const response =
    await api.get<ExecutiveDashboard>(
      "/api/executive-dashboard"
    );

  return response.data;
}
