# PL Player Stats Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `scrape.py`, a Python 3 stdlib-only scraper that downloads Premier League player statistics (all players, all available stats) for seasons 2018/19–2025/26 from the official PL JSON API and writes one wide CSV per season plus a career-xG CSV.

**Architecture:** Single script. `fetch()` wraps the API with headers/retry; `get_season_players()` paginates the per-season leaderboard via the `_next` cursor; `write_season_csv()` writes a wide per-season CSV; `get_career_xg()` fetches career xG/xA per player; `main()` wires CLI, resume-skip, and `--self-test`.

**Tech Stack:** Python 3 stdlib only (`urllib.request`, `json`, `csv`, `argparse`, `time`, `pathlib`). No third-party dependencies. Tests are assert-based, run via `python3 scrape.py --self-test` and one-liner `python3 -c` checks.

## Global Constraints

- Python 3.8+ (uses `pathlib`, f-strings).
- **No third-party dependencies** — stdlib only.
- API base: `https://sdp-prem-prod.premier-league-prod.pulselive.com`
- Every request MUST send headers `Origin: https://www.premierleague.com` and a browser `User-Agent` (both defined in `HEADERS`).
- Seasons 2018–2025 (2018=2018/19 … 2025=2025/26). Season label format `{season}-{last2 of season+1}`, e.g. `2018-19`.
- Per-season leaderboard pagination uses the opaque `pagination._next` cursor appended as `&_next={cursor}`; the `_page` param is ignored by the API and must NOT be used.
- xG/xA are career totals only (official API limitation, accepted).
- Output directory default: `data/` (gitignored). Per-season files: `data/players_2018-19.csv` … `data/players_2025-26.csv`. Career xG: `data/players_career_xg.csv`.
- Runaway loops/duplicate rows are bugs: every season file must have unique `player_id` values and ≥250 rows.

---

### Task 1: Repo setup + `fetch()`

**Files:**
- Create: `.gitignore`
- Create: `scrape.py` (module header, constants, `fetch()` only)

**Interfaces:**
- Consumes: nothing.
- Produces: `fetch(url: str, retries: int = 5) -> dict` — GETs `url` with `HEADERS`, returns parsed JSON, retries with `2*(attempt+1)` second backoff on 429/5xx/network errors, raises on final failure.

- [ ] **Step 1: Create `.gitignore`** so the downloaded data is never committed.

```
data/
__pycache__/
```

- [ ] **Step 2: Create `scrape.py` with the module skeleton and `fetch()`**

```python
#!/usr/bin/env python3
"""Scrape Premier League player stats (2018/19-2025/26) from the official site's JSON API."""
import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://sdp-prem-prod.premier-league-prod.pulselive.com"
HEADERS = {
    "Origin": "https://www.premierleague.com",
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0 Safari/537.36"),
}
XG_FIELDS = ["expectedGoals", "expectedAssists", "expectedGoalsOnTarget",
             "expectedGoalsFreekick", "expectedGoalsOnTargetConceded"]
IDENTITY = ["player_id", "name", "position", "team"]


def fetch(url, retries=5):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, OSError, TimeoutError):
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"could not fetch {url}")
```

- [ ] **Step 3: Verify `fetch()` against the live API**

Run:
```bash
python3 -c "import scrape; d=scrape.fetch(scrape.API+'/api/v3/competitions/8/seasons/2018/players/stats/leaderboard?_sort=goals:desc&country=&_limit=5'); assert 'data' in d and len(d['data'])==5; print('fetch ok')"
```
Expected: `fetch ok`

- [ ] **Step 4: Commit**

```bash
git add .gitignore scrape.py
git commit -m "feat: add fetch() with retry and repo gitignore"
```

---

### Task 2: `get_season_players()` + `season_label()`

**Files:**
- Modify: `scrape.py` (add `get_season_players`, `season_label` after `fetch`)

**Interfaces:**
- Consumes: `fetch(url)` from Task 1.
- Produces:
  - `get_season_players(season: int) -> list[dict]` — all leaderboard rows for the season (each row has `playerMetadata.id/name/position/currentTeam.name` and `stats: dict`), paginated by following `pagination._next` until it is null.
  - `season_label(season: int) -> str` — e.g. `2018` → `"2018-19"`.

- [ ] **Step 1: Add the two functions**

```python
def get_season_players(season):
    rows, nxt = [], None
    while True:
        url = (f"{API}/api/v3/competitions/8/seasons/{season}/players/stats/"
               "leaderboard?_sort=goals:desc&country=&_limit=100")
        if nxt:
            url += "&_next=" + nxt
        data = fetch(url)
        rows.extend(data.get("data") or [])
        nxt = (data.get("pagination") or {}).get("_next")
        if not nxt:
            return rows


def season_label(season):
    return f"{season}-{str(season + 1)[-2:]}"
```

- [ ] **Step 2: Verify pagination terminates and returns unique players**

