# Merge words.tsv + grammar.tsv → cards.tsv Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `words.tsv` and `grammar.tsv` with a single `cards.tsv` using a unified 17-column schema, then update all downstream scripts and docs.

**Architecture:** A one-time migration script reads both old TSVs, maps columns to the new schema, and writes `cards.tsv`. Then each downstream consumer is updated to read the new file/columns. Old files are deleted last.

**Tech Stack:** Python 3 (stdlib only for migration), TSV data format.

**Spec:** `docs/superpowers/specs/2026-03-19-merge-words-grammar-design.md`

---

### Task 1: Write and run the migration script

**Files:**
- Create: `merge_to_cards.py`
- Read: `words.tsv`, `grammar.tsv`
- Create: `cards.tsv`

This script is run once and deleted after. No tests needed — we verify by row count and spot checks.

- [ ] **Step 1: Write `merge_to_cards.py`**

```python
#!/usr/bin/env python3
"""One-time migration: merge words.tsv + grammar.tsv → cards.tsv."""

import csv
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

WORDS_PATH = os.path.join(ROOT, 'words.tsv')
GRAMMAR_PATH = os.path.join(ROOT, 'grammar.tsv')
OUT_PATH = os.path.join(ROOT, 'cards.tsv')

COLUMNS = [
    'name', 'pinyin', 'pos', 'classifier', 'definition', 'level', 'type',
    'grammar_category', 'sentence_1', 'pinyin_1', 'translation_1',
    'sentence_2', 'pinyin_2', 'translation_2',
    'sentence_3', 'pinyin_3', 'translation_3',
]


def read_words(path):
    """Yield dicts in the new schema from words.tsv."""
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, dialect='excel-tab'):
            yield {
                'name': row.get('simplified', ''),
                'pinyin': row.get('pinyin', ''),
                'pos': row.get('pos', ''),
                'classifier': row.get('classifier', ''),
                'definition': row.get('definition', ''),
                'level': row.get('new_hsk', ''),
                'type': 'word',
                'grammar_category': '',
                'sentence_1': row.get('sentence_1', ''),
                'pinyin_1': '',
                'translation_1': row.get('translation_1', ''),
                'sentence_2': row.get('sentence_2', ''),
                'pinyin_2': '',
                'translation_2': row.get('translation_2', ''),
                'sentence_3': row.get('sentence_3', ''),
                'pinyin_3': '',
                'translation_3': row.get('translation_3', ''),
            }


def derive_grammar_category(row):
    """Return grammar_detail value only (no fallback to category_type/grammar_type).

    We use grammar_detail exclusively because it feeds into sentence key
    generation for Anki GUID stability. The old key format was
    g|{grammar_detail}|{content}|s{n}, so grammar_category must match
    grammar_detail exactly. ~97 rows have empty grammar_detail and will
    get empty grammar_category — this is intentional.
    """
    return row.get('grammar_detail', '').strip()


def read_grammar(path):
    """Yield dicts in the new schema from grammar.tsv."""
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, dialect='excel-tab'):
            yield {
                'name': row.get('content', '').strip(),
                'pinyin': '',
                'pos': '',
                'classifier': '',
                'definition': '',
                'level': row.get('hsk_level', ''),
                'type': 'grammar',
                'grammar_category': derive_grammar_category(row),
                'sentence_1': row.get('sentence_1', ''),
                'pinyin_1': '',
                'translation_1': row.get('translation_1', ''),
                'sentence_2': row.get('sentence_2', ''),
                'pinyin_2': '',
                'translation_2': row.get('translation_2', ''),
                'sentence_3': row.get('sentence_3', ''),
                'pinyin_3': '',
                'translation_3': row.get('translation_3', ''),
            }


def level_sort_key(level_str):
    """'L1' → 1, 'L2' → 2, etc."""
    return int(level_str.lstrip('L')) if level_str.startswith('L') else 99


def main():
    words = list(read_words(WORDS_PATH))
    grammar = list(read_grammar(GRAMMAR_PATH))

    # Group by level, words first then grammar within each level
    from collections import defaultdict
    by_level = defaultdict(lambda: ([], []))
    for row in words:
        by_level[row['level']][0].append(row)
    for row in grammar:
        by_level[row['level']][1].append(row)

    with open(OUT_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, dialect='excel-tab')
        writer.writeheader()
        total = 0
        for level in sorted(by_level, key=level_sort_key):
            word_rows, grammar_rows = by_level[level]
            for row in word_rows:
                writer.writerow(row)
                total += 1
            for row in grammar_rows:
                writer.writerow(row)
                total += 1

    print(f'Wrote {total} rows to {OUT_PATH}')
    print(f'  {len(words)} word rows + {len(grammar)} grammar rows')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run the migration**

Run: `python3 merge_to_cards.py`
Expected: `Wrote 7872 rows to cards.tsv` (7412 words + 460 grammar, approximately)

- [ ] **Step 3: Verify row counts**

Run: `wc -l cards.tsv words.tsv grammar.tsv`
Expected: cards.tsv line count = words.tsv lines + grammar.tsv lines - 1 (one header instead of two)

- [ ] **Step 4: Verify schema — check header and sample rows**

Run: `head -1 cards.tsv | tr '\t' '\n' | cat -n`
Expected: 17 columns matching the spec schema.

Run: `grep -m1 'grammar' cards.tsv | head -1` to confirm a grammar row has the right shape.

- [ ] **Step 5: Verify level ordering — words before grammar within each level**

Run: `awk -F'\t' 'NR>1 {print $6, $7}' cards.tsv | uniq | head -20`
Expected: For each level, `word` lines appear before `grammar` lines.

- [ ] **Step 6: Commit**

```bash
git add cards.tsv
git commit -m "data: create cards.tsv by merging words.tsv + grammar.tsv"
```

---

### Task 2: Update build_sentences_xlsx.py

**Files:**
- Modify: `build_sentences_xlsx.py`

Replace `extract_words` + `extract_grammar` with a single `extract_sentences` that reads `cards.tsv` and branches on the `type` column. Key format stays stable for Anki GUIDs.

- [ ] **Step 1: Rewrite the extraction logic**

Replace the entire file with:

```python
"""Build data/sentences.tsv from cards.tsv.

Extracts the three sentence/translation pairs from each row and writes
them as individual rows in sentences.tsv.

Output order per level: word sentences first, then grammar sentences.
Levels are emitted in order (L1, L2, L3, ...).
"""

