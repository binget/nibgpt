import api from "./api";

import type {
  ChatResponse,
  ConversationDetail,
  ConversationSummary,
} from "../types/chat";

export async function getConversations(): Promise<
  ConversationSummary[]
> {
  const response = await api.get<ConversationSummary[]>(
    "/api/chat/conversations"
  );

  return response.data;
}

export async function getConversation(
  conversationId: number
): Promise<ConversationDetail> {
  const response = await api.get<ConversationDetail>(
    `/api/chat/conversations/${conversationId}`
  );

  return response.data;
}

export async function sendChatMessage(
  prompt: string,
  conversationId: number | null
): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>(
    "/api/chat/message",
    {
      prompt,
      conversation_id: conversationId,
    }
  );

  return response.data;
}

export async function deleteConversation(
  conversationId: number
): Promise<void> {
  await api.delete(
    `/api/chat/conversations/${conversationId}`
  );
}
