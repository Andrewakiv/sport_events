import { describe, expect, it } from "vitest";

import { lastPageOffset, pageSearchParams, parseFilters } from "./filters";

describe("parseFilters", () => {
  it("reads valid API filters from the URL", () => {
    const filters = parseFilters(
      new URL(
        "https://example.test/matches?season=2026&date=2026-10-07&team_id=64&status=FINISHED&limit=10&offset=20",
      ),
    );

    expect(filters).toEqual({
      season: 2026,
      date: "2026-10-07",
      teamId: 64,
      status: "FINISHED",
      limit: 10,
      offset: 20,
    });
  });

  it("falls back safely for malformed values", () => {
    const filters = parseFilters(
      new URL(
        "https://example.test/matches?season=nope&date=2026-02-31&limit=999&offset=-2",
      ),
    );

    expect(filters).toEqual({
      season: undefined,
      date: undefined,
      teamId: undefined,
      status: undefined,
      limit: 25,
      offset: 0,
    });
  });
});

describe("pageSearchParams", () => {
  it("preserves filters and sets the requested offset", () => {
    const params = new URLSearchParams("season=2026&status=FINISHED");
    expect(pageSearchParams(params, 25).toString()).toBe(
      "season=2026&status=FINISHED&offset=25",
    );
    expect(params.has("offset")).toBe(false);
  });

  it("removes offset for the first page", () => {
    const params = new URLSearchParams("season=2026&offset=25");
    expect(pageSearchParams(params, 0).toString()).toBe("season=2026");
  });
});

describe("lastPageOffset", () => {
  it.each([
    [0, 25, 0],
    [1, 25, 0],
    [25, 25, 0],
    [26, 25, 25],
    [51, 25, 50],
  ])(
    "total %i with limit %i starts the last page at %i",
    (total, limit, expected) => {
      expect(lastPageOffset(total, limit)).toBe(expected);
    },
  );
});
