# Design: Premier League Player Stats Scraper (2018/19–2025/26)

**Date:** 2026-08-31

## Goal

A data scraper that downloads English Premier League player statistics from the
official Premier League site (via its public JSON API) for all players and all
available stat categories, for seasons 2018/19 through 2025/26. Output is CSV.

## Data sources (official PL JSON API)

Base: `https://sdp-prem-prod.premier-league-prod.pulselive.com`

All requests require headers `Origin: https://www.premierleague.com` and a
browser User-Agent.

### S1. Per-season player leaderboard (primary)

```
GET /api/v3/competitions/8/seasons/{season}/players/stats/leaderboard
    ?_sort=goals:desc&country=&_limit=100[&_next={cursor}]
```

- `season` ∈ {2018, 2019, ..., 2025} mapping to 2018/19 … 2025/26.
- Pagination: the response's `pagination._next` is an opaque cursor. Request
  the first page without `_next`, then append `&_next={cursor}` for each
  subsequent page until `pagination._next` is null (the `_page` parameter is
  ignored by this API and must not be used). ~267 players per season. Each row:
  - `playerMetadata`: `id`, `name`, `position`, `currentTeam.name`, `country`.
  - `stats`: ~90 numeric fields (`goals`, `goalAssists`, `appearances`,
    `timePlayed`, `totalShots`, `shotsOnTargetIncGoals`, `totalPasses`,
    `accuratePasses`, `tacklesWon`, `totalTackles`, `interceptions`,
    `totalClearances`, `blocks`, `duelsWon`, `aerialDuelsWon`, `savesMade`,
    `cleanSheets`, `yellowCards`, `totalRedCards`, etc.). No xG.

### S2. Per-player career stats (only source of xG/xA)

```
GET /api/v1/competitions/8/players/{playerId}/stats
```

- Returns 135 stats as career totals across all seasons, including
  `expectedGoals`, `expectedAssists`, `expectedGoalsOnTarget`,
  `expectedGoalsFreekick`, `expectedGoalsOnTargetConceded`.
- Fetched once per unique player id (union across all seasons).
- NOTE: xG/xA are **career totals only**; the official API does not expose
  per-season xG. This limitation is accepted by the user.

## Scope

- Seasons: 2018/19 (id `2018`) through 2025/26 (id `2025`). 2026/27 (in
  progress) is excluded.
- Per-season aggregate stats only. No per-match breakdowns.
- xG/xA included as career totals per player.

## Implementation

Single script `scrape.py` in Python 3 stdlib only (`urllib.request`, `json`,
`csv`, `argparse`, `time`). No third-party dependencies.

### Functions

1. `fetch(url)` — GET with headers, JSON parse, retry up to 5 times with
   backoff on network errors / 429 / 5xx. 0.2s delay between requests.
2. `get_season_players(season)` — paginate S1 following `pagination._next`
   until null, return list of rows `{playerMetadata, stats}`.
3. `get_career_xg(player_ids)` — for each unique id, fetch S2 and keep the 5
   xG fields. 0.1s delay between requests.
4. `write_season_csv(season, rows)` — wide CSV, one row per player.
5. `write_xg_csv(rows)` — one row per player.

### CSV schema

Season files `data/players_2018-19.csv` … `data/players_2025-26.csv`:

- Identity columns: `player_id`, `name`, `position`, `team`.
- One column per stat key, using the API's raw key names. Column set is the
  union of keys across all seasons so files share a schema; missing values are
  empty.

xG file `data/players_career_xg.csv`:

- `player_id`, `name`, `expectedGoals`, `expectedAssists`,
  `expectedGoalsOnTarget`, `expectedGoalsFreekick`,
  `expectedGoalsOnTargetConceded`.

### CLI

```
python3 scrape.py [--from 2018] [--to 2025] [--out data]
                  [--no-xg] [--force] [--self-test]
```

- `--from` / `--to`: season year range (default full 2018–2025).
- `--out`: output directory (default `data`).
- `--no-xg`: skip the xG pass.
- `--force`: overwrite existing season CSV files (default: skip existing, so a
  rerun resumes).
- `--self-test`: run asserts and exit (see Testing).

## Error handling / resilience

- Retry with backoff; season files written as completed, so interrupted runs
  resume without re-scraping done seasons.
- Failed seasons are logged and skipped, leaving the run to continue.

## Testing

`--self-test` performs assert-based checks using live API calls (small, cheap):
- Season 2018/19 leaderboard: top scorer value is 22, and it returns at least
  250 unique players.
- Each season returns at least 250 players.
- Career xG endpoint returns a value for a known player.
- Column set is consistent across seasons.

This is the single runnable check (no test framework).

## Volume / runtime

- ~8 seasons × ~3 pages ≈ 25 leaderboard requests.
- ~1,200–1,500 unique players × 1 xG request ≈ 1,500 requests.
- Total ≈ 10–15 minutes with the built-in delays.

## Out of scope

- Per-match player statistics.
- Per-season xG (not available from the official API).
- Other competitions (only PL, competition id `8`).
