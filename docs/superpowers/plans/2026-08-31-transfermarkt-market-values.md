# Transfermarkt Market Values Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `scrape_market_values.py`, a Playwright-based scraper that collects Premier League players' Transfermarkt market values (2018–2026) after a one-time human captcha solve, and writes a standalone CSV.

**Architecture:** A single script. Pure parser functions (`parse_value`, `parse_date`, `parse_leaderboard`, `parse_timeline`) are network-free and fully unit-testable via `--self-test` against embedded fixtures. A Playwright layer (`solve_captcha`, `fetch_text`) opens a real headed browser, waits for the user to solve the AWS WAF captcha, then reuses the session cookies (via `context.request`) to fetch the league leaderboard and every player's value-history page without re-rendering. `main()` orchestrates, writes incrementally, and resumes.

**Tech Stack:** Python 3, Playwright (already installed in the environment), stdlib only otherwise (`re`, `csv`, `argparse`, `time`, `pathlib`, `datetime`). No test framework — assertions run via `python3 scrape_market_values.py --self-test` and `python3 -c` checks.

## Global Constraints

- Playwright is a permitted dependency (required for the captcha). Everything else is Python stdlib only.
- transfermarkt.com serves an AWS WAF captcha ("Human Verification" page) — automated requests are blocked. The script MUST open a headed browser and wait for a human to solve the captcha before scraping.
- Leaderboard URL constant: `https://www.transfermarkt.com/premier-league/marktwerte/wettbewerb/GB1/ausrichtung//spielerposition_id//altersklasse//land_id/0/only_loans//plus/1`
- Value history URL per player: `https://www.transfermarkt.com/{slug}/marktwerteverlauf/spieler/{playerId}`
- Only timeline events with date year in `[from_year, to_year]` (default 2018–2026) are written.
- Output CSV: `data/transfermarkt_market_values.csv` with header `player_id,player_name,club,date,market_value_eur`. One row per value-change event. Writes incrementally per player; existing players are skipped on rerun unless `--force`.
- Value parsing: `€180.00m` → `180000000`, `€25m` → `25000000`, `€500k` → `500000`, full `€1,800,000` → `1800000`. Dates `30.06.2025` → `2025-06-30`.
- `--self-test` must run without any network access or captcha.

---

### Task 1: Value and date parsing

**Files:**
- Create: `scrape_market_values.py` (module header, imports, `parse_value`, `parse_date`)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `parse_value(token: str) -> int | None` — parse a Transfermarkt value token into integer euros.
  - `parse_date(token: str) -> str | None` — parse a date token into `YYYY-MM-DD`.
  - `run_self_test()` — will grow across tasks; for now asserts the value/date parsers.

- [ ] **Step 1: Create `scrape_market_values.py` with imports, `parse_value`, `parse_date`, and `run_self_test`**

```python
#!/usr/bin/env python3
"""Scrape Premier League player market values from transfermarkt.com.

Requires one human captcha solve in a real browser (transfermarkt is behind an
AWS WAF captcha); afterwards it scrapes the value history (2018-2026) for all
PL players into a CSV.
"""
import argparse
import csv
import re
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

DEFAULT_URL = ("https://www.transfermarkt.com/premier-league/marktwerte/wettbewerb/GB1/"
               "ausrichtung//spielerposition_id//altersklasse//land_id/0/only_loans//plus/1")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")


def parse_value(token):
    m = re.search(r"([\d.,]+)\s*([kmb])?", (token or "").replace("€", "").strip(), re.I)
    if not m:
        return None
    num_str, suffix = m.group(1), (m.group(2) or "").lower()
    if suffix:
        num = float(num_str.replace(",", "."))
    else:
        num = float(num_str.replace(",", ""))
    factor = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(suffix, 1)
    return int(round(num * factor))


def parse_date(token):
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%b %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime((token or "").strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def run_self_test():
    assert parse_value("€180.00m") == 180_000_000
    assert parse_value("€25m") == 25_000_000
    assert parse_value("€500k") == 500_000
    assert parse_value("€1,800,000") == 1_800_000
    assert parse_value("-") is None
    assert parse_value("") is None
    assert parse_date("30.06.2025") == "2025-06-30"
    assert parse_date("2025-06-30") == "2025-06-30"
    assert parse_date("not a date") is None
    print("self-test: OK")


if __name__ == "__main__":
    run_self_test()
```

