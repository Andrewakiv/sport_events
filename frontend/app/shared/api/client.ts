import createClient from "openapi-fetch";

import { demoMatches, findDemoMatch } from "./demo-data";
import type { paths } from "./schema";
import type { Match, MatchFilters, MatchPage, MatchResult } from "./types";

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

export async function getMatches(filters: MatchFilters): Promise<MatchResult> {
  if (filters.demo) {
    return { page: filterDemoMatches(filters), source: "demo" };
  }

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

  return { page: data, source: "api" };
}

export async function getMatch(
  matchId: number,
  demo: boolean,
): Promise<Match | null> {
  if (demo) return findDemoMatch(matchId);

  const { data, error, response } = await api.GET(
    "/api/v1/football/champions-league/matches/{match_id}",
    { params: { path: { match_id: matchId } } },
  );

  if (response.status === 404) return null;
  if (!data) throw new ApiError(apiMessage(error), response.status);
  return data;
}

function filterDemoMatches(filters: MatchFilters): MatchPage {
  const filtered = demoMatches.filter((match) => {
    const seasonYear = Number(match.season.start_date.slice(0, 4));
    const utcDate = match.kickoff_at.slice(0, 10);
    const hasTeam =
      match.home_team?.id === filters.teamId ||
      match.away_team?.id === filters.teamId;

    return (
      (filters.season === undefined || seasonYear === filters.season) &&
      (filters.date === undefined || utcDate === filters.date) &&
      (filters.teamId === undefined || hasTeam) &&
      (filters.status === undefined || match.status === filters.status)
    );
  });

  return {
    items: filtered.slice(filters.offset, filters.offset + filters.limit),
    total: filtered.length,
    limit: filters.limit,
    offset: filters.offset,
  };
}

function apiMessage(error: unknown): string {
  if (typeof error === "object" && error !== null && "detail" in error) {
    const detail = error.detail;
    if (typeof detail === "string") return detail;
  }
  return "Не вдалося отримати дані з API.";
}
