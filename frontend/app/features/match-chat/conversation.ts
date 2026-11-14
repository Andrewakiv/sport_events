import type { ChatMessage } from "../../shared/api/types";

export const MAX_MESSAGE_LENGTH = 1000;
export const MAX_HISTORY_MESSAGES = 20;

/**
 * The API accepts at most 20 messages and the model needs the conversation to
 * start with a user message, so drop leading assistant replies after trimming.
 */
export function requestWindow(messages: ChatMessage[]): ChatMessage[] {
  const recent = messages.slice(-MAX_HISTORY_MESSAGES);
  const firstUser = recent.findIndex((message) => message.role === "user");
  return firstUser === -1 ? [] : recent.slice(firstUser);
}
