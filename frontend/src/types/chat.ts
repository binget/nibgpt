import type {
  ReportingContext,
} from "../services/orchestrator";

export interface ChatMessage {
  id: number;
  conversation_id: number;
  role: "user" | "assistant";
  content: string;
  source_type: string | null;
  report_payload?: Record<
    string,
    any
  > | null;
  created_at: string;
}

export interface ConversationSummary {
  id: number;
  title: string;

  reporting_context?:
    ReportingContext | null;

  created_at: string;
  updated_at: string;
}

export interface ConversationDetail {
  id: number;
  title: string;

  reporting_context?:
    ReportingContext | null;

  created_at: string;
  updated_at: string;

  messages: ChatMessage[];
}

export interface ChatResponse {
  conversation_id: number;
  message: ChatMessage;
}
