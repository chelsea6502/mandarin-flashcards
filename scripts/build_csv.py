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
    """Merge two entry lists into a dict keyed by simplified.

    Prefers new_entries data. Words in both get source 'old-HSK5, new-HSK3'.
    """
    merged = {}
    for entry in new_entries:
        merged[entry["simplified"]] = {"entry": entry, "source": "new-HSK3"}
    for entry in old_entries:
        key = entry["simplified"]
        if key in merged:
            merged[key]["source"] = "old-HSK5, new-HSK3"
        else:
            merged[key] = {"entry": entry, "source": "old-HSK5"}
    return merged


def to_rows(merged: dict) -> list:
    """Expand merged entries into one row dict per definition."""
    rows = []
    for simplified, item in merged.items():
        entry = item["entry"]
        source = item["source"]
        pos = ", ".join(entry.get("pos", []))
        for form in entry.get("forms", []):
            pinyin = form.get("transcriptions", {}).get("pinyin", "")
            traditional = form.get("traditional", "")
            classifier = ", ".join(form.get("classifiers", []))
            for meaning in form.get("meanings", []):
                rows.append({
                    "simplified": simplified,
                    "pinyin": pinyin,
                    "traditional": traditional,
                    "pos": pos,
                    "classifier": classifier,
                    "definition": meaning,
                    "source": source,
                })
    return rows


FIELDNAMES = ["simplified", "pinyin", "traditional", "pos", "classifier", "definition", "source"]


def write_csv(rows: list, output_path) -> None:
    """Write rows to a CSV file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
