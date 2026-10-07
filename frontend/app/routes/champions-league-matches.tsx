import { Link, useSearchParams } from "react-router";

import type { Route } from "./+types/champions-league-matches";
import { MatchCard } from "../entities/match/match-card";
import { MatchFiltersPanel } from "../features/match-filters/match-filters";
import { MatchPagination } from "../features/match-pagination/match-pagination";
import { ApiError, getMatches } from "../shared/api/client";
import type { Match, MatchResult } from "../shared/api/types";
import { parseFilters } from "../shared/filters";
import { formatMatchDate, utcDateKey } from "../shared/format";

export function meta() {
  return [
    { title: "Ліга чемпіонів — Sport Events" },
    {
      name: "description",
      content: "Розклад і результати матчів UEFA Champions League.",
    },
  ];
}

type LoaderData =
  | { ok: true; result: MatchResult; filters: ReturnType<typeof parseFilters> }
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
    return { ok: false, message: "API зараз недоступний.", filters };
  }
}

export default function ChampionsLeagueMatches({
  loaderData,
}: Route.ComponentProps) {
  const [, setSearchParams] = useSearchParams();

  return (
    <main>
      <section className="competition-hero">
        <div className="hero-copy">
          <p className="eyebrow">UEFA · сезон 2026/27</p>
          <h1>
            Champions <span>League</span>
          </h1>
          <p className="hero-summary">
            Один екран для майбутніх матчів і фінальних рахунків. Дані читаються
            з локального Sport Events API.
          </p>
        </div>
        <div className="competition-emblem" aria-hidden="true">
          <div>★</div>
          <span>UCL</span>
        </div>
      </section>

      <div className="content-grid">
        <MatchFiltersPanel filters={loaderData.filters} />

        <section className="matches-panel" aria-labelledby="matches-heading">
          <div className="matches-toolbar">
            <div>
              <p className="eyebrow">Матч-центр</p>
              <h2 id="matches-heading">Розклад і результати</h2>
            </div>
            {loaderData.ok && (
              <span
                className={`source-badge source-${loaderData.result.source}`}
              >
                {loaderData.result.source === "demo" ? "Demo data" : "Live API"}
              </span>
            )}
          </div>

          {!loaderData.ok ? (
            <ApiUnavailable
              message={loaderData.message}
              status={loaderData.status}
            />
          ) : loaderData.result.page.items.length === 0 ? (
            <EmptyState demo={loaderData.filters.demo} />
          ) : (
            <>
              <MatchGroups
                matches={loaderData.result.page.items}
                demo={loaderData.result.source === "demo"}
              />
              <MatchPagination
                limit={loaderData.result.page.limit}
                offset={loaderData.result.page.offset}
                total={loaderData.result.page.total}
              />
            </>
          )}
        </section>
      </div>

      {loaderData.filters.demo && (
        <button
          className="demo-exit"
          type="button"
          onClick={() =>
            setSearchParams((current) => {
              const next = new URLSearchParams(current);
              next.delete("demo");
              return next;
            })
          }
        >
          Вийти з demo
        </button>
      )}
    </main>
  );
}

function MatchGroups({ matches, demo }: { matches: Match[]; demo: boolean }) {
  const groups = matches.reduce<Map<string, Match[]>>((result, match) => {
    const date = utcDateKey(match);
    const existing = result.get(date) ?? [];
    existing.push(match);
    result.set(date, existing);
    return result;
  }, new Map());

  return (
    <div className="match-groups">
      {[...groups.entries()].map(([date, dayMatches]) => (
        <section className="match-day" key={date}>
          <div className="day-heading">
            <h3>{formatMatchDate(`${date}T12:00:00Z`)}</h3>
            <span>{matchCount(dayMatches.length)}</span>
          </div>
          <div className="match-list">
            {dayMatches.map((match) => (
              <MatchCard key={match.id} match={match} demo={demo} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function matchCount(count: number): string {
  const remainder100 = count % 100;
  const remainder10 = count % 10;
  const noun =
    remainder10 === 1 && remainder100 !== 11
      ? "матч"
      : remainder10 >= 2 &&
          remainder10 <= 4 &&
          (remainder100 < 12 || remainder100 > 14)
        ? "матчі"
        : "матчів";
  return `${count} ${noun}`;
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
      <p className="eyebrow">API {status ? `· ${status}` : "недоступний"}</p>
      <h3>Не вдалося завантажити матчі</h3>
      <p>
        {message} Запустіть FastAPI або відкрийте підготовлений режим перегляду.
      </p>
      <Link className="button button-primary" to="?demo=1">
        Переглянути demo
      </Link>
    </div>
  );
}

function EmptyState({ demo }: { demo: boolean }) {
  return (
    <div className="state-card">
      <span className="state-icon" aria-hidden="true">
        0
      </span>
      <p className="eyebrow">Порожня вибірка</p>
      <h3>Матчів за цими умовами немає</h3>
      <p>Скиньте фільтри або оберіть інший сезон, дату чи статус.</p>
      <Link className="button button-secondary" to={demo ? "?demo=1" : "?"}>
        Скинути фільтри
      </Link>
    </div>
  );
}
