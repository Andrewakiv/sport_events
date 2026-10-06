# Formula 1 provider contract

- Issue: [#9](https://github.com/Andrewakiv/sport_events/issues/9)
- Provider: Jolpica F1, Ergast-compatible API
- Base URL: `https://api.jolpi.ca/ergast/f1/`
- Observed: 2026-09-29, without an API token

This is an observed input contract for future import work, not an application or
database schema. It deliberately covers only calendars, race qualifying, sprint
results, and race results. The accompanying [event samples](../tests/fixtures/jolpica_f1_events.json)
retain selected values from real responses while omitting URLs, biographical fields,
and unneeded classification rows. No credentials or request headers are included.

The Ergast-compatible endpoints are the agreed initial integration surface. Jolpica's
newer `/f1/alpha/` endpoints expose additional session types, but were explicitly
alpha at the time of observation and are not part of this contract.

## Access verified

These season endpoints returned HTTP 200 with `limit=100` and offset pagination:

- `/{season}/races/`
- `/{season}/qualifying/`
- `/{season}/sprint/`
- `/{season}/results/`

`MRData.total` counts classification rows for qualifying, sprint, and result
endpoints, not race weekends. Distinct rounds were counted across every page.

| Season | Calendar rounds | Qualifying rows / rounds | Sprint rows / rounds | Race rows / rounds |
| --- | ---: | ---: | ---: | ---: |
| 2026 | 23 | 325 / 15 | 110 / 5 | 330 / 15 |
| 2025 | 24 | 479 / 24 | 120 / 6 | 479 / 24 |
| 2024 | 24 | 479 / 24 | 120 / 6 | 479 / 24 |
| 2023 | 22 | 440 / 22 | 120 / 6 | 440 / 22 |

At capture time, 2026 rounds 1–15 had race and qualifying data. Eight later
rounds were present only in the calendar. The calendar listed six sprint weekends;
the first five had sprint results and round 17 (Singapore, 2026-10-11) was still
scheduled. Empty `RaceTable.Races` arrays with `total: "0"` are therefore a normal
response for a known future session, not evidence that the event does not exist.

The 479-row historical totals are not by themselves provider omissions. The 2024
Australian Grand Prix has 19 qualifying and race classifications, and the 2025
Spanish Grand Prix has 20 qualifying but 19 race classifications. The 2025 São
Paulo Grand Prix has 19 qualifying classifications. Importers must retain the rows
actually returned and must not synthesize a fixed grid size.

## Calendar shape

Every observed race contained `season`, `round`, `raceName`, `Circuit`, `date`,
`time`, `FirstPractice`, and `Qualifying`. A normal weekend also contained
`SecondPractice` and `ThirdPractice`. Sprint weekends replace those two practice
objects with sprint-specific objects:

| Season | Sprint weekends | Sprint schedule keys |
| --- | ---: | --- |
| 2023 | 6 | `Sprint`, `SprintShootout` |
| 2024 | 6 | `Sprint`, `SprintQualifying` |
| 2025 | 6 | `Sprint`, `SprintQualifying` |
| 2026 | 6 | `Sprint`, `SprintQualifying` |

Session values contain separate `date` and `time` strings. Observed `time` values
end in `Z`; combine them as UTC timestamps. Treat every session object and its time
as optional because Jolpica documents them as conditional and may publish dates
before session times are confirmed. Presence of `Sprint` in the calendar is the
authoritative sprint-weekend signal; an empty sprint-result endpoint can also mean
that a scheduled sprint has not happened yet.

The Ergast-compatible API supplies results for race qualifying, sprint, and race.
It does not supply free-practice or sprint-qualifying classifications. The alpha
API announced those result types in 2026, but adopting it requires a later contract
decision because its identifiers and response shapes are not stable here.

## Stable identifiers and mapping decisions

All keys below are provider-scoped. Do not join them to another provider without an
explicit crosswalk.

| Concept | Provider field | Import key and decision |
| --- | --- | --- |
| Season | `season` | Four-digit string; normalize to an integer year. There is no numeric season ID. |
| Grand Prix | `season`, `round` | Composite key `(season, round)`. `round` restarts each season and is returned as a numeric string. Do not use `raceName` or Wikipedia `url` as identity. |
| Circuit | `Circuit.circuitId` | Stable provider identifier. Store names and location as mutable attributes. Latitude and longitude are numeric strings. |
| Driver | `Driver.driverId` | Stable provider identifier. Car `number`, `permanentNumber`, code, and name are attributes, not keys; historical nested driver attributes can reflect later changes. |
| Constructor | `Constructor.constructorId` | Stable provider identifier. Name and nationality are mutable attributes. |
| Session | no provider ID | Derive `(season, round, session_type)`, where the contracted result types are `qualifying`, `sprint`, and `race`. Keep practice and sprint-qualifying schedule times as calendar attributes only. |
| Classification | no provider ID | Derive `(season, round, session_type, driverId)`. Position can change after penalties or corrections and must not be part of identity. |

Calendar, qualifying, sprint, and race responses repeat race, circuit, driver, and
constructor data. The importer should reconcile by these keys and treat the latest
successful observation as mutable provider state. It must not create separate Grand
Prix records just because a repeated name or URL differs.

## Classification fields and optionality

Provider numbers are JSON strings. Parse them only after checking for absence or an
empty string, and preserve the original value when lossless display matters.

### Qualifying

Each `QualifyingResults` row has `number`, `Driver`, and `Constructor`. `position`,
`Q1`, `Q2`, and `Q3` are conditional. Later phase times are naturally absent for
eliminated drivers; an observed 2025 row also used an empty `Q2` string. Missing or
empty phase times map to `null`, not zero. A qualifying position is not necessarily
the final race grid after penalties.

The 2026 endpoint exposes an additional gap: Australian round 1 has 19 qualifying
rows but 22 race rows (`max_verstappen`, `sainz`, and `stroll` occur only in the race
response), and Spanish round 14 has 20 qualifying rows but 22 race rows (`bearman`
and `stroll` occur only in the race response). The payload gives no reason. A race
classification must not require a matching qualifying classification.

### Sprint and race

`SprintResults` and `Results` rows can contain `number`, `position`, `positionText`,
`points`, `Driver`, `Constructor`, `grid`, `laps`, `status`, `Time`, and
`FastestLap`. Several are conditional:

- `positionText` may be non-numeric, such as `R`; use numeric `position` for order
  and retain `positionText` for provider display semantics.
- `Time` is absent for some retired classifications. Winner time is absolute while
  later `time` strings can be gaps; do not parse all display strings as durations
  with the same meaning.
- `FastestLap`, `AverageSpeed`, and nested time fields are optional.
- `grid` can be zero or missing for pit-lane and unresolved starts. It is not an
  event-participation key.
- `status` is mutable provider text. Jolpica warns that status mappings may change;
  retain the raw value and do not make it a closed application enum.
- `points` can be fractional in Formula 1 history, so use a decimal representation
  if it is persisted later.

## Missing, delayed, and mutable data

- Calendar records can precede classifications by months. Scheduled sessions have
  no explicit status field; completion is established only by a non-empty result
  endpoint.
- Responses contain no per-record `lastUpdated` timestamp. Record the fetch time
  locally and refresh mutable current-season data. A successful empty response does
  not prove a session was cancelled.
- Jolpica has described updates as volunteer-operated and not guaranteed within
  hours of a session. Its published guidance has historically targeted at least a
  post-weekend update, with possible upstream delays. This source is not suitable
  for the product's live-update path without a separate decision.
- Calendar times can be omitted until confirmed and can change. Results and
  positions can be corrected after initial publication. Upserts must be idempotent
  on the composite keys above.
- The Ergast-compatible surface omits free-practice and sprint-qualifying results.
  Do not infer either from calendar times or ordinary qualifying results.
- The provider makes no uptime or correctness guarantee. Preserve the last
  successful snapshot when a refresh fails or returns an implausible regression;
  alert for review rather than deleting existing data.

## Operational limits and use

- No API key was required for the verified endpoints. Send an identifying custom
  `User-Agent` such as `sport-events/<version>`; Jolpica says default user agents may
  be blocked.
- The documented page limit is 100 rows. Follow `MRData.total`, `limit`, and
  `offset`; a single season classification response is not complete when
  `total > limit`.
- Jolpica maintainers state unauthenticated limits of 4 requests/second and 500
  requests/hour. Throttle below both limits, cache unchanged historical seasons,
  serialize pagination, and back off on HTTP 429 or provider throttling responses.
- The service is free for non-commercial use and its data is published under
  CC BY-NC-SA 4.0. Commercial use requires contacting Jolpica. Any product release
  must review attribution and share-alike obligations before redistributing data.
- Jolpica is volunteer-run and disclaims availability and correctness guarantees.
  Retry and stale-data behavior belong in the later client/synchronization issues,
  not in this discovery change.

## Sources

- [Jolpica documentation and common response fields](https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md)
- [Race calendar fields](https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/races.md)
- [Qualifying fields](https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/qualifying.md)
- [Sprint fields](https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/sprint.md)
- [Race-result fields](https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/results.md)
- [Status mapping caveats](https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/status.md)
- [Maintainer rate-limit guidance](https://github.com/jolpica/jolpica-f1/discussions/80)
- [Maintainer update-frequency guidance](https://github.com/jolpica/jolpica-f1/discussions/95)
- [Terms of use](https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md)
- [Alpha results announcement](https://github.com/jolpica/jolpica-f1/discussions/319)
