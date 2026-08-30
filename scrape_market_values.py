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


TIMELINE_FIXTURE = """<table id="yw1">
<tr><th>Date</th><th>Market value</th><th>Age</th></tr>
<tr><td>30.06.2025</td><td class="rechts hauptlink">€180.00m</td><td>24</td></tr>
<tr><td>10.06.2024</td><td class="rechts hauptlink">€200.00m</td><td>23</td></tr>
</table>"""

TIMELINE_FIXTURE_FALLBACK = """<div class="row">
15.06.2024
<table><tr><td>age 27</td></tr></table>
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
    lb = parse_leaderboard(LEADERBOARD_FIXTURE)
    assert len(lb) == 2
    assert lb[0]["player_id"] == 819840
    assert lb[0]["slug"] == "erling-haaland"
    assert lb[0]["name"] == "Erling Haaland"
    assert lb[0]["club"] == "Manchester City"
    assert lb[0]["current_value_eur"] == 180_000_000
    assert lb[1]["name"] == "Mohamed Salah"
    tl = parse_timeline(TIMELINE_FIXTURE)
    assert len(tl) == 2
    assert tl[0] == {"date": "2025-06-30", "value_eur": 180_000_000}
    assert tl[1] == {"date": "2024-06-10", "value_eur": 200_000_000}
    tl2 = parse_timeline(TIMELINE_FIXTURE_FALLBACK)
    assert tl2 == [{"date": "2024-06-15", "value_eur": 150_000_000}]
    print("self-test: OK")


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
        try:
            resp = context.request.get(url)
        except Exception as e:
            last = e
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f"failed to fetch {url}: {e}") from e
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


if __name__ == "__main__":
    raise SystemExit(main())
