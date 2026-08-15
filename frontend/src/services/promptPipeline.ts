import api from "./api";

import type {
  PromptPipelineResponse,
} from "../types/promptPipeline";

export async function analyzePromptPipeline(
  prompt: string,
  dataSourceId: number | null,
  maximumResults = 5
): Promise<PromptPipelineResponse> {
  const response =
    await api.post<PromptPipelineResponse>(
      "/api/prompt-pipeline/analyze",
      {
        prompt,
        data_source_id: dataSourceId,
        maximum_results: maximumResults,
      }
    );

  return response.data;
}
