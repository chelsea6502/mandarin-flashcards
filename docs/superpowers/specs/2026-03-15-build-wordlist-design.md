# Design: Build Word List XLSX

## Overview

A Python script that reads Mandarin word lists from HSK source text files, deduplicates them, and writes a structured XLSX file ready for pinyin and definition annotation.

## Inputs

Source files from `~/flashcards/source/` (explicitly listed — higher levels exist on disk but are intentionally excluded per requirements):
- `HSK2/HSK1.txt`, `HSK2/HSK2.txt`, `HSK2/HSK3.txt`, `HSK2/HSK4.txt`, `HSK2/HSK5.txt`
- `HSK3/HSK1.txt`, `HSK3/HSK2.txt`, `HSK3/HSK3.txt`

Each file contains one Chinese word per line.

## Output

`data/words.xlsx` in the project repository.

### Columns

| Column | Notes |
|--------|-------|
| Word | Simplified Chinese character(s) |
| Pinyin | Empty — to be filled in later |
| Definition | Empty — to be filled in later |
| Sources | Comma-separated list of source lists (e.g. `HSK2-L1, HSK3-L1`) |

### Ordering

Rows ordered by first appearance: HSK2-L1 first, then HSK2-L2 through HSK2-L5, then HSK3-L1 through HSK3-L3. Words already seen in an earlier list are not repeated as rows; their later-list label is appended to the Sources column.

## Deduplication

Words are deduplicated by exact character match. If the same word appears in multiple source lists, it gets one row with all source labels listed in the Sources column. Duplicates within a single file are also collapsed — each word appears at most once regardless of how many times it occurs in any one file.

## Script

**Location:** `scripts/build_wordlist.py`

**Library:** `openpyxl` only (no pandas).

**Encoding:** All source files are read as UTF-8.

**Source label format:** Directory name + `-L` + the digits obtained by stripping the leading non-digit characters from the filename stem (e.g. strip `HSK` from `HSK1` → `1`). Examples: `HSK2/HSK1.txt` → `HSK2-L1`, `HSK3/HSK3.txt` → `HSK3-L3`.

**Python version:** 3.7+.

**Input paths:** Resolved relative to `~/flashcards/source/` (a directory separate from the repo). The eight files are hard-coded in the ordered list defined in step 1. If any of those eight files does not exist at runtime, the script prints an error to stderr and exits with code 1 before writing any output.

**Output path:** `data/words.xlsx` inside the repo (separate from `~/flashcards/`). If the file already exists it is overwritten. The `data/` directory is created if it does not exist; if creation fails the script prints an error to stderr and exits with code 1.

**Whitespace handling:** Each line is `.strip()`-ed (both ends). Blank lines after stripping are skipped. Lines with internal whitespace (e.g. `你 好`) are treated as valid words and kept as-is — no validation of internal content.

**Sources separator:** Comma-space: `HSK2-L1, HSK3-L1`.

**Output styling:** Plain — no bold headers, no frozen panes, no column width adjustments.

**Repo root resolution:** The script resolves the output path using `Path(__file__).parent.parent` (i.e., one level above `scripts/`), so it works regardless of working directory.

**Empty files:** A source file that exists but yields zero non-blank lines is silently accepted — it contributes no rows or labels.

**Logic:**
1. Define ordered list of `(source_label, file_path)` pairs in processing order
2. Verify all eight files exist; abort with a clear error message if any are missing
3. For each file in order, read lines as UTF-8, `.strip()`, skip blanks
4. Maintain a `dict` (insertion-ordered, Python 3.7+): word → list of source labels. For each word: if the word is not yet a key, add it with `[source_label]`. If it is already a key (seen in any prior file or earlier in the current file), append `source_label` only if it is not already in the list. This check is global — the same word is never added as a new row regardless of which file it re-appears in.
5. Write to XLSX: header row (`Word`, `Pinyin`, `Definition`, `Sources`), then one row per unique word with Sources joined as `", "` (comma-space)
