import api from "./api";


export interface ReportingContext {
  measure?: string | null;
  dimension?: string | null;
  status?: string | null;
  ranking?: string | null;
  limit?: number | null;
  previous_prompt?: string | null;
}


export interface OrchestratorRequest {
  prompt: string;
  requested_limit?: number;
  maximum_entities?: number;
  maximum_path_depth?: number;
  user_role?: string;
  previous_prompt?: string | null;
  context?: ReportingContext | null;
  conversation_id?: number | null;
}


export interface OrchestratorReport {
  success: boolean;
  prompt: string;
  decision: string;

  data_source_id?: number;
  data_source_name?: string;

  sql?: string;
  answer?: string;

  parameters?: Record<
    string,
    unknown
  >;

  columns: string[];

  rows: Record<
    string,
    any
  >[];

  row_count: number;

  execution_time_ms?: number;

  warnings: string[];
  errors: string[];
  explanation: string[];
}


export interface WebSource {
  title: string;
  url: string;
  trust_level?: string;
}


export interface OrchestratorResponse {
  route:
    | "reporting"
    | "knowledge"
    | "general"
    | "web"
    | "competitor";

  confidence: number;
  reason: string;

  success: boolean;

  answer?: string | null;

  report?: OrchestratorReport | null;

  context?: ReportingContext | null;

  warnings: string[];

  sources?: WebSource[];

  retrieved_at?: string | null;
}


export interface StreamCallbacks {
  onStart?: () => void;

  onToken:
    (token: string) => void;

  onDone?: () => void;

  onError?:
    (message: string) => void;
}


export async function askNIBGPT(
  payload: OrchestratorRequest
): Promise<OrchestratorResponse> {

  const response =
    await api.post<OrchestratorResponse>(
      "/api/orchestrator/ask",
      payload
    );

  return response.data;
}


export async function streamNIBGPT(
  prompt: string,
  conversationId: number | null,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
  mode: "general" | "document" = "general"
): Promise<void> {

  const response = await fetch(
    "http://172.24.0.13:8000/api/orchestrator/stream",
    {
      method: "POST",

      headers: {
      "Content-Type":
        "application/json",

      ...(localStorage.getItem(
        "nibgpt_access_token"
      )
        ? {
            Authorization:
              `Bearer ${localStorage.getItem(
                "nibgpt_access_token"
              )}`,
          }
        : {}),
    },

      body: JSON.stringify({
      prompt,

      conversation_id:
        conversationId,

      mode,
    }),

      signal,
    }
  );

  if (!response.ok) {
    throw new Error(
      `Streaming request failed: ${response.status}`
    );
  }

  if (!response.body) {
    throw new Error(
      "Streaming response body is unavailable."
    );
  }

  const reader =
    response.body.getReader();

  const decoder =
    new TextDecoder(
      "utf-8"
    );

  let buffer = "";

  try {

    while (true) {

      const {
        value,
        done,
      } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(
        value,
        {
          stream: true,
        }
      );

      const events =
        buffer.split(
          "\n\n"
        );

      buffer =
        events.pop() ?? "";

      for (
        const event
        of events
      ) {

        const line = event
          .split("\n")
          .find(
            (item) =>
              item.startsWith(
                "data:"
              )
          );

        if (!line) {
          continue;
        }

        const rawData =
          line
            .slice(5)
            .trim();

        if (!rawData) {
          continue;
        }

        const data =
          JSON.parse(
            rawData
          );

        if (
          data.type ===
          "start"
        ) {
          callbacks
            .onStart?.();

          continue;
        }

        if (
          data.type ===
          "token"
        ) {
          callbacks.onToken(
            data.content ?? ""
          );

          continue;
        }

        if (
          data.type ===
          "done"
        ) {
          callbacks
            .onDone?.();

          continue;
        }

        if (
          data.type ===
          "error"
        ) {
          callbacks.onError?.(
            data.message ??
              (
                "NIBGPT streaming " +
                "failed."
              )
          );
        }
      }
    }

  } finally {

    reader.releaseLock();

  }
}


export async function streamReportExplanation(
  report: OrchestratorReport,
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {

  const response = await fetch(
    (
      "http://172.24.0.13:8000/" +
      "api/orchestrator/" +
      "report-explanation/stream"
    ),
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        report,
      }),

      signal,
    }
  );

  if (!response.ok) {
    throw new Error(
      (
        "Report explanation " +
        `failed: ${response.status}`
      )
    );
  }

  if (!response.body) {
    throw new Error(
      (
        "Report explanation stream " +
        "is unavailable."
      )
    );
  }

  const reader =
    response.body.getReader();

  const decoder =
    new TextDecoder(
      "utf-8"
    );

  let buffer = "";

  try {

    while (true) {

      const {
        value,
        done,
      } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(
        value,
        {
          stream: true,
        }
      );

      const events =
        buffer.split(
          "\n\n"
        );

      buffer =
        events.pop() ?? "";

      for (
        const event
        of events
      ) {

        const line = event
          .split("\n")
          .find(
            (item) =>
              item.startsWith(
                "data:"
              )
          );

        if (!line) {
          continue;
        }

        const rawData =
          line
            .slice(5)
            .trim();

        if (!rawData) {
          continue;
        }

        const data =
          JSON.parse(
            rawData
          );

        if (
          data.type ===
          "start"
        ) {
          callbacks
            .onStart?.();

          continue;
        }

        if (
          data.type ===
          "token"
        ) {
          callbacks.onToken(
            data.content ?? ""
          );

          continue;
        }

        if (
          data.type ===
          "done"
        ) {
          callbacks
            .onDone?.();

          continue;
        }

        if (
          data.type ===
          "error"
        ) {
          callbacks.onError?.(
            data.message ??
              (
                "Unable to explain " +
                "the report."
              )
          );
        }
      }
    }

  } finally {

    reader.releaseLock();

  }
}