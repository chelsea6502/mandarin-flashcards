#!/usr/bin/env python3
"""Fetch grammar points from chinesetest.cn and save to data/grammar_source.json."""

import json
import sys
import urllib.request
from pathlib import Path

API_URL = (
    "https://www.chinesetest.cn/api/hsk/outline/languagePage"
    "?examLevelId=&leveId1=&leveId2=&leveId3=&content=&current=1&size=1000"
)

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_PATH = REPO_ROOT / "data" / "grammar_source.json"


def fetch_grammar_points(url: str) -> list:
    """Fetch all grammar points from the API and return the records list."""
    req = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["data"]["records"]


def write_json(records: list, output_path) -> None:
    """Write records to a JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def main() -> None:
    print("Fetching grammar points...", flush=True)
    records = fetch_grammar_points(API_URL)
    write_json(records, OUTPUT_PATH)
    print(f"Wrote {len(records)} records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
