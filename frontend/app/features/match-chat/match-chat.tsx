import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { ApiError, postChat } from "../../shared/api/client";
import type { ChatMessage } from "../../shared/api/types";
import { MAX_MESSAGE_LENGTH, requestWindow } from "./conversation";

const EXAMPLE_QUESTIONS = [
  "What are Barcelona's upcoming matches?",
  "Show the latest finished matches.",
  "Which matches are on today?",
];

export function MatchChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const log = useRef<HTMLDivElement>(null);

  useEffect(() => () => controller.current?.abort(), []);

  useEffect(() => {
    const element = log.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [messages, pending]);

  async function ask(question: string) {
    const text = question.trim();
    if (!text || text.length > MAX_MESSAGE_LENGTH || pending) return;

    const next: ChatMessage[] = [...messages, { role: "user", content: text }];
    const request = new AbortController();
    controller.current = request;
    setMessages(next);
    setDraft("");
    setError(null);
    setPending(true);

    try {
      const answer = await postChat(requestWindow(next), request.signal);
      setMessages([...next, { role: "assistant", content: answer.answer }]);
    } catch (failure) {
      if (request.signal.aborted) return;
      // Keep the history consistent: the unanswered question goes back to the input.
      setMessages(messages);
      setDraft(text);
      setError(
        failure instanceof ApiError
          ? failure.message
          : "Something went wrong. Try again in a moment.",
      );
    } finally {
      if (!request.signal.aborted) setPending(false);
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      void ask(draft);
    }
  }

  const canSend = !pending && draft.trim().length > 0;

  return (
    <section className="chat-panel" aria-labelledby="chat-heading">
      <div className="chat-heading">
        <p className="eyebrow">Assistant</p>
        <h2 id="chat-heading">Ask about Champions League matches</h2>
        <p className="chat-note">
          Answers use the imported match data, which can be a few hours old.
          Formula 1 and live scores are not covered. Your conversation is kept
          only on this page.
        </p>
      </div>

      <div
        className="chat-log"
        ref={log}
        role="log"
        aria-live="polite"
        aria-label="Conversation"
      >
        {messages.length === 0 && !pending ? (
          <div className="chat-empty">
            <p>Try one of these questions:</p>
            <div className="chat-examples">
              {EXAMPLE_QUESTIONS.map((question) => (
                <button
                  className="button button-secondary"
                  key={question}
                  type="button"
                  onClick={() => void ask(question)}
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        ) : null}
        {messages.map((message, index) => (
          <div
            className={`chat-message chat-message-${message.role}`}
            key={index}
          >
            <span className="chat-author">
              {message.role === "user" ? "You" : "Assistant"}
            </span>
            <p>{message.content}</p>
          </div>
        ))}
        {pending ? (
          <p className="chat-pending" role="status">
            Looking through the match data…
          </p>
        ) : null}
      </div>

      {error ? (
        <div className="chat-error" role="alert">
          {error}
        </div>
      ) : null}

      <form
        className="chat-form"
        onSubmit={(event) => {
          event.preventDefault();
          void ask(draft);
        }}
      >
        <label htmlFor="chat-input">Your question</label>
        <textarea
          id="chat-input"
          name="question"
          rows={3}
          maxLength={MAX_MESSAGE_LENGTH}
          value={draft}
          placeholder="Ask about fixtures, results or teams"
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onKeyDown}
        />
        <div className="chat-form-footer">
          <span className="chat-counter">
            {draft.length}/{MAX_MESSAGE_LENGTH} · Enter to send, Shift+Enter for
            a new line
          </span>
          <button
            className="button button-primary"
            type="submit"
            disabled={!canSend}
          >
            {pending ? "Sending…" : "Send"}
          </button>
        </div>
      </form>
    </section>
  );
}
