// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { parseFilters } from "../filters";

const NativeRequest = globalThis.Request;
const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.resetModules();
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  // Browsers resolve relative Request URLs against the page; Node needs an origin.
  vi.stubGlobal(
    "Request",
    class extends NativeRequest {
      constructor(input: RequestInfo | URL, init?: RequestInit) {
        super(
          typeof input === "string"
            ? new URL(input, "http://localhost")
            : input,
          init,
        );
      }
    },
  );
});

afterEach(() => vi.unstubAllGlobals());

describe("backend-only match client", () => {
  it("requests API filters and preserves an empty database response", async () => {
    const page = { items: [], total: 0, limit: 10, offset: 20 };
    fetchMock.mockResolvedValue(Response.json(page));
    const { getMatches } = await import("./client");

    const result = await getMatches(
      parseFilters(
        new URL(
          "http://localhost/matches?season=2026&status=FINISHED&limit=10&offset=20&demo=1",
        ),
      ),
    );

    expect(result).toEqual(page);
    expect(fetchMock).toHaveBeenCalledOnce();
    const request = fetchMock.mock.calls[0]?.[0];
    if (!(request instanceof NativeRequest))
      throw new Error("Expected an API request");
    const url = new URL(request.url);
    expect(url.pathname).toBe("/api/v1/football/champions-league/matches");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      season: "2026",
      status: "FINISHED",
      limit: "10",
      offset: "20",
    });
  });

  it("surfaces API errors instead of substituting sample matches", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ detail: "Database unavailable" }, { status: 503 }),
    );
    const { getMatches } = await import("./client");
    await expect(
      getMatches(parseFilters(new URL("http://localhost/matches"))),
    ).rejects.toMatchObject({
      name: "ApiError",
      status: 503,
      message: "Database unavailable",
    });
  });

  it("propagates network failure instead of returning sample matches", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    const { getMatches } = await import("./client");
    await expect(
      getMatches(parseFilters(new URL("http://localhost/matches"))),
    ).rejects.toThrow("Failed to fetch");
  });

  it("returns not found for a missing backend match", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ detail: "Not found" }, { status: 404 }),
    );
    const { getMatch } = await import("./client");
    await expect(getMatch(42)).resolves.toBeNull();
    const request = fetchMock.mock.calls[0]?.[0];
    expect(request).toMatchObject({
      url: "http://localhost/api/v1/football/champions-league/matches/42",
    });
  });
});

describe("chat client", () => {
  const messages = [{ role: "user" as const, content: "Next match?" }];

  it("posts the conversation and returns the answer", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ answer: "On Tuesday.", outcome: "answered" }),
    );
    const { postChat } = await import("./client");

    await expect(postChat(messages)).resolves.toEqual({
      answer: "On Tuesday.",
      outcome: "answered",
    });

    const request = fetchMock.mock.calls[0]?.[0];
    if (!(request instanceof NativeRequest))
      throw new Error("Expected an API request");
    expect(request.method).toBe("POST");
    expect(new URL(request.url).pathname).toBe("/api/v1/chat");
    expect(await request.json()).toEqual({ messages });
  });

  it.each([
    [
      429,
      { "Retry-After": "12" },
      "Too many questions. Try again in 12 seconds.",
    ],
    [429, {}, "Too many questions. Please wait a moment and try again."],
    [503, {}, "The assistant is not available right now."],
    [422, {}, "That message could not be sent. Keep it under 1000 characters."],
    [
      502,
      {},
      "The assistant is temporarily unavailable. Try again in a moment.",
    ],
  ])("maps HTTP %i to a friendly message", async (status, headers, message) => {
    fetchMock.mockResolvedValue(
      Response.json({ detail: "provider detail" }, { status, headers }),
    );
    const { postChat } = await import("./client");

    await expect(postChat(messages)).rejects.toMatchObject({
      name: "ApiError",
      status,
      message,
    });
  });

  it("reports an unreachable service without leaking the cause", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    const { postChat } = await import("./client");

    await expect(postChat(messages)).rejects.toMatchObject({
      name: "ApiError",
      message: "The assistant could not be reached. Check your connection.",
    });
  });

  it("rethrows an aborted request unchanged", async () => {
    const controller = new AbortController();
    controller.abort();
    fetchMock.mockRejectedValue(new DOMException("Aborted", "AbortError"));
    const { postChat } = await import("./client");

    await expect(postChat(messages, controller.signal)).rejects.toMatchObject({
      name: "AbortError",
    });
  });
});
