// @vitest-environment node
import { describe, expect, it } from "vitest";

import type { ChatMessage } from "../../shared/api/types";
import { requestWindow } from "./conversation";

function conversation(count: number): ChatMessage[] {
  return Array.from({ length: count }, (_, index) => ({
    role: index % 2 === 0 ? "user" : "assistant",
    content: `message ${index}`,
  }));
}

describe("requestWindow", () => {
  it("keeps a short conversation unchanged", () => {
    const messages = conversation(3);
    expect(requestWindow(messages)).toEqual(messages);
  });

  it("keeps the last 20 messages when they start with a user message", () => {
    const messages = conversation(23);
    const window = requestWindow(messages);
    expect(window).toHaveLength(19);
    expect(window[0]).toEqual({ role: "user", content: "message 4" });
    expect(window.at(-1)).toEqual(messages.at(-1));
  });

  it("drops a leading assistant reply left by trimming", () => {
    const messages = conversation(22);
    const window = requestWindow(messages);
    expect(window[0]?.role).toBe("user");
    expect(window).toHaveLength(20);
    expect(window[0]).toEqual({ role: "user", content: "message 2" });
  });

  it("returns nothing when there is no user message", () => {
    expect(requestWindow([{ role: "assistant", content: "hi" }])).toEqual([]);
  });
});
