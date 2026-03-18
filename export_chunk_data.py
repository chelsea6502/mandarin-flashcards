#!/usr/bin/env python3
"""
Export flashcard rows by HSK level for audit agents.

Produces chunked TSV files (same format as words.tsv) plus a vocabulary file
per level.

Usage:
    python3 export_chunk_data.py            # exports all levels
    python3 export_chunk_data.py 1 2        # exports L1 and L2 only

Output files:
    data/level_data/L1_chunk_01.tsv, L1_chunk_02.tsv, ..., L1_vocab.txt
"""

import csv
import math
import os
import sys

TSV_PATH = os.path.join(os.path.dirname(__file__), 'words.tsv')
OUT_DIR = os.path.join(os.path.dirname(__file__), 'data', 'level_data')

CHUNK_SIZE = 50

COLUMNS = [
    'simplified', 'pinyin', 'pos', 'classifier', 'definition', 'new_hsk',
    'sentence_1', 'translation_1', 'sentence_2', 'translation_2',
    'sentence_3', 'translation_3',
]


def load_rows(tsv_path):
    rows_by_level = {}
    vocab_by_level = {}
    with open(tsv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f, dialect='excel-tab')
        for r_idx, row in enumerate(reader, start=2):
            lvl = row.get('new_hsk', '')
            if not lvl:
                continue
            lvl_num = int(str(lvl).lstrip('L'))
            data = dict(row)
            data['row'] = r_idx
            data['new_hsk'] = lvl
            rows_by_level.setdefault(lvl_num, []).append(data)
            word = data.get('simplified', '')
            if word:
                vocab_by_level.setdefault(lvl_num, set()).add(word)
            classifier = data.get('classifier', '')
            if classifier and classifier != 'null':
                for cl in classifier.split(','):
                    cl = cl.strip()
                    if cl:
                        vocab_by_level.setdefault(lvl_num, set()).add(cl)
    return rows_by_level, vocab_by_level


# Functional characters taught via grammar.tsv that lack their own words.tsv
# entry.  Keyed by the earliest HSK level where they appear.
_GRAMMAR_EXTRAS = {
    1: {'儿', '号', '没'},
    2: {'着'},
    6: {'啦', '嘛'},
}


def chunk(rows, size):
    """Split rows into chunks of the given size."""
    for i in range(0, len(rows), size):
        yield rows[i:i + size]


def rows_to_tsv(rows, chunk_num, total_chunks):
    """Format rows as a TSV string with a header comment and column headers."""
    lines = [f'# chunk {chunk_num}/{total_chunks}']
    lines.append('ROW\t' + '\t'.join(COLUMNS))
    for r in rows:
        vals = [str(r.get('row', ''))]
        vals.extend(str(r.get(c, '') or '') for c in COLUMNS)
        lines.append('\t'.join(vals))
    return '\n'.join(lines) + '\n'


def main():
    levels_requested = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else list(range(1, 7))

    rows_by_level, vocab_by_level = load_rows(TSV_PATH)
    for lvl, items in _GRAMMAR_EXTRAS.items():
        vocab_by_level.setdefault(lvl, set()).update(items)
    print(f'Loaded {TSV_PATH}')

    os.makedirs(OUT_DIR, exist_ok=True)

    for lvl in sorted(levels_requested):
        if lvl not in rows_by_level:
            print(f'  L{lvl}: no rows found, skipping')
            continue

        rows = rows_by_level[lvl]
        total_chunks = math.ceil(len(rows) / CHUNK_SIZE)

        for i, ch in enumerate(chunk(rows, CHUNK_SIZE), 1):
            tsv = rows_to_tsv(ch, i, total_chunks)

            if total_chunks == 1:
                filename = f'L{lvl}_chunk.tsv'
            else:
                filename = f'L{lvl}_chunk_{i:02d}.tsv'

            path = os.path.join(OUT_DIR, filename)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(tsv)

        # Cumulative vocabulary file
        cumulative_vocab = set()
        for l in range(1, lvl + 1):
            cumulative_vocab |= vocab_by_level.get(l, set())

        vocab_path = os.path.join(OUT_DIR, f'L{lvl}_vocab.txt')
        with open(vocab_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted(cumulative_vocab)) + '\n')

        print(f'  L{lvl}: {len(rows)} rows, {total_chunks} chunk(s), {len(cumulative_vocab)} vocab')

    print('Done.')


if __name__ == '__main__':
    main()
