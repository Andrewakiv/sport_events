import createClient from "openapi-fetch";

import type { paths } from "./schema";
import type {
  ChatAnswer,
  ChatMessage,
  Match,
  MatchFilters,
  MatchPage,
} from "./types";

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

export async function postChat(
  messages: ChatMessage[],
  signal?: AbortSignal,
): Promise<ChatAnswer> {
  let result;
  try {
    result = await api.POST("/api/v1/chat", { body: { messages }, signal });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError(
      "The assistant could not be reached. Check your connection.",
    );
  }

  const { data, response } = result;
  if (!data) {
    throw new ApiError(
      chatErrorMessage(response.status, response.headers.get("Retry-After")),
      response.status,
    );
  }
  return data;
}

function chatErrorMessage(status: number, retryAfter: string | null): string {
  if (status === 429) {
    const seconds = Number.parseInt(retryAfter ?? "", 10);
    return Number.isFinite(seconds) && seconds > 0
      ? `Too many questions. Try again in ${seconds} ${seconds === 1 ? "second" : "seconds"}.`
      : "Too many questions. Please wait a moment and try again.";
  }
  if (status === 503) return "The assistant is not available right now.";
  if (status === 422) {
    return "That message could not be sent. Keep it under 1000 characters.";
  }
  return "The assistant is temporarily unavailable. Try again in a moment.";
}

function apiMessage(error: unknown): string {
  if (typeof error === "object" && error !== null && "detail" in error) {
    const detail = error.detail;
    if (typeof detail === "string") return detail;
  }
  return "Unable to retrieve data from the API.";
}