- [ ] **Step 2: Run the self-test**

Run: `python3 scrape_market_values.py --self-test`
Expected: `self-test: OK`

- [ ] **Step 3: Commit**

```bash
git add scrape_market_values.py
git commit -m "feat: add value and date parsers for transfermarkt"
```

---

### Task 2: Leaderboard parser

**Files:**
- Modify: `scrape_market_values.py` (add `parse_leaderboard`, extend `run_self_test`)

**Interfaces:**
- Consumes: `parse_value` from Task 1.
- Produces: `parse_leaderboard(html: str) -> list[dict]` — each dict has keys `player_id` (int), `slug` (str), `name` (str), `club` (str), `current_value_eur` (int|None). Player link pattern: `href="/{slug}/profil/spieler/{id}"`.

- [ ] **Step 1: Add `parse_leaderboard` and its fixture, extend `run_self_test`**

```python
LEADERBOARD_FIXTURE = """<table class="items">
<tr class="odd">
<td class="hauptlink"><a href="/erling-haaland/profil/spieler/819840">Erling Haaland</a></td>
<td class="zentriert">24</td>
<td class="rechts hauptlink"><a href="#">€180.00m</a></td>
<td class="zentriert"><a href="/manchester-city/startseite/verein/281">Manchester City</a></td>
</tr>
<tr class="even">
<td class="hauptlink"><a href="/mohamed-salah/profil/spieler/148296">Mohamed Salah</a></td>
<td class="zentriert">33</td>
<td class="rechts hauptlink"><a href="#">€55.00m</a></td>
<td class="zentriert"><a href="/liverpool/startseite/verein/31">Liverpool</a></td>
</tr>
</table>"""


def parse_leaderboard(html):
    players = []
    for row in re.split(r"<tr[^>]*>", html):
        m = re.search(r'href="/([^"]*?)/profil/spieler/(\d+)"[^>]*>([^<]*)</a>', row)
        if not m:
            continue
        value = None
        vm = re.search(r"€\s*([\d.,]+(?:[kmb])?)", row, re.I)
        if vm:
            value = parse_value(vm.group(1))
        club = ""
        cm = re.search(r'/startseite/verein/\d+"[^>]*>([^<]+)</a>', row)
        if cm:
            club = cm.group(1).strip()
        players.append({
            "player_id": int(m.group(2)),
            "slug": m.group(1),
            "name": m.group(3).strip(),
            "club": club,
            "current_value_eur": value,
        })
    return players
```

In `run_self_test()`, replace the final `print("self-test: OK")` with:

```python
    lb = parse_leaderboard(LEADERBOARD_FIXTURE)
    assert len(lb) == 2
    assert lb[0]["player_id"] == 819840
    assert lb[0]["slug"] == "erling-haaland"
    assert lb[0]["name"] == "Erling Haaland"
    assert lb[0]["club"] == "Manchester City"
    assert lb[0]["current_value_eur"] == 180_000_000
    assert lb[1]["name"] == "Mohamed Salah"
    print("self-test: OK")
```

- [ ] **Step 2: Run the self-test**

Run: `python3 scrape_market_values.py --self-test`
Expected: `self-test: OK`

- [ ] **Step 3: Commit**

```bash
git add scrape_market_values.py
git commit -m "feat: add transfermarkt leaderboard parser"
```

---

### Task 3: Timeline parser

**Files:**
- Modify: `scrape_market_values.py` (add `parse_timeline`, extend `run_self_test`)

