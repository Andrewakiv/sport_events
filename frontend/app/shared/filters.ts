import type { MatchFilters } from "./api/types";

const DEFAULT_LIMIT = 25;
const MAX_LIMIT = 100;

export function parseFilters(url: URL): MatchFilters {
  return {
    season: optionalInteger(url.searchParams.get("season"), 1900, 2100),
    date: validDate(url.searchParams.get("date")),
    teamId: optionalInteger(url.searchParams.get("team_id"), 1, 2_147_483_647),
    status: nonEmpty(url.searchParams.get("status")),
    limit:
      optionalInteger(url.searchParams.get("limit"), 1, MAX_LIMIT) ??
      DEFAULT_LIMIT,
    offset: optionalInteger(url.searchParams.get("offset"), 0) ?? 0,
    demo: url.searchParams.get("demo") === "1",
  };
}

export function pageSearchParams(
  current: URLSearchParams,
  offset: number,
): URLSearchParams {
  const next = new URLSearchParams(current);
  if (offset > 0) next.set("offset", String(offset));
  else next.delete("offset");
  return next;
}

function optionalInteger(
  value: string | null,
  minimum: number,
  maximum = Number.MAX_SAFE_INTEGER,
): number | undefined {
  if (value === null || value.trim() === "") return undefined;
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < minimum || parsed > maximum)
    return undefined;
  return parsed;
}

function validDate(value: string | null): string | undefined {
  if (value === null || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return undefined;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ||
    date.toISOString().slice(0, 10) !== value
    ? undefined
    : value;
}

function nonEmpty(value: string | null): string | undefined {
  const trimmed = value?.trim();
  return trimmed ? trimmed : undefined;
}
