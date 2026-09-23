# Champions League provider contract

- Issue: [#4](https://github.com/Andrewakiv/sport_events/issues/4)
- Provider: football-data.org API v4
- Observed: 2026-09-23, using this project's authenticated account
- Competition: UEFA Champions League (`CL`, provider ID `2001`)

This is an observed input contract for future import work, not an application or
database schema. The accompanying [match samples](../tests/fixtures/champions_league_matches.json)
contain selected fields from actual match-list responses. Unselected fields were
omitted; retained values were not fabricated or changed. No credentials or request
headers are included.

## Access verified

`GET /v4/competitions/CL` returned HTTP 200. Its `currentSeason.startDate` is
`2026-09-08`, so the four requested seasons use start years 2026–2023. Every
`GET /v4/competitions/CL/matches?season=<year>` below returned HTTP 200:

| Season | Provider season ID | Matches | Observed status | Observed stages |
| --- | ---: | ---: | --- | --- |
| 2026/27 | 2557 | 144 | 18 `FINISHED`, 126 `TIMED` | `LEAGUE_STAGE` |
| 2025/26 | 2454 | 189 | 189 `FINISHED` | `LEAGUE_STAGE`, `PLAYOFFS`, `LAST_16`, `QUARTER_FINALS`, `SEMI_FINALS`, `FINAL` |
| 2024/25 | 2350 | 189 | 189 `FINISHED` | `LEAGUE_STAGE`, `PLAYOFFS`, `LAST_16`, `QUARTER_FINALS`, `SEMI_FINALS`, `FINAL` |
| 2023/24 | 1630 | 125 | 125 `FINISHED` | `GROUP_STAGE`, `LAST_16`, `QUARTER_FINALS`, `SEMI_FINALS`, `FINAL` |

The 2026/27 response currently ends at `2027-01-27`; it does not yet contain
knockout fixtures. Do not interpret the provider's current `endDate` as a
guarantee that the tournament itself ends then. Earlier seasons were not tested.

## Observed fields and nullability

Every match in the four responses had these top-level keys: `area`,
`competition`, `season`, `id`, `utcDate`, `status`, `matchday`, `stage`, `group`,
`lastUpdated`, `homeTeam`, `awayTeam`, `score`, `odds`, and `referees`.

- `id` is the provider match identifier. `competition.id` was `2001`; each
  `season.id` is listed above. Both `homeTeam.id` and `awayTeam.id` were present
  in all 647 observed matches. These IDs should remain provider-scoped.
- `utcDate` and `lastUpdated` are UTC timestamp strings. `stage` is not fixed
  across seasons: the 2023/24 format uses `GROUP_STAGE`, while later seasons use
  `LEAGUE_STAGE`.
- `group` was `null` for all 2024–2026 matches; in 2023/24 it was populated
  for 96 group-stage matches and `null` for 29 knockout matches. `matchday` was
  `null` for the sampled 2025/26 final and for one 2023/24 match.
- `score.fullTime.home` and `.away` were `null` in all 126 `TIMED` matches and
  populated in every observed `FINISHED` match. `score.winner` may also be
  `null` before play. The penalty-shootout final additionally supplied
  `score.regularTime`, `score.extraTime`, and `score.penalties`; do not assume
  all score objects have identical keys or that `fullTime` means regulation
  time in a penalty shootout.
- `referees` was an empty list for all 126 `TIMED` matches and populated in
  the sampled finished matches. The sample responses' `odds` object contained
  an activation message, not odds data. All 189 matches checked in 2024/25
  had that restriction message.
- `season.winner` was `null` even in the completed 2025/26 final response;
  it was populated in the sampled 2023/24 response. Do not infer season
  completion or a winner from this field alone.

No `SCHEDULED`, `POSTPONED`, or `CANCELLED` match occurred in these four
responses. Such statuses are documented by the provider but have **not** been
verified with a real `CL` example in this scope; no synthetic fixture was added.
Likewise, deep match details such as lineups and goals were not requested or
verified. Match lists fold them by default.

## Operational limits

- Use the `X-Auth-Token` header. The same competition endpoint returned HTTP
  403 without authentication. Keep `FOOTBALL_DATA_API_TOKEN` in local `.env`
  only; `.env` is Git-ignored.
- The provider publishes 10 requests/minute for its free plan and delayed
  scores/schedules. This account's exact plan and live-data entitlement were
  not verified. The four requested historical seasons are accessible, but
  access further back is unknown.
- The sampled `odds` response requires an additional Odds Package; do not
  treat the object as usable odds data.

## Sources

- [Competition endpoints and season filters](https://docs.football-data.org/general/v4/competition.html)
- [Match fields and status behavior](https://docs.football-data.org/general/v4/match.html)
- [Null, rate-limit, and folding policies](https://docs.football-data.org/general/v4/policies.html)
- [Published plans](https://www.football-data.org/pricing)
