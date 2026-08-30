# Design: Transfermarkt Player Market Values Scraper

**Date:** 2026-08-31

## Goal

Scrape Premier League player market values from Transfermarkt for the 2018–2026
window and write them to a standalone CSV, matching the player-statistics
dataset already collected for those seasons.

## The barrier (verified)

`transfermarkt.com` is protected by an AWS WAF **captcha** ("Human Verification"
page). Verified blocked by: plain curl (405), headless Playwright, headed
Playwright, playwright-stealth, and nodriver. All routes and TLDs are blocked
from this network. Community API mirrors (`transfermarkt-api.fly.dev`,
`transfermarkt-api.vercel.app`) are down/disabled. **Automated access is not
possible without one human captcha solve.**

## Approach

A Playwright-driven scraper that opens a real browser window and waits for the
user to solve the one-time captcha, then scrapes the market-value data in that
same authenticated browser session.

## Source pages

- League market-values leaderboard (user-supplied URL):
  `https://www.transfermarkt.com/premier-league/marktwerte/wettbewerb/GB1/ausrichtung//spielerposition_id//altersklasse//land_id/0/only_loans//plus/1`
  - Lists all PL players: name, club, age, nationality, current market value.
  - Paginated (~9 pages). Pagination links extracted from the page HTML.
- Per-player market-value history page (timeline):
  `https://www.transfermarkt.com/{slug}/marktwerteverlauf/spieler/{playerId}`
  - One row per value-change event: `date (YYYY-MM-DD)`, `value`, `age`.
  - Only rows with `date` in [2018, 2026] are kept.

## Implementation

Single script `scrape_market_values.py`. Python 3 with Playwright (already
installed in the environment) and stdlib `html.parser`/`csv`/`argparse` for
parsing and output.

### Flow

1. Launch headed Chromium. Navigate to the leaderboard URL.
2. If the "Human Verification" page appears, print a prompt telling the user to
   solve the captcha in the opened window. Poll every 2s until the market-value
   table is present (or a timeout of 10 min).
3. Scrape the leaderboard across all pages via Playwright's `context.request`
   (reuses the solved session cookies — the `aws-waf-token` cookie makes plain
   requests pass without re-rendering each page). Rows → player id, name, club,
   current value. The player link in each row provides both the slug and the
   numeric player id used to build the timeline URL.
4. For each player, `context.request.get` their `marktwerteverlauf` page, parse
   `(date, value)` events, keep 2018–2026, append to the CSV incrementally.
5. Write `data/transfermarkt_market_values.csv`.

### CSV schema

```
player_id,player_name,club,date,market_value_eur
```

One row per value-change event within the window. Values are integers of euros
(Transfermarkt formats them like `€180.00m` / `€25m` / `€500k`).

### Parsing strategy

Extract leaderboard rows and timeline rows by Transfermarkt's known CSS class
names (e.g. `hauptlink` for player name, `rechts hauptlink` for value) using
stdlib `HTMLParser`. A lenient fallback pattern (any table row containing an
anchor link to `/spieler/{id}` plus a value token) is applied when the primary
selector finds nothing, so a changed layout never silently drops rows.

### CLI

```
python3 scrape_market_values.py [--url <leaderboard-url>] [--from-year 2018]
    [--to-year 2026] [--out data/transfermarkt_market_values.csv]
    [--timeout-min 10]
```

### Resilience

- Incremental writes: each player's rows are appended as they complete, so an
  interrupted run keeps all previously scraped players. Re-running skips
  players already in the output file unless `--force`.
- Clear timeout error if the captcha is not solved in time.
- Per-request retry (up to 3) with backoff on transient failures.

## Testing

`--self-test` (run after the captcha solve) validates parsing against live
pages:
- Fetches 2–3 known players (e.g. Erling Haaland id `819840`, Mohamed Salah)
  and asserts their timeline pages contain ≥1 parseable `(date, value)` row
  with a positive integer value and a parseable date.
- Asserts the leaderboard parse yields ≥ 400 player rows.
- Prints a short sample of parsed rows for eyeball verification.

This is the single runnable check (no test framework).

## Volume / runtime

- ~900 players × 1 timeline request ≈ 900 fast requests (via `context.request`,
  no page rendering) ≈ 15–30 min.
- Leaderboard: ~9 pages.

## Out of scope

- Data before 2018 or after 2026.
- Non-PL competitions.
- Joining market values into the per-season stats CSVs (standalone output
  chosen by the user).
