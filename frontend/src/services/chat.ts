import api from "./api";

import type {
  ChatMessage,
  ChatResponse,
  ConversationDetail,
  ConversationSummary,
} from "../types/chat";


export async function getConversations():
Promise<ConversationSummary[]> {
  const response =
    await api.get<
      ConversationSummary[]
    >(
      "/api/chat/conversations"
    );

  return response.data;
}


export async function getConversation(
  conversationId: number
): Promise<ConversationDetail> {
  const response =
    await api.get<
      ConversationDetail
    >(
      `/api/chat/conversations/${conversationId}`
    );

  return response.data;
}


export async function createConversation(
  firstPrompt: string
): Promise<ConversationSummary> {
  const response =
    await api.post<
      ConversationSummary
    >(
      "/api/chat/conversations",
      {
        first_prompt:
          firstPrompt,
      }
    );

  return response.data;
}


export async function saveConversationMessage(
  conversationId: number,
  role: "user" | "assistant",
  content: string,
  sourceType?: string | null,
  reportPayload?: Record<
    string,
    any
  > | null
): Promise<ChatMessage> {
  const response =
    await api.post<
      ChatMessage
    >(
      `/api/chat/conversations/${conversationId}/messages`,
      {
        role,
        content,
        source_type:
          sourceType ?? null,
        report_payload:
    reportPayload ?? null,
      }
    );

  return response.data;
}


/*
 * Backward compatibility for the old ChatPage.tsx.
 *
 * The old page expects:
 *
 * sendChatMessage(prompt, conversationId)
 *
 * Keep it for now so the legacy AI Chat page
 * does not break.
 */
export async function sendChatMessage(
  prompt: string,
  conversationId: number | null
): Promise<ChatResponse> {
  let currentConversationId =
    conversationId;

  if (
    currentConversationId ===
    null
  ) {
    const conversation =
      await createConversation(
        prompt
      );

    currentConversationId =
      conversation.id;
  }

  const userMessage =
    await saveConversationMessage(
      currentConversationId,
      "user",
      prompt,
      "user"
    );

  /*
   * Legacy compatibility only.
   *
   * The new NIBGPTPage does NOT use this
   * function for AI generation.
   */
  return {
    conversation_id:
      currentConversationId,
    message:
      userMessage,
  };
}


export async function deleteConversation(
  conversationId: number
): Promise<void> {
  await api.delete(
    `/api/chat/conversations/${conversationId}`
  );
}

export async function renameConversation(
  conversationId: number,
  title: string
): Promise<ConversationSummary> {
  const response =
    await api.patch<ConversationSummary>(
      `/api/chat/conversations/${conversationId}`,
      {
        title,
      }
    );

  return response.data;
}