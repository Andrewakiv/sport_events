import { Link } from "react-router";

import type { Route } from "./+types/champions-league-match";
import { ApiError, getMatch } from "../shared/api/client";
import type { Match } from "../shared/api/types";
import { safeReturnTo } from "../shared/return-to";
import {
  formatLongKickoff,
  stageLabel,
  statusLabel,
  teamInitials,
} from "../shared/format";

type LoaderData =
  | { ok: true; match: Match | null; returnTo: string }
  | { ok: false; message: string; status?: number; returnTo: string };

export async function clientLoader({
  params,
  request,
}: Route.ClientLoaderArgs): Promise<LoaderData> {
  const url = new URL(request.url);
  const matchId = Number(params.matchId);
  const returnTo = safeReturnTo(url.searchParams.get("returnTo"));

  if (!Number.isInteger(matchId) || matchId <= 0) {
    return { ok: true, match: null, returnTo };
  }

  try {
    return { ok: true, match: await getMatch(matchId), returnTo };
  } catch (error) {
    if (error instanceof ApiError) {
      return {
        ok: false,
        message: error.message,
        status: error.status,
        returnTo,
      };
    }
    return {
      ok: false,
      message: "The API is currently unavailable.",
      returnTo,
    };
  }
}

export function meta({ data }: Route.MetaArgs) {
  if (!data?.ok || !data.match)
    return [{ title: "Match not found — Sport Events" }];
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
          ← Back to matches
        </Link>
        <div className="state-card error-state" role="alert">
          <p className="eyebrow">API {loaderData.status ?? "offline"}</p>
          <h1>Unable to load match</h1>
          <p>{loaderData.message}</p>
        </div>
      </main>
    );
  }

  if (!loaderData.match) {
    return (
      <main className="detail-page">
        <Link className="back-link" to={loaderData.returnTo}>
          ← Back to matches
        </Link>
        <div className="state-card">
          <p className="eyebrow">404</p>
          <h1>Match not found</h1>
          <p>Check the address or return to the fixture list.</p>
        </div>
      </main>
    );
  }

  const match = loaderData.match;
  const finished = match.status === "FINISHED";

  return (
    <main className="detail-page">
      <Link className="back-link" to={loaderData.returnTo}>
        ← Back to matches
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
          <p className="eyebrow">Match #{match.id}</p>
          <h1 id="details-heading">Match details</h1>
        </div>
        <dl>
          <Fact
            label="Season"
            value={`${match.season.start_date.slice(0, 4)} / ${match.season.end_date.slice(0, 4)}`}
          />
          <Fact label="Stage" value={stageLabel(match.stage)} />
          <Fact label="Matchday" value={match.matchday?.toString() ?? "—"} />
          <Fact label="Group" value={match.group ?? "—"} />
          <Fact label="Duration" value={match.score?.duration ?? "—"} />
        </dl>
      </section>
    </main>
  );
}

function DetailTeam({ name }: { name: string | undefined }) {
  return (
    <div className="detail-team">
      <span className="detail-team-badge" aria-hidden="true">
        {teamInitials(name)}
      </span>
      <h2>{name ?? "To be confirmed"}</h2>
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
