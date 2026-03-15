#!/usr/bin/env python3
"""Build data/words.xlsx from HSK JSON word lists."""

import json
import sys
import urllib.request
from pathlib import Path

import openpyxl

BASE = "https://raw.githubusercontent.com/drkameleon/complete-hsk-vocabulary/refs/heads/main/wordlists/exclusive"
OLD_HSK_URLS = {i: f"{BASE}/old/{i}.json" for i in range(1, 6)}
NEW_HSK_URLS = {i: f"{BASE}/new/{i}.json" for i in range(1, 4)}

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_PATH = REPO_ROOT / "data" / "words.xlsx"


POS_MAP = {
    "n":  "noun",
    "nr": "proper noun (person)",
    "ns": "proper noun (place)",
    "nt": "proper noun (organization)",
    "nz": "proper noun (other)",
    "an": "adjective-noun",
    "vn": "verbal noun",
    "v":  "verb",
    "a":  "adjective",
    "ad": "adverbial adjective",
    "b":  "non-predicate adjective",
    "d":  "adverb",
    "p":  "preposition",
    "c":  "conjunction",
    "cc": "coordinating conjunction",
    "m":  "numeral",
    "Mg": "numeral morpheme",
    "mq": "numeral-classifier",
    "q":  "classifier",
    "qt": "time classifier",
    "qv": "verbal classifier",
    "r":  "pronoun",
    "u":  "particle",
    "y":  "modal particle",
    "e":  "interjection",
    "o":  "onomatopoeia",
    "f":  "directional word",
    "s":  "place word",
    "t":  "time word",
    "tg": "time morpheme",
    "g":  "morpheme",
    "h":  "prefix",
    "k":  "suffix",
    "l":  "set phrase",
    "z":  "state word",
}


def expand_pos(tags: list) -> str:
    return ", ".join(POS_MAP.get(tag, tag) for tag in tags)


def fetch_json(url: str) -> list:
    """Fetch a URL and return the parsed JSON array."""
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def load_level_entries(level_urls: dict) -> dict:
    """Fetch exclusive level files and return dict: simplified -> (entry, level)."""
    result = {}
    for level, url in sorted(level_urls.items()):
        for entry in fetch_json(url):
            word = entry["simplified"]
            if word not in result:
                result[word] = (entry, level)
    return result


def merge_entries(new_by_word: dict, old_by_word: dict) -> dict:
    """Merge level-annotated dicts, preferring new HSK data.

    Returns dict: simplified -> {"entry": ..., "source": "old-HSK L3, new-HSK L1"}
    """
    merged = {}
    for word, (entry, level) in new_by_word.items():
        merged[word] = {"entry": entry, "source": f"new-HSK L{level}"}
    for word, (entry, level) in old_by_word.items():
        if word in merged:
            merged[word]["source"] = f"old-HSK L{level}, " + merged[word]["source"]
        else:
            merged[word] = {"entry": entry, "source": f"old-HSK L{level}"}
    return merged


def to_rows(merged: dict) -> list:
    """Expand merged entries into one row dict per definition."""
    rows = []
    for simplified, item in merged.items():
        entry = item["entry"]
        source = item["source"]
        pos = expand_pos(entry.get("pos", []))
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


MERGE_COLS = ["simplified", "pinyin", "traditional", "pos", "classifier", "source"]
# Columns to merge across rows of the same word (definition column stays separate)


def write_xlsx(rows: list, output_path) -> None:
    """Write rows to an XLSX file, merging non-definition cells for same-word rows."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(FIELDNAMES)

    # Group consecutive rows by simplified character
    col_index = {name: i + 1 for i, name in enumerate(FIELDNAMES)}
    excel_row = 2
    i = 0
    while i < len(rows):
        word = rows[i]["simplified"]
        group_start = excel_row
        # Find all consecutive rows with the same simplified character
        j = i
        while j < len(rows) and rows[j]["simplified"] == word:
            ws.append([rows[j][f] for f in FIELDNAMES])
            excel_row += 1
            j += 1
        group_end = excel_row - 1
        # Merge non-definition columns if the word spans multiple rows
        if group_end > group_start:
            for col_name in MERGE_COLS:
                c = col_index[col_name]
                ws.merge_cells(
                    start_row=group_start, start_column=c,
                    end_row=group_end, end_column=c
                )
        i = j

    wb.save(output_path)


def main() -> None:
    print("Fetching old HSK L1-5...", flush=True)
    old_by_word = load_level_entries(OLD_HSK_URLS)
    print("Fetching new HSK L1-3...", flush=True)
    new_by_word = load_level_entries(NEW_HSK_URLS)
    merged = merge_entries(new_by_word, old_by_word)
    rows = to_rows(merged)
    write_xlsx(rows, OUTPUT_PATH)
    print(f"Wrote {len(rows)} rows ({len(merged)} words) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
