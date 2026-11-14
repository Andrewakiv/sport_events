import { Link } from "react-router";

import { MatchChat } from "../features/match-chat/match-chat";

export function meta() {
  return [
    { title: "Ask about matches — Sport Events" },
    {
      name: "description",
      content:
        "Ask questions about UEFA Champions League fixtures and results.",
    },
  ];
}

export default function ChampionsLeagueChat() {
  return (
    <main className="chat-page">
      <Link className="back-link" to="/football/champions-league/matches">
        ← Back to matches
      </Link>
      <MatchChat />
    </main>
  );
}
