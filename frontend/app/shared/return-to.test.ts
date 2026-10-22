import { describe, expect, it } from "vitest";

import { safeReturnTo } from "./return-to";

const FALLBACK = "/football/champions-league/matches";

describe("safeReturnTo", () => {
  it("keeps the matches list path and its query", () => {
    expect(safeReturnTo(`${FALLBACK}?season=2026&offset=25`)).toBe(
      `${FALLBACK}?season=2026&offset=25`,
    );
  });

  it.each([null, "", "https://evil.example/", "//evil.example/", "/other"])(
    "falls back for %s",
    (value) => {
      expect(safeReturnTo(value)).toBe(FALLBACK);
    },
  );

  it("rejects paths that merely share the list prefix", () => {
    expect(safeReturnTo(`${FALLBACK}/42`)).toBe(FALLBACK);
    expect(safeReturnTo(`${FALLBACK}evil`)).toBe(FALLBACK);
  });
});
