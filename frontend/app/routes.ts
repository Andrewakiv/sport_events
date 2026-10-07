import { index, route, type RouteConfig } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route(
    "football/champions-league/matches",
    "routes/champions-league-matches.tsx",
  ),
  route(
    "football/champions-league/matches/:matchId",
    "routes/champions-league-match.tsx",
  ),
] satisfies RouteConfig;
