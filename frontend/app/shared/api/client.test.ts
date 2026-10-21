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