**Interfaces:**
- Consumes: `parse_value`, `parse_date` from Task 1.
- Produces: `parse_timeline(html: str) -> list[dict]` — each dict has keys `date` (str `YYYY-MM-DD`) and `value_eur` (int). Primary path: rows containing both a `dd.mm.yyyy` date and a `€` value token. Fallback path (when no such rows): whole-page scan for a date followed within 150 chars by a value token.

- [ ] **Step 1: Add `parse_timeline` and its fixture, extend `run_self_test`**

```python
TIMELINE_FIXTURE = """<table id="yw1">
<tr><th>Date</th><th>Market value</th><th>Age</th></tr>
<tr><td>30.06.2025</td><td class="rechts hauptlink">€180.00m</td><td>24</td></tr>
<tr><td>10.06.2024</td><td class="rechts hauptlink">€200.00m</td><td>23</td></tr>
</table>"""

TIMELINE_FIXTURE_FALLBACK = """<div class="row">
<span class="date">15.06.2024</span>
<span class="mw">€150.00m</span>
</div>"""


def parse_timeline(html):
    events = []
    for row in re.split(r"<tr[^>]*>", html):
        dm = re.search(r"\d{1,2}\.\d{1,2}\.\d{4}", row)
        vm = re.search(r"€\s*([\d.,]+(?:[kmb])?)", row, re.I)
        if dm and vm:
            date = parse_date(dm.group(0))
            value = parse_value(vm.group(1))
            if date and value is not None:
                events.append({"date": date, "value_eur": value})
    if not events:
        for m in re.finditer(r"(\d{1,2})\.(\d{1,2})\.(\d{4}).{0,150}?€\s*([\d.,]+(?:[kmb])?)",
                             html, re.I | re.S):
            date = parse_date(f"{m.group(1)}.{m.group(2)}.{m.group(3)}")
            value = parse_value(m.group(4))
            if date and value is not None:
                events.append({"date": date, "value_eur": value})
    return events
```

In `run_self_test()`, replace the final `print("self-test: OK")` with:

```python
    tl = parse_timeline(TIMELINE_FIXTURE)
    assert len(tl) == 2
    assert tl[0] == {"date": "2025-06-30", "value_eur": 180_000_000}
    assert tl[1] == {"date": "2024-06-10", "value_eur": 200_000_000}
    tl2 = parse_timeline(TIMELINE_FIXTURE_FALLBACK)
    assert tl2 == [{"date": "2024-06-15", "value_eur": 150_000_000}]
    print("self-test: OK")
```

- [ ] **Step 2: Run the self-test**

Run: `python3 scrape_market_values.py --self-test`
Expected: `self-test: OK`

- [ ] **Step 3: Commit**

```bash
git add scrape_market_values.py
git commit -m "feat: add transfermarkt value-history timeline parser"
```

---

### Task 4: Browser session + captcha handling

**Files:**
- Modify: `scrape_market_values.py` (add `solve_captcha`, `fetch_text`, `total_pages`; move the `if __name__` block to call `main()`)

**Interfaces:**
- Consumes: `DEFAULT_URL`, `UA` from Task 1.
- Produces:
  - `solve_captcha(page, url: str, timeout_min: int) -> None` — navigates to `url`; if the "Human Verification" page appears, prints a prompt and polls every 2s until the real page loads (contains `profil/spieler`); raises `TimeoutError` after `timeout_min` minutes.
  - `fetch_text(context, url: str, retries: int = 3) -> str` — GETs `url` via the browser context's request API (reuses session cookies), retries with backoff, raises `RuntimeError` if the WAF challenge returns or all retries fail.
  - `total_pages(html: str) -> int` — max `?page=N` seen in pagination links; 1 if none.
  - `main()` — for now: parse `--self-test` only, otherwise launch headed browser, call `solve_captcha`, print `captcha cleared`, close. Real orchestration lands in Task 5.

