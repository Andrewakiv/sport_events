import { Link } from "react-router";

import type { Route } from "./+types/champions-league-match";
import { ApiError, getMatch } from "../shared/api/client";
import type { Match } from "../shared/api/types";
import {
  formatLongKickoff,
  stageLabel,
  statusLabel,
  teamInitials,
} from "../shared/format";

type LoaderData =
  | { ok: true; match: Match | null; demo: boolean; returnTo: string }
  | { ok: false; message: string; status?: number; returnTo: string };

export async function clientLoader({
  params,
  request,
}: Route.ClientLoaderArgs): Promise<LoaderData> {
  const url = new URL(request.url);
  const matchId = Number(params.matchId);
  const demo = url.searchParams.get("demo") === "1";
  const returnTo = safeReturnTo(url.searchParams.get("returnTo"));

  if (!Number.isInteger(matchId) || matchId <= 0) {
    return { ok: true, match: null, demo, returnTo };
  }

  try {
    return { ok: true, match: await getMatch(matchId, demo), demo, returnTo };
  } catch (error) {
    if (error instanceof ApiError) {
      return {
        ok: false,
        message: error.message,
        status: error.status,
        returnTo,
      };
    }
    return { ok: false, message: "API зараз недоступний.", returnTo };
  }
}

export function meta({ data }: Route.MetaArgs) {
  if (!data?.ok || !data.match)
    return [{ title: "Матч не знайдено — Sport Events" }];
  const home = data.match.home_team?.name ?? "TBD";
  const away = data.match.away_team?.name ?? "TBD";
  return [{ title: `${home} — ${away} · Sport Events` }];
}

export default function ChampionsLeagueMatch({
  loaderData,
}: Route.ComponentProps) {
  if (!loaderData.ok) {
    return (
      <main className="detail-page">
        <Link className="back-link" to={loaderData.returnTo}>
          ← До матчів
        </Link>
        <div className="state-card error-state" role="alert">
          <p className="eyebrow">API {loaderData.status ?? "offline"}</p>
          <h1>Не вдалося відкрити матч</h1>
          <p>{loaderData.message}</p>
        </div>
      </main>
    );
  }

  if (!loaderData.match) {
    return (
      <main className="detail-page">
        <Link className="back-link" to={loaderData.returnTo}>
          ← До матчів
        </Link>
        <div className="state-card">
          <p className="eyebrow">404</p>
          <h1>Матч не знайдено</h1>
          <p>Перевірте адресу або поверніться до загального розкладу.</p>
        </div>
      </main>
    );
  }

  const match = loaderData.match;
  const finished = match.status === "FINISHED";

  return (
    <main className="detail-page">
      <Link className="back-link" to={loaderData.returnTo}>
        ← До матчів
      </Link>

      <section className="scoreboard">
        <div className="scoreboard-topline">
          <span>{stageLabel(match.stage)}</span>
          <span className={`status-pill status-${match.status.toLowerCase()}`}>
            {statusLabel(match.status)}
          </span>
        </div>

        <div className="scoreboard-teams">
          <DetailTeam name={match.home_team?.name} />
          <div className="score-block">
            {finished && match.score ? (
              <strong>
                {match.score.home}
                <i>:</i>
                {match.score.away}
              </strong>
            ) : (
              <strong className="versus">VS</strong>
            )}
            <span>{formatLongKickoff(match.kickoff_at)}</span>
          </div>
          <DetailTeam name={match.away_team?.name} />
        </div>
      </section>

      <section className="detail-facts" aria-labelledby="details-heading">
        <div>
          <p className="eyebrow">Матч #{match.id}</p>
          <h1 id="details-heading">Деталі події</h1>
        </div>
        <dl>
          <Fact
            label="Сезон"
            value={`${match.season.start_date.slice(0, 4)} / ${match.season.end_date.slice(0, 4)}`}
          />
          <Fact label="Стадія" value={stageLabel(match.stage)} />
          <Fact label="Тур" value={match.matchday?.toString() ?? "—"} />
          <Fact label="Група" value={match.group ?? "—"} />
          <Fact label="Тривалість" value={match.score?.duration ?? "—"} />
        </dl>
      </section>

      {loaderData.demo && (
        <p className="demo-disclaimer">Демонстраційні дані для UI preview.</p>
      )}
    </main>
  );
}

function DetailTeam({ name }: { name: string | undefined }) {
  return (
    <div className="detail-team">
      <span className="detail-team-badge" aria-hidden="true">
        {teamInitials(name)}
      </span>
      <h2>{name ?? "Ще не визначено"}</h2>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function safeReturnTo(value: string | null): string {
  const fallback = "/football/champions-league/matches";
  return value?.startsWith(fallback) ? value : fallback;
}
