import createClient from "openapi-fetch";

import type { paths } from "./schema";
import type { Match, MatchFilters, MatchPage } from "./types";

const api = createClient<paths>({ baseUrl: "/" });

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function getMatches(filters: MatchFilters): Promise<MatchPage> {
  const { data, error, response } = await api.GET(
    "/api/v1/football/champions-league/matches",
    {
      params: {
        query: {
          season: filters.season,
          date: filters.date,
          team_id: filters.teamId,
          status: filters.status,
          limit: filters.limit,
          offset: filters.offset,
        },
      },
    },
  );

  if (!data) {
    throw new ApiError(apiMessage(error), response.status);
  }

  return data;
}

export async function getMatch(matchId: number): Promise<Match | null> {
  const { data, error, response } = await api.GET(
    "/api/v1/football/champions-league/matches/{match_id}",
    { params: { path: { match_id: matchId } } },
  );

  if (response.status === 404) return null;
  if (!data) throw new ApiError(apiMessage(error), response.status);
  return data;
}

function apiMessage(error: unknown): string {
  if (typeof error === "object" && error !== null && "detail" in error) {
    const detail = error.detail;
    if (typeof detail === "string") return detail;
  }
  return "Не вдалося отримати дані з API.";
}
