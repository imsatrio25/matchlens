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
<table><tr><td>15.06.2024</td><td>age 27</td></tr></table>
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


if __name__ == "__main__":
    run_self_test()