import csv
from collections import defaultdict
from pathlib import Path

from pypinyin import pinyin, Style
from pypinyin_dict.phrase_pinyin_data import cc_cedict

cc_cedict.load()


def sentence_to_pinyin(sentence):
    """Convert a Chinese sentence to space-separated pinyin with tone marks."""
    result = pinyin(sentence, style=Style.TONE, heteronym=False)
    return ' '.join(syl[0] for syl in result)


def extract_sentences(path):
    """Yield (key, level, type, sentence, translation) from cards.tsv."""
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, dialect='excel-tab'):
            level = row.get("level", "")
            row_type = row.get("type", "")
            name = row.get("name", "")
            definition = row.get("definition", "")
            grammar_category = row.get("grammar_category", "")
            for n in (1, 2, 3):
                sentence = row.get(f"sentence_{n}", "")
                translation = row.get(f"translation_{n}", "")
                if sentence:
                    if row_type == "grammar":
                        parts = [p for p in [grammar_category, name] if p]
                        key = f"g|{'|'.join(parts)}|s{n}"
                    else:
                        key = f"w|{name}|{definition}|s{n}"
                    yield (key, str(level), row_type, sentence.strip(), translation.strip())


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", type=int, default=None,
                        help="Max HSK level to include (e.g. 3 for L1-L3)")
    args = parser.parse_args()

    root = Path(__file__).parent
    cards_path = root / "cards.tsv"
    out_path = root / "data" / "sentences.tsv"

    # Group by level and type, preserving row order
    words_by_level = defaultdict(list)
    grammar_by_level = defaultdict(list)

    for key, level, row_type, sentence, translation in extract_sentences(cards_path):
        if row_type == "grammar":
            grammar_by_level[level].append((key, sentence, translation))
        else:
            words_by_level[level].append((key, sentence, translation))

    all_levels = sorted(set(words_by_level) | set(grammar_by_level))
    if args.level is not None:
        allowed = {f"L{i}" for i in range(1, args.level + 1)}
        all_levels = [l for l in all_levels if l in allowed]

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, dialect='excel-tab')
        writer.writerow(["key", "level", "sentence", "pinyin", "translation"])

        words_count = 0
        grammar_count = 0
        for level in all_levels:
            for key, sentence, translation in words_by_level.get(level, []):
                writer.writerow([key, level, sentence, sentence_to_pinyin(sentence), translation])
                words_count += 1
            for key, sentence, translation in grammar_by_level.get(level, []):
                writer.writerow([key, level, sentence, sentence_to_pinyin(sentence), translation])
                grammar_count += 1

    total = words_count + grammar_count
    print(f"Wrote {total} rows to {out_path} ({words_count} words + {grammar_count} grammar)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify key stability**

Run: `python3 build_sentences_xlsx.py`
Then compare output with the previous version:
Run: `git diff data/sentences.tsv | head -50`
Expected: Only whitespace or ordering changes if any — no key format changes. The `key` column values should be identical to the previous output.

- [ ] **Step 3: Commit**

```bash
git add build_sentences_xlsx.py
git commit -m "refactor: build_sentences_xlsx reads cards.tsv instead of words.tsv + grammar.tsv"
```

---

### Task 3: Update export_chunk_data.py

**Files:**
- Modify: `export_chunk_data.py`

Update to read `cards.tsv` with new column names. Export both word and grammar chunks.

- [ ] **Step 1: Rewrite export_chunk_data.py**

Replace the entire file with:

```python
#!/usr/bin/env python3
"""
Export flashcard rows by HSK level for audit agents.

Produces chunked TSV files (same format as cards.tsv) plus a vocabulary file
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

TSV_PATH = os.path.join(os.path.dirname(__file__), 'cards.tsv')
OUT_DIR = os.path.join(os.path.dirname(__file__), 'data', 'level_data')

CHUNK_SIZE = 50

COLUMNS = [
    'name', 'pinyin', 'pos', 'classifier', 'definition', 'level', 'type',
    'grammar_category', 'sentence_1', 'pinyin_1', 'translation_1',
    'sentence_2', 'pinyin_2', 'translation_2',
    'sentence_3', 'pinyin_3', 'translation_3',
]


def load_rows(tsv_path):
    rows_by_level = {}
    vocab_by_level = {}
    with open(tsv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f, dialect='excel-tab')
        for r_idx, row in enumerate(reader, start=2):
            lvl = row.get('level', '')
            if not lvl:
                continue
            lvl_num = int(str(lvl).lstrip('L'))
            data = dict(row)
            data['row'] = r_idx
            rows_by_level.setdefault(lvl_num, []).append(data)
            name = data.get('name', '')
            if name and data.get('type') == 'word':
                vocab_by_level.setdefault(lvl_num, set()).add(name)
            classifier = data.get('classifier', '')
            if classifier and classifier != 'null':
                for cl in classifier.split(','):
                    cl = cl.strip()
                    if cl:
                        vocab_by_level.setdefault(lvl_num, set()).add(cl)
    return rows_by_level, vocab_by_level


# Functional characters taught via grammar rows that lack their own word row.
# Keyed by the earliest HSK level where they appear.
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
```

Key changes from original:
- `TSV_PATH` points to `cards.tsv`
- Column list uses new names (`name`, `level`, `type`, `grammar_category`, `pinyin_N`)
- `load_rows` reads `level` instead of `new_hsk`, `name` instead of `simplified`
- Vocab collection only adds `name` for `type=word` rows (grammar names like `小—、第—` are not vocabulary)
- `_GRAMMAR_EXTRAS` dict preserved — these characters are taught via grammar rows but lack word rows

- [ ] **Step 2: Run and verify**

Run: `python3 export_chunk_data.py 1`
Expected: Chunk files created in `data/level_data/` with the new column headers.

Run: `head -3 data/level_data/L1_chunk_01.tsv`
Expected: Header row starts with `ROW name pinyin pos classifier definition level type grammar_category ...`

- [ ] **Step 3: Commit**

```bash
git add export_chunk_data.py
git commit -m "refactor: export_chunk_data reads cards.tsv with new column names"
```

---

### Task 4: Update audio/generate_audio.py

**Files:**
- Modify: `audio/generate_audio.py:56,80-85`

Two small changes: TSV path and column name.

- [ ] **Step 1: Update WORDS_TSV path**

Change line 56 from:
```python
WORDS_TSV = os.path.join(_DIR, "..", "words.tsv")
```
to:
```python
WORDS_TSV = os.path.join(_DIR, "..", "cards.tsv")
```

- [ ] **Step 2: Update column reference in count_words_per_level**

Change line 85 from:
```python
            level = row.get("new_hsk", "")
```
to:
```python
            level = row.get("level", "")
```

- [ ] **Step 3: Update the docstring on line 81**

Change from:
```python
    """Return dict of level -> word count from words.tsv."""
```
to:
```python
    """Return dict of level -> word count from cards.tsv."""
```

- [ ] **Step 4: Commit**

```bash
git add audio/generate_audio.py
git commit -m "refactor: generate_audio reads cards.tsv with new column names"
```

---

### Task 5: Update docs/agent-instructions/generate-sentences.md

**Files:**
- Modify: `docs/agent-instructions/generate-sentences.md`

Update file references and column names throughout.

- [ ] **Step 1: Apply all text replacements**

| Line | Old text | New text |
|------|----------|----------|
| 3 | `words.tsv` | `cards.tsv` |
| 11 | `new_hsk=L1` or `new_hsk=L2` | `level=L1` or `level=L2` |
| 19 | `words.tsv` | `cards.tsv` |
| 22 | `simplified	pinyin	pos	classifier	definition	new_hsk	sentence_1	translation_1	sentence_2	translation_2	sentence_3	translation_3` | `name	pinyin	pos	classifier	definition	level	type	grammar_category	sentence_1	pinyin_1	translation_1	sentence_2	pinyin_2	translation_2	sentence_3	pinyin_3	translation_3` |
| 57 | `words.tsv` (×2) | `cards.tsv` |
| 67 | `words.tsv` | `cards.tsv` |

- [ ] **Step 2: Commit**

```bash
git add docs/agent-instructions/generate-sentences.md
git commit -m "docs: update generate-sentences instructions for cards.tsv schema"
```

---

### Task 6: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update Stack section**

Change:
```
- **TSV** as the working data format (`words.tsv`, `grammar.tsv`, `data/sentences.tsv`) — directly readable/writable by Claude Code
```
to:
```
- **TSV** as the working data format (`cards.tsv`, `data/sentences.tsv`) — directly readable/writable by Claude Code
```

- [ ] **Step 2: Merge "Row Quality" sections**

Replace both "Row Quality: words.tsv" and "Row Quality: grammar.tsv" sections with a single "Row Quality: cards.tsv" section:

```markdown
## Row Quality: cards.tsv

Each row represents either one definition of one word (`type=word`) or one grammar point (`type=grammar`). Quality means every field is accurate **and** internally consistent.

### Word rows

**Core fields**
- `name` — correct simplified characters
- `pinyin` — correct tones as diacritics (ā á ǎ à), not numbers; syllables space-separated; neutral tone written without mark (e.g. `ba`, not `bà`)
- `pos` — accurate, using the existing taxonomy in the file; comma-separated when multiple
- `classifier` — correct measure word(s) for this specific noun sense; null if inapplicable; comma-separated if multiple
- `definition` — accurate English gloss for this row's specific sense; verbs start with "to …"; natural English; not duplicating another row for the same word

**Sentences**
- Grammatically correct, natural Mandarin
- Vocabulary at or below the row's HSK level
- Three distinct sentences — different contexts or structures, not minor variations of each other
- If a classifier is present, at least one sentence uses it naturally with a numeral
- Each sentence ends with 。 ！ or ？; no pinyin mixed in
- Prefer short, clear sentences

### Grammar rows

**Core fields**
- `name` — the specific grammar item(s); uses — to mark where the morpheme attaches (e.g. `—们`, `小—`)
- `grammar_category` — accurate category label matching the file's existing conventions

**Sentences**
- Each sentence unambiguously demonstrates the grammar point — not a sentence where it just happens to appear
- If name lists multiple forms, the three sentences collectively cover all of them
- Vocabulary appropriate for the row's HSK level
- Accurate, natural English translations
- Sentences are distinct — different forms, contexts, or functions
```

- [ ] **Step 3: Update Architecture section**

Replace:
```
- `export_chunk_data.py` — reads `words.tsv`, exports chunked TSVs to `data/level_data/` for agent audit workflows
- `build_sentences_xlsx.py` — reads `words.tsv` + `grammar.tsv`, writes `data/sentences.tsv`
```
with:
```
- `export_chunk_data.py` — reads `cards.tsv`, exports chunked TSVs to `data/level_data/` for agent audit workflows
- `build_sentences_xlsx.py` — reads `cards.tsv`, writes `data/sentences.tsv`
```

- [ ] **Step 4: Update Agent Audit Workflow section**

Replace references to `words.tsv` column names:
- `same columns as words.tsv` → `same columns as cards.tsv`
- `the row number in words.tsv` → `the row number in cards.tsv`
- `fix issues directly in words.tsv` → `fix issues directly in cards.tsv`

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for cards.tsv schema"
```

---

### Task 7: Delete old files and migration script

**Files:**
- Delete: `words.tsv`, `grammar.tsv`, `merge_to_cards.py`

- [ ] **Step 1: Delete old files**

```bash
git rm words.tsv grammar.tsv
rm merge_to_cards.py
```

- [ ] **Step 2: Commit**

```bash
git commit -m "chore: remove words.tsv, grammar.tsv after migration to cards.tsv"
```

---

### Task 8: Final verification

- [ ] **Step 1: Verify all scripts reference cards.tsv, not words.tsv or grammar.tsv**

Run: `grep -r 'words\.tsv\|grammar\.tsv' --include='*.py' --include='*.md' .`
Expected: No matches (except possibly in the spec doc or git history references, which are fine).

- [ ] **Step 2: Run build_sentences_xlsx.py end-to-end**

Run: `python3 build_sentences_xlsx.py`
Expected: Completes without error, writes data/sentences.tsv with correct row count.

- [ ] **Step 3: Run export_chunk_data.py end-to-end**

Run: `python3 export_chunk_data.py`
Expected: Completes without error, writes chunk files with new column headers.