Run:
```bash
python3 -c "import scrape; rows=scrape.get_season_players(2018); ids=[r['playerMetadata']['id'] for r in rows]; assert len(rows)>=250, len(rows); assert len(ids)==len(set(ids)); assert scrape.season_label(2018)=='2018-19'; print('players:', len(rows))"
```
Expected: `players: 267`

- [ ] **Step 3: Commit**

```bash
git add scrape.py
git commit -m "feat: add get_season_players with cursor pagination"
```

---

### Task 3: `write_season_csv()`

**Files:**
- Modify: `scrape.py` (add `write_season_csv` after `season_label`)

**Interfaces:**
- Consumes: leaderboard rows (Task 2 shape); `IDENTITY` constant from Task 1.
- Produces: `write_season_csv(path: str|Path, rows: list[dict], columns: list[str]) -> None` — writes a wide CSV: identity columns (`player_id`, `name`, `position`, `team`) then every stat column from `columns`; missing values are empty.

- [ ] **Step 1: Add the function**

```python
def write_season_csv(path, rows, columns):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for r in rows:
            meta = r.get("playerMetadata") or {}
            out = {
                "player_id": meta.get("id"),
                "name": meta.get("name"),
                "position": meta.get("position"),
                "team": (meta.get("currentTeam") or {}).get("name", ""),
            }
            out.update(r.get("stats") or {})
            writer.writerow(out)
```

- [ ] **Step 2: Verify the CSV round-trips**

Run:
```bash
python3 -c "
import scrape, csv
rows = scrape.get_season_players(2018)
keys = sorted({k for r in rows for k in r['stats']})
cols = scrape.IDENTITY + keys
scrape.write_season_csv('/tmp/players_2018-19.csv', rows, cols)
with open('/tmp/players_2018-19.csv') as f:
    rd = list(csv.DictReader(f))
assert len(rd) == len(rows), (len(rd), len(rows))
assert rd[0]['player_id'] and rd[0]['name']
assert set(cols) == set(rd[0].keys()), set(rd[0].keys()) ^ set(cols)
print('csv ok:', len(rd), 'rows,', len(cols), 'cols')
"
```
Expected: `csv ok: 267 rows, N cols`

- [ ] **Step 3: Commit**

```bash
git add scrape.py
git commit -m "feat: add write_season_csv"
```

---

### Task 4: `get_career_xg()` + `write_xg_csv()`

**Files:**
- Modify: `scrape.py` (add `get_career_xg`, `write_xg_csv` after `write_season_csv`)

**Interfaces:**
- Consumes: `fetch(url)`; `XG_FIELDS` from Task 1.
- Produces:
  - `get_career_xg(player_ids: iterable[str]) -> list[dict]` — for each unique id, GET `/api/v1/competitions/8/players/{id}/stats`, keep `player_id`, `name` (from `data.player.name`), and the 5 `XG_FIELDS` values; 0.1s sleep between requests.
  - `write_xg_csv(path, rows: list[dict]) -> None` — CSV with columns `player_id`, `name`, then `XG_FIELDS`.

- [ ] **Step 1: Add the two functions**

```python
def get_career_xg(player_ids):
    rows = []
    for pid in sorted(set(player_ids)):
        data = fetch(f"{API}/api/v1/competitions/8/players/{pid}/stats")
        stats = data.get("stats") or {}
        row = {"player_id": pid, "name": (data.get("player") or {}).get("name", "")}
        for field in XG_FIELDS:
            row[field] = stats.get(field)
        rows.append(row)
        time.sleep(0.1)
    return rows


def write_xg_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["player_id", "name"] + XG_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
```

- [ ] **Step 2: Verify xG values are numeric for known players**

Run:
```bash
python3 -c "
import scrape
rows = scrape.get_career_xg(['118748', '223094'])  # Salah, Haaland
assert len(rows) == 2
for r in rows:
    assert isinstance(r['expectedGoals'], (int, float)), r
scrape.write_xg_csv('/tmp/xg.csv', rows)
print('xg ok:', rows)
"
```
Expected: `xg ok: [{'player_id': '118748', ... 'expectedGoals': 182.4536, ...}, ...]`

- [ ] **Step 3: Commit**

```bash
git add scrape.py
git commit -m "feat: add career xG fetch and CSV writer"
```

---

### Task 5: `main()` CLI + resume + `--self-test`

**Files:**
- Modify: `scrape.py` (add `run_self_test` and `main`; add the `if __name__` guard)

**Interfaces:**
- Consumes: all functions from Tasks 1–4.
- Produces:
  - `run_self_test() -> None` — assert-based checks over all 8 seasons + one career-xG call; prints `self-test: OK` and returns.
  - `main() -> int` — argparse CLI:
    - `--from <int>` default `2018`, `--to <int>` default `2025`
    - `--out <dir>` default `data`
    - `--no-xg` (skip career xG pass)
    - `--force` (overwrite existing season files)
    - `--self-test` (run `run_self_test()` and exit 0)