- [ ] **Step 1: Add the functions and a stub `main()`**

```python
def solve_captcha(page, url, timeout_min):
    print("Opening:", url)
    print("If a 'Human Verification' page appears, solve the captcha in the opened browser window.")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    deadline = time.monotonic() + timeout_min * 60
    while time.monotonic() < deadline:
        try:
            content = page.content()
        except Exception:
            time.sleep(2)
            continue
        if "Human Verification" not in content and "profil/spieler" in content:
            print("Captcha cleared.")
            return
        time.sleep(2)
    raise TimeoutError(f"captcha not solved within {timeout_min} minutes")


def fetch_text(context, url, retries=3):
    last = None
    for attempt in range(retries):
        resp = context.request.get(url)
        if resp.ok:
            text = resp.text()
            if "Human Verification" in text:
                raise RuntimeError("WAF challenge returned; session cookies no longer valid")
            return text
        last = resp.status
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url} (status {last})")


def total_pages(html):
    pages = [int(p) for p in re.findall(r"[?&]page=(\d+)", html)]
    return max(pages) if pages else 1


def main():
    parser = argparse.ArgumentParser(description="Scrape PL player market values from transfermarkt")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--timeout-min", type=int, default=10)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        run_self_test()
        return 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent=UA, locale="en-US")
        page = context.new_page()
        solve_captcha(page, args.url, args.timeout_min)
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Verify captcha detection + timeout path (no solving needed)**

Run:
```bash
python3 -c "
import scrape_market_values as s
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page()
    try:
        s.solve_captcha(pg, s.DEFAULT_URL, timeout_min=0.05)
        print('UNEXPECTED: no timeout')
    except TimeoutError:
        print('captcha detection + timeout path works')
    b.close()
