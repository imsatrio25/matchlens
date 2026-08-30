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
