import type { components } from "./schema";

export type Match = components["schemas"]["Match"];
export type MatchPage = components["schemas"]["MatchPage"];

export interface MatchFilters {
  season?: number;
  date?: string;
  teamId?: number;
  status?: string;
  limit: number;
  offset: number;
}