"
```
Expected: the prompt prints, then `captcha detection + timeout path works`.

Also confirm `python3 scrape_market_values.py --self-test` still prints `self-test: OK`.

- [ ] **Step 3: Commit**

```bash
git add scrape_market_values.py
git commit -m "feat: add browser captcha handling and fetch helpers"
```

---

### Task 5: Orchestration + CLI + incremental CSV

**Files:**
- Modify: `scrape_market_values.py` (full `main()` with leaderboard + timeline scraping, resume, CSV writing; extend CLI flags)

**Interfaces:**
- Consumes: `solve_captcha`, `fetch_text`, `total_pages` (Task 4); `parse_leaderboard` (Task 2); `parse_timeline` (Task 3); `parse_value`/`parse_date` (Task 1).
- Produces: `main() -> int` — full CLI:
  - `--url` (default `DEFAULT_URL`), `--from-year` (default 2018), `--to-year` (default 2026), `--out` (default `data/transfermarkt_market_values.csv`), `--timeout-min` (default 10), `--force`, `--self-test`.
  - Behavior: self-test early return; else open headed browser, solve captcha, fetch all leaderboard pages, collect players, skip ones already in the output CSV (unless `--force`), and for each remaining player fetch their `marktwerteverlauf` page, parse events, keep those within `[from_year, to_year]`, and append rows to the CSV immediately. Prints progress every 50 players.

- [ ] **Step 1: Replace `main()` with the full orchestration**

```python
def main():
    parser = argparse.ArgumentParser(description="Scrape PL player market values from transfermarkt")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--from-year", type=int, default=2018)
    parser.add_argument("--to-year", type=int, default=2026)
    parser.add_argument("--out", default="data/transfermarkt_market_values.csv")
    parser.add_argument("--timeout-min", type=int, default=10)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        return 0

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    done_ids = set()
    if out_path.exists() and not args.force:
        with open(out_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                done_ids.add(row["player_id"])
        print(f"resume: {len(done_ids)} players already in {out_path}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent=UA, locale="en-US")
        page = context.new_page()
        solve_captcha(page, args.url, args.timeout_min)

        lb_html = fetch_text(context, args.url)
        players = parse_leaderboard(lb_html)
        for pageno in range(2, total_pages(lb_html) + 1):
            players.extend(parse_leaderboard(fetch_text(context, f"{args.url}?page={pageno}")))
        seen = {}
        for pl in players:
            seen.setdefault(pl["player_id"], pl)
        players = [pl for pl in seen.values() if str(pl["player_id"]) not in done_ids]
        print(f"scraping value history for {len(players)} players")

        new_file = not out_path.exists()
        with open(out_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["player_id", "player_name", "club", "date", "market_value_eur"])
            if new_file:
                writer.writeheader()
            for i, pl in enumerate(players, 1):
                try:
                    turl = f"https://www.transfermarkt.com/{pl['slug']}/marktwerteverlauf/spieler/{pl['player_id']}"
                    html = fetch_text(context, turl)
                    events = parse_timeline(html)
                    for ev in events:
                        year = int(ev["date"][:4])
                        if args.from_year <= year <= args.to_year:
                            writer.writerow({
                                "player_id": pl["player_id"],
                                "player_name": pl["name"],
                                "club": pl["club"],
                                "date": ev["date"],
                                "market_value_eur": ev["value_eur"],
                            })
                except RuntimeError as e:
                    print(f"  skipping {pl['name']} (id {pl['player_id']}): {e}")
                f.flush()
                if i % 50 == 0:
                    print(f"  {i}/{len(players)} players done")
        browser.close()

    print(f"done -> {out_path}")
    return 0
```

- [ ] **Step 2: Verify `--self-test` still passes**

Run: `python3 scrape_market_values.py --self-test`
Expected: `self-test: OK`

- [ ] **Step 3: Verify resume logic parses existing CSV ids**

Run:
```bash
python3 -c "
import csv, pathlib
path = pathlib.Path('/tmp/resume_check.csv')
path.write_text('player_id,player_name,club,date,market_value_eur\n819840,Erling Haaland,Manchester City,2025-06-30,180000000\n')
done = {r['player_id'] for r in csv.DictReader(open(path))}
assert done == {'819840'}
print('resume parse ok')
"
```
Expected: `resume parse ok`

- [ ] **Step 4: Commit**

```bash
git add scrape_market_values.py
git commit -m "feat: orchestrate leaderboard + timeline scraping with resume"
```

---

### Task 6: Live interactive run (human-assisted) + final review

**Files:**
- None (the code is complete; this task is a live acceptance run).

- [ ] **Step 1: Run the scraper interactively (requires you to solve the captcha once)**

Run: `python3 scrape_market_values.py`

You will see a headed Chromium window open. If a "Human Verification" page appears, solve the captcha in that window. The scraper then fetches the league leaderboard, prints `scraping value history for N players`, and fetches each player's value history (~15–30 min for ~900 players).

Expected end state:
```
scraping value history for N players
  ...
done -> data/transfermarkt_market_values.csv
```

- [ ] **Step 2: Verify the output CSV**

Run:
```bash
python3 -c "
import csv
rows = list(csv.DictReader(open('data/transfermarkt_market_values.csv')))
assert len(rows) > 1000, len(rows)
import datetime
years = {r['date'][:4] for r in rows}
assert years <= {'2018','2019','2020','2021','2022','2023','2024','2025','2026'}, years
assert all(int(r['market_value_eur']) > 0 for r in rows[:500])
players = {r['player_id'] for r in rows}
print('rows:', len(rows), 'players:', len(players), 'years:', sorted(years))
"
```
Expected: `rows: N, players: M, years: [...]` with N > 1000 and M ≈ the player count.

- [ ] **Step 3: Run `--self-test` once more to confirm end state**

Run: `python3 scrape_market_values.py --self-test`
Expected: `self-test: OK`

- [ ] **Step 4: Final review**

Run: `git log --oneline -6` and `git status`. Confirm 5 commits exist and `data/` is untracked (gitignored).
