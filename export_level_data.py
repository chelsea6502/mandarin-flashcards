#!/usr/bin/env python3
"""
Export flashcard rows by HSK level to data/level_data/L{n}.json.

Run this once before dispatching audit agents so they can read level data
from the project directory (agents cannot access /tmp).

Usage:
    python3 scripts/export_level_data.py            # exports all levels
    python3 scripts/export_level_data.py 1 2        # exports L1 and L2 only

Output files:
    data/level_data/L1.json   — all L1 rows (300 rows)
    data/level_data/L2.json   — all L2 rows (197 rows)
    ...
    data/level_data/vocab_upto_L1.json  — vocabulary valid for L1 sentences
    data/level_data/vocab_upto_L2.json  — vocabulary valid for L1+L2 sentences
    ...

Row format (JSON array of objects):
    {
        "row": <xlsx row number, 1-indexed>,
        "simplified": "...",
        "pinyin": "...",
        "traditional": "...",
        "pos": "...",
        "classifier": "...",
        "definition": "...",
        "new_hsk": 1,
        "sentence_1": "...", "translation_1": "...",
        "sentence_2": "...", "translation_2": "...",
        "sentence_3": "...", "translation_3": "..."
    }
"""

import json
import os
import sys
import openpyxl

XLSX_PATH = os.path.join(os.path.dirname(__file__), '..', 'words.xlsx')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'level_data')

COLS = [
    'simplified', 'pinyin', 'traditional', 'pos',
    'classifier', 'definition', 'new_hsk',
    'sentence_1', 'translation_1',
    'sentence_2', 'translation_2',
    'sentence_3', 'translation_3',
]


def load_rows(ws):
    rows_by_level = {}
    vocab_by_level = {}
    for r_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        data = dict(zip(COLS, row))
        lvl = data.get('new_hsk')
        if not lvl:
            continue
        lvl = int(str(lvl).lstrip('L'))
        data['row'] = r_idx
        data['new_hsk'] = lvl
        rows_by_level.setdefault(lvl, []).append(data)
        word = data.get('simplified', '')
        if word:
            vocab_by_level.setdefault(lvl, set()).add(word)
    return rows_by_level, vocab_by_level


def main():
    levels_requested = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else list(range(1, 7))

    wb = openpyxl.load_workbook(XLSX_PATH)
    ws = wb.active
    print(f'Loaded {XLSX_PATH}')

    rows_by_level, vocab_by_level = load_rows(ws)
    os.makedirs(OUT_DIR, exist_ok=True)

    for lvl in sorted(levels_requested):
        if lvl not in rows_by_level:
            print(f'  L{lvl}: no rows found, skipping')
            continue

        # Export rows for this level
        rows = rows_by_level[lvl]
        out_path = os.path.join(OUT_DIR, f'L{lvl}.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        print(f'  L{lvl}: {len(rows)} rows -> {out_path}')

        # Export cumulative vocabulary up to this level
        cumulative_vocab = set()
        for l in range(1, lvl + 1):
            cumulative_vocab |= vocab_by_level.get(l, set())
        vocab_path = os.path.join(OUT_DIR, f'vocab_upto_L{lvl}.json')
        with open(vocab_path, 'w', encoding='utf-8') as f:
            json.dump(sorted(cumulative_vocab), f, ensure_ascii=False, indent=2)
        print(f'  vocab_upto_L{lvl}: {len(cumulative_vocab)} words -> {vocab_path}')

    print('Done.')


if __name__ == '__main__':
    main()
