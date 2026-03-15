# Design: Build Grammar XLSX

## Overview

A Python script that fetches HSK grammar point files from GitHub, parses them into structured rows, and writes `data/grammar.xlsx` — a spreadsheet parallel to `data/words.xlsx` with irrelevant vocabulary columns removed.

## Inputs

Seven files fetched at runtime via `urllib.request` from `https://raw.githubusercontent.com/krmanik/HSK-3.0/main/New%20HSK%20(2021)/HSK%20Grammar/`:

- `HSK 1.txt` → level `L1`
- `HSK 2.txt` → level `L2`
- `HSK 3.txt` → level `L3`
- `HSK 4.txt` → level `L4`
- `HSK 5.txt` → level `L5`
- `HSK 6.txt` → level `L6`
- `HSK 7-9.txt` → level `L7-9`

Each file is UTF-8 encoded and contains numbered grammar point entries interspersed with section headers.

## Output

`data/grammar.xlsx` in the project repository.

### Columns

| Column | Notes |
|--------|-------|
| `id` | Grammar point tag, e.g. `一01` (extracted from `【一01】`) |
| `name` | Descriptor text after `】`, e.g. `方位名词：上、下、里、外…` |
| `hsk_level` | Derived from filename, e.g. `L1`, `L7-9` |
| `sentence_1` | First example sentence from the grammar point block |
| `translation_1` | Empty — to be filled in later |
| `sentence_2` | Second example sentence |
| `translation_2` | Empty — to be filled in later |
| `sentence_3` | Third example sentence |
| `translation_3` | Empty — to be filled in later |

### Ordering

Rows appear in file order: L1 first, then L2 through L6, then L7-9. Within each file, grammar points appear in the order they occur in the source.

## Parsing Rules

**Grammar point lines** are identified by the pattern `【…】` anywhere in the line.
- `id`: the text between `【` and `】`
- `name`: all text after `】` on the same line, stripped

**Section header lines** are lines that do NOT contain `【` and match the pattern of lettered/numbered section headings (e.g. `A.1 一级语法点`, `A.1.1.1 名词`). These are skipped and not emitted as rows.

**Example sentences** are the non-blank lines that follow a grammar point line, up until the next grammar point line or section header line. From those lines, only lines ending with Chinese sentence-final punctuation (`。`, `？`, `！`) are treated as sentences. Other lines (e.g. bare phrase lists like `桌子上 树下`) are skipped.

The first three qualifying sentences populate `sentence_1`, `sentence_2`, `sentence_3`. If fewer than three sentences exist in the block, the remaining sentence columns are empty.

## Script

**Location:** `scripts/build_grammar.py`

**Library:** `openpyxl` only (no pandas, no third-party HTTP libraries).

**Fetch:** Each file is fetched with `urllib.request.urlopen`. If any fetch fails (non-200 or network error), the script prints an error to stderr and exits with code 1 before writing any output.

**Output path:** `data/grammar.xlsx` resolved via `Path(__file__).parent.parent`. If the file already exists it is overwritten. The `data/` directory is created if it does not exist.

**Output styling:** Plain — no bold headers, no frozen panes, no column width adjustments (consistent with `words.xlsx`).

**Logic:**
1. Define ordered list of `(level_label, url)` pairs
2. For each file: fetch and decode as UTF-8, split into lines, strip each line
3. Parse lines sequentially: on a grammar point line, extract `id` and `name`, then collect subsequent non-blank lines as candidate sentences (stopping at the next grammar point or section header)
4. From candidate lines, filter to those ending with `。`, `？`, or `！`; take the first three
5. Emit one row per grammar point: `id`, `name`, `hsk_level`, `sentence_1`, `translation_1`, `sentence_2`, `translation_2`, `sentence_3`, `translation_3`
6. Write header row then all data rows to `data/grammar.xlsx`
