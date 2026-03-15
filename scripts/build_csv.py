#!/usr/bin/env python3
"""Build data/words.csv from HSK JSON word lists."""

import csv
import json
import sys
import urllib.request
from pathlib import Path

OLD_HSK5_URL = "https://raw.githubusercontent.com/drkameleon/complete-hsk-vocabulary/refs/heads/main/wordlists/exclusive/old/5.json"
NEW_HSK3_URL = "https://raw.githubusercontent.com/drkameleon/complete-hsk-vocabulary/refs/heads/main/wordlists/exclusive/new/3.json"

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_PATH = REPO_ROOT / "data" / "words.csv"


def fetch_json(url: str) -> list:
    """Fetch a URL and return the parsed JSON array."""
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def merge_entries(new_entries: list, old_entries: list) -> dict:
    raise NotImplementedError


def to_rows(merged: dict) -> list:
    raise NotImplementedError


def write_csv(rows: list, output_path) -> None:
    raise NotImplementedError
