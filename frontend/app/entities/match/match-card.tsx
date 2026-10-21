import { Link, useLocation } from "react-router";

import type { Match } from "../../shared/api/types";
import {
  formatMatchTime,
  stageLabel,
  statusLabel,
  teamInitials,
} from "../../shared/format";

interface MatchCardProps {
  match: Match;
}

export function MatchCard({ match }: MatchCardProps) {
  const location = useLocation();
  const detailSearch = new URLSearchParams({
    returnTo: `${location.pathname}${location.search}`,
  });

  const finished = match.status === "FINISHED";
  const live = match.status === "IN_PLAY" || match.status === "PAUSED";

  return (
    <Link
      className="match-card"
      to={`${match.id}?${detailSearch.toString()}`}
      aria-label={`${match.home_team?.name ?? "Team to be confirmed"} — ${match.away_team?.name ?? "Team to be confirmed"}`}
    >
      <div className="match-time">
        <strong>{formatMatchTime(match.kickoff_at)}</strong>
        <span className={`status-pill status-${match.status.toLowerCase()}`}>
          {live && <i aria-hidden="true" />}
          {statusLabel(match.status)}
        </span>
      </div>

      <div className="match-teams">
        <TeamRow
          name={match.home_team?.name}
          score={finished ? match.score?.home : undefined}
        />
        <TeamRow
          name={match.away_team?.name}
          score={finished ? match.score?.away : undefined}
        />
      </div>

      <div className="match-meta">
        <span>{stageLabel(match.stage)}</span>
        {match.matchday !== null && <span>Matchday {match.matchday}</span>}
        <span className="arrow" aria-hidden="true">
          ↗
        </span>
      </div>
    </Link>
  );
}

function TeamRow({
  name,
  score,
}: {
  name: string | undefined;
  score: number | undefined;
}) {
  return (
    <div className="team-row">
      <span className="team-badge" aria-hidden="true">
        {teamInitials(name)}
      </span>
      <strong className={!name ? "team-tbd" : undefined}>
        {name ?? "To be confirmed"}
      </strong>
      <b>{score ?? "—"}</b>
    </div>
  );
}
