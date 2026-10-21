import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";

import type { Match } from "../../shared/api/types";
import { MatchCard } from "./match-card";

const scheduledMatch: Match = {
  id: 42,
  season: { id: 2026, start_date: "2026-07-01", end_date: "2027-05-31" },
  kickoff_at: "2026-10-07T19:00:00Z",
  status: "SCHEDULED",
  stage: "LEAGUE_STAGE",
  matchday: 2,
  group: null,
  home_team: { id: 64, name: "Liverpool FC" },
  away_team: null,
  score: null,
};

describe("MatchCard", () => {
  it("does not fabricate a score or missing team", () => {
    render(
      <MemoryRouter
        initialEntries={["/football/champions-league/matches?season=2026"]}
      >
        <Routes>
          <Route
            path="/football/champions-league/matches"
            element={<MatchCard match={scheduledMatch} />}
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Liverpool FC")).toBeInTheDocument();
    expect(screen.getByText("To be confirmed")).toBeInTheDocument();
    expect(screen.getAllByText("—")).toHaveLength(2);
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "/football/champions-league/matches/42?returnTo=%2Ffootball%2Fchampions-league%2Fmatches%3Fseason%3D2026",
    );
  });
});
