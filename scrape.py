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

    if not args.no_xg and all_ids and (not (out_dir / "players_career_xg.csv").exists() or args.force):
        xg_rows = get_career_xg(all_ids)
        write_xg_csv(out_dir / "players_career_xg.csv", xg_rows)
        print(f"wrote {out_dir / 'players_career_xg.csv'} ({len(xg_rows)} players)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
