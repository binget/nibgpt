import api from "./api";

import type {
  ReasoningPlan,
  ReasoningRequest,
} from "../types/reasoning";

export async function analyzeReasoning(
  payload: ReasoningRequest
): Promise<ReasoningPlan> {
  const response = await api.post<ReasoningPlan>(
    "/api/reasoning/analyze",
    payload
  );

  return response.data;
}
