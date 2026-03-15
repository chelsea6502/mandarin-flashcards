#!/usr/bin/env python3
"""Fetch vocabulary and Chinese character data from chinesetest.cn syllabus API."""

import json
import sys
import urllib.request
from pathlib import Path

BASE_URL = "https://www.chinesetest.cn/api/hsk/outline"

VOCAB_URL = f"{BASE_URL}/glossaryPage?examLevelId=&type=1&content=&pinyin=&cixing=&current=1&size=20000"
HANZI_URL = f"{BASE_URL}/hanziPage?type=&examLevelId=&content=&current=1&size=20000"

REPO_ROOT = Path(__file__).parent.parent


def fetch_records(url: str) -> list:
    req = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["data"]["records"]


def write_json(records: list, output_path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def main() -> None:
    print("Fetching vocabulary...", flush=True)
    vocab = fetch_records(VOCAB_URL)
    write_json(vocab, REPO_ROOT / "data" / "vocabulary_source.json")
    print(f"Wrote {len(vocab)} vocabulary records")

    print("Fetching Chinese characters...", flush=True)
    hanzi = fetch_records(HANZI_URL)
    write_json(hanzi, REPO_ROOT / "data" / "hanzi_source.json")
    print(f"Wrote {len(hanzi)} Chinese character records")


if __name__ == "__main__":
    main()
