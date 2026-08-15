import api from "./api";

import type {
  PromptAnalysisResponse,
} from "../types/intelligence";

export async function analyzePrompt(
  prompt: string,
  dataSourceId: number | null
): Promise<PromptAnalysisResponse> {
  const response =
    await api.post<PromptAnalysisResponse>(
      "/api/intelligence/analyze",
      {
        prompt,
        data_source_id: dataSourceId,
        maximum_results: 5,
      }
    );

  return response.data;
}
