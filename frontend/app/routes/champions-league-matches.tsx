import { Link, useNavigation } from "react-router";

import type { Route } from "./+types/champions-league-matches";
import { MatchCard } from "../entities/match/match-card";
import { MatchFiltersPanel } from "../features/match-filters/match-filters";
import { MatchPagination } from "../features/match-pagination/match-pagination";
import { PageOutOfRange } from "../features/match-pagination/page-out-of-range";
import { ApiError, getMatches } from "../shared/api/client";
import type { Match, MatchPage } from "../shared/api/types";
import { parseFilters } from "../shared/filters";
import { formatMatchDate, localDateKey } from "../shared/format";

export function meta() {
  return [
    { title: "Champions League — Sport Events" },
    {
      name: "description",
      content: "UEFA Champions League fixtures and results.",
    },
  ];
}

type LoaderData =
  | { ok: true; result: MatchPage; filters: ReturnType<typeof parseFilters> }
  | {
      ok: false;
      message: string;
      status?: number;
      filters: ReturnType<typeof parseFilters>;
    };

export async function clientLoader({
  request,
}: Route.ClientLoaderArgs): Promise<LoaderData> {
  const filters = parseFilters(new URL(request.url));
  try {
    return { ok: true, result: await getMatches(filters), filters };
  } catch (error) {
    if (error instanceof ApiError) {
      return {
        ok: false,
        message: error.message,
        status: error.status,
        filters,
      };
    }
    return { ok: false, message: "The API is currently unavailable.", filters };
  }
}

export default function ChampionsLeagueMatches({
  loaderData,
}: Route.ComponentProps) {
  const pending = useNavigation().state === "loading";

  return (
    <main>
      <section className="competition-hero">
        <div className="hero-copy">
          <p className="eyebrow">UEFA Champions League</p>
          <h1>
            Champions <span>League</span>
          </h1>
          <p className="hero-summary">
            Upcoming fixtures and results from completed matches.
          </p>
        </div>
        <div className="competition-emblem" aria-hidden="true">
          <div>★</div>
          <span>UCL</span>
        </div>
      </section>

      <div className="content-grid">
        <MatchFiltersPanel filters={loaderData.filters} />

        <section
          className={pending ? "matches-panel is-pending" : "matches-panel"}
          aria-labelledby="matches-heading"
          aria-busy={pending}
        >
          <div className="matches-toolbar">
            <div>
              <p className="eyebrow">Match centre</p>
              <h2 id="matches-heading">Fixtures and results</h2>
            </div>
          </div>

          {!loaderData.ok ? (
            <ApiUnavailable
              message={loaderData.message}
              status={loaderData.status}
            />
          ) : loaderData.result.items.length === 0 ? (
            loaderData.result.total > 0 ? (
              <PageOutOfRange
                limit={loaderData.result.limit}
                total={loaderData.result.total}
              />
            ) : (
              <EmptyState />
            )
          ) : (
            <>
              <MatchGroups matches={loaderData.result.items} />
              <MatchPagination
                limit={loaderData.result.limit}
                offset={loaderData.result.offset}
                total={loaderData.result.total}
              />
            </>
          )}
        </section>
      </div>
    </main>
  );
}

function MatchGroups({ matches }: { matches: Match[] }) {
  const groups = matches.reduce<Map<string, Match[]>>((result, match) => {
    const date = localDateKey(match.kickoff_at);
    const existing = result.get(date) ?? [];
    existing.push(match);
    result.set(date, existing);
    return result;
  }, new Map());

  return (
    <div className="match-groups">
      {[...groups.entries()].map(([date, dayMatches]) => {
        const firstMatch = dayMatches[0];
        if (!firstMatch) return null;
        return (
          <section className="match-day" key={date}>
            <div className="day-heading">
              <h3>{formatMatchDate(firstMatch.kickoff_at)}</h3>
              <span>{matchCount(dayMatches.length)}</span>
            </div>
            <div className="match-list">
              {dayMatches.map((match) => (
                <MatchCard key={match.id} match={match} />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function matchCount(count: number): string {
  return `${count} ${count === 1 ? "match" : "matches"}`;
}

function ApiUnavailable({
  message,
  status,
}: {
  message: string;
  status?: number;
}) {
  return (
    <div className="state-card error-state" role="alert">
      <span className="state-icon" aria-hidden="true">
        !
      </span>
      <p className="eyebrow">API {status ? `· ${status}` : "unavailable"}</p>
      <h3>Unable to load matches</h3>
      <p>{message} Please try refreshing the page later.</p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="state-card">
      <span className="state-icon" aria-hidden="true">
        0
      </span>
      <p className="eyebrow">No results</p>
      <h3>No matches found</h3>
      <p>Reset the filters or choose a different season, date or status.</p>
      <Link className="button button-secondary" to="?">
        Reset filters
      </Link>
    </div>
  );
}
