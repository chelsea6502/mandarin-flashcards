import json
import sys
from pathlib import Path

import openpyxl


COLUMNS = [
    "hsk_level", "grammar_type", "category_type", "grammar_detail", "content",
    "description",
    "sentence_1", "translation_1",
    "sentence_2", "translation_2",
    "sentence_3", "translation_3",
]

REPO_ROOT = Path(__file__).parent.parent
SOURCE_PATH = REPO_ROOT / "data" / "grammar_source.json"
OUTPUT_PATH = REPO_ROOT / "data" / "grammar.xlsx"

LEVEL_MAP = {
    "HSK1": "L1",
    "HSK2": "L2",
    "HSK3": "L3",
    "HSK4": "L4",
    "HSK5": "L5",
    "HSK6": "L6",
    "HSK7-9": "L7-9",
}


def parse_grammar_points(records: list) -> list:
    rows = []
    for r in records:
        sentences = [s.strip() for s in r.get("cases", "").split("\r\n") if s.strip()]
        sentences = (sentences + ["", "", ""])[:3]
        rows.append({
            "hsk_level": LEVEL_MAP.get(r["examLevelId"], r["examLevelId"]),
            "grammar_type": r.get("grammarType", ""),
            "category_type": r.get("categoryType", ""),
            "grammar_detail": r.get("grammarDetail", ""),
            "content": r.get("content", ""),
            "description": "",
            "sentence_1": sentences[0],
            "translation_1": "",
            "sentence_2": sentences[1],
            "translation_2": "",
            "sentence_3": sentences[2],
            "translation_3": "",
        })
    return rows


def write_xlsx(rows: list, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(COLUMNS)
    for row in rows:
        ws.append([row.get(col) or None for col in COLUMNS])
    wb.save(path)


def main():
    if not SOURCE_PATH.exists():
        print(f"Error: {SOURCE_PATH} not found. Run scripts/fetch_grammar.py first.", file=sys.stderr)
        sys.exit(1)
    records = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    rows = parse_grammar_points(records)
    write_xlsx(rows, OUTPUT_PATH)
    print(f"Wrote {len(rows)} grammar points to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
