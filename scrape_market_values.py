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