- [ ] **Step 1: Add `run_self_test` and `main`**

```python
def run_self_test():
    for season in range(2018, 2026):
        rows = get_season_players(season)
        assert len(rows) >= 250, f"season {season}: only {len(rows)} players"
        ids = [r["playerMetadata"]["id"] for r in rows]
        assert len(ids) == len(set(ids)), f"season {season}: duplicate player ids"
        keys = {k for r in rows for k in (r.get("stats") or {})}
        assert 50 <= len(keys) <= 150, f"season {season}: {len(keys)} stat keys"
        if season == 2018:
            top = max((r["stats"].get("goals") or 0) for r in rows)
            assert top == 22.0, f"2018/19 top scorer has {top} goals, expected 22"
    data = fetch(f"{API}/api/v1/competitions/8/players/118748/stats")
    xg = (data.get("stats") or {}).get("expectedGoals")
    assert isinstance(xg, (int, float)), "career xG is not numeric"
    print("self-test: OK")


def main():
    parser = argparse.ArgumentParser(description="Scrape PL player stats from the official API")
    parser.add_argument("--from", dest="year_from", type=int, default=2018)
    parser.add_argument("--to", dest="year_to", type=int, default=2025)
    parser.add_argument("--out", default="data")
    parser.add_argument("--no-xg", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        return 0

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    fetched = {}
    all_ids = set()
    for season in range(args.year_from, args.year_to + 1):
        path = out_dir / f"players_{season_label(season)}.csv"
        if path.exists() and not args.force:
            print(f"skip {path} (already exists; use --force to re-scrape)")
            continue
        rows = get_season_players(season)
        fetched[season] = rows
        for r in rows:
            meta = r.get("playerMetadata") or {}
            if meta.get("id"):
                all_ids.add(meta["id"])

    if not fetched:
        print("nothing to scrape")
        return 0

    stat_keys = sorted({k for rows in fetched.values() for r in rows for k in (r.get("stats") or {})})
    columns = IDENTITY + stat_keys
    for season, rows in fetched.items():
        path = out_dir / f"players_{season_label(season)}.csv"
        write_season_csv(path, rows, columns)
        print(f"wrote {path} ({len(rows)} players)")

    if not args.no_xg and all_ids:
        xg_rows = get_career_xg(all_ids)
        write_xg_csv(out_dir / "players_career_xg.csv", xg_rows)
        print(f"wrote {out_dir / 'players_career_xg.csv'} ({len(xg_rows)} players)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run `--self-test` (hits all 8 seasons + 1 xG call, ~30 requests, ~30s)**

Run: `python3 scrape.py --self-test`
Expected: `self-test: OK`

- [ ] **Step 3: Verify a small real scrape + resume behavior**

Run:
```bash
python3 scrape.py --from 2024 --to 2025 --no-xg --out /tmp/pl
python3 scrape.py --from 2024 --to 2025 --no-xg --out /tmp/pl
```
Expected: first run prints two `wrote ...` lines; second run prints two `skip ...` lines. Then:
```bash
python3 -c "
import csv
rows = list(csv.DictReader(open('/tmp/pl/players_2024-25.csv')))
assert len(rows) >= 250, len(rows)
assert len({r['player_id'] for r in rows}) == len(rows)
assert 'goals' in rows[0] and 'goalAssists' in rows[0] and 'cleanSheets' in rows[0]
print('real scrape ok:', len(rows), 'players')
"
```
Expected: `real scrape ok: N players`

- [ ] **Step 4: Full run (8 seasons + career xG, ~1,500 requests, ~10–15 min)**

Run: `python3 scrape.py`
Expected: 8 `wrote data/players_YYYY-YY.csv` lines + `wrote data/players_career_xg.csv (N players)`. Then:
```bash
python3 -c "
import csv
for s in range(2018, 2026):
    path = f'data/players_{s}-{str(s+1)[-2:]}.csv'
    rows = list(csv.DictReader(open(path)))
    assert len(rows) >= 250, (path, len(rows))
    assert len({r['player_id'] for r in rows}) == len(rows), path
    assert set(('player_id','name','position','team','goals','goalAssists')) <= set(rows[0]), path
print('all seasons ok')
"
```
Expected: `all seasons ok`

- [ ] **Step 5: Commit**

```bash
git add scrape.py
git commit -m "feat: add CLI, resume-skip, and self-test"
```

---

### Task 6: Final review

**Files:**
- None (review only).

- [ ] **Step 1: Self-review the diff**

Run: `git log --oneline -5` and `git status`. Confirm 6 commits exist (`.gitignore`, `fetch`, pagination, csv, xg, CLI) and `data/` is untracked (gitignored).

- [ ] **Step 2: Run the self-test once more to confirm end state**

Run: `python3 scrape.py --self-test`
Expected: `self-test: OK`
