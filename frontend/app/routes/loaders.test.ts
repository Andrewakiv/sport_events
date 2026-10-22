import { beforeEach, describe, expect, it, vi } from "vitest";

import type * as ApiClient from "../shared/api/client";
import { ApiError, getMatch, getMatches } from "../shared/api/client";
import { clientLoader as detailLoader } from "./champions-league-match";
import { clientLoader as listLoader } from "./champions-league-matches";

vi.mock("../shared/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof ApiClient>()),
  getMatches: vi.fn(),
  getMatch: vi.fn(),
}));

const BASE = "http://localhost/football/champions-league/matches";

function listArgs(search = "") {
  return { request: new Request(`${BASE}${search}`) } as Parameters<
    typeof listLoader
  >[0];
}

function detailArgs(matchId: string, search = "") {
  return {
    params: { matchId },
    request: new Request(`${BASE}/${matchId}${search}`),
  } as unknown as Parameters<typeof detailLoader>[0];
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("matches list loader", () => {
  it("passes parsed URL filters to the API", async () => {
    const page = { items: [], total: 0, limit: 25, offset: 0 };
    vi.mocked(getMatches).mockResolvedValue(page);

    const result = await listLoader(listArgs("?season=2025&status=FINISHED"));

    expect(getMatches).toHaveBeenCalledWith(
      expect.objectContaining({ season: 2025, status: "FINISHED", limit: 25 }),
    );
    expect(result).toMatchObject({ ok: true, result: page });
  });

  it("returns the API error status and message", async () => {
    vi.mocked(getMatches).mockRejectedValue(new ApiError("Boom", 500));

    expect(await listLoader(listArgs())).toMatchObject({
      ok: false,
      message: "Boom",
      status: 500,
    });
  });

  it("reports an unreachable API for unexpected failures", async () => {
    vi.mocked(getMatches).mockRejectedValue(new TypeError("network"));

    expect(await listLoader(listArgs())).toMatchObject({
      ok: false,
      message: "The API is currently unavailable.",
    });
  });
});

describe("match detail loader", () => {
  it.each(["abc", "0", "-3", "1.5"])(
    "treats %s as not found without calling the API",
    async (matchId) => {
      expect(await detailLoader(detailArgs(matchId))).toMatchObject({
        ok: true,
        match: null,
      });
      expect(getMatch).not.toHaveBeenCalled();
    },
  );

  it("returns null for a missing match and keeps a safe returnTo", async () => {
    vi.mocked(getMatch).mockResolvedValue(null);
    const returnTo = "/football/champions-league/matches?season=2026";

    expect(
      await detailLoader(
        detailArgs("7", `?returnTo=${encodeURIComponent(returnTo)}`),
      ),
    ).toEqual({ ok: true, match: null, returnTo });
  });

  it("returns an error state when the API fails", async () => {
    vi.mocked(getMatch).mockRejectedValue(new ApiError("Down", 503));

    expect(await detailLoader(detailArgs("7"))).toMatchObject({
      ok: false,
      message: "Down",
      status: 503,
    });
  });
});
