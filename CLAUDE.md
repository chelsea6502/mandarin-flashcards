# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Blueprints and tooling for designing Mandarin Chinese flashcards. Word lists are sourced from HSK JSON vocabularies, processed into a CSV, and will eventually be exported to Anki (`.apkg`).

## Stack

- **Python** for all scripts (stdlib only — no third-party deps except `pytest`)
- **CSV** as the working data format
- **Anki** as the eventual export target (via `genanki` or similar)

## Commands

```bash
# Generate data/words.csv from HSK JSON sources
python3 scripts/build_csv.py

# Run tests
python3 -m pytest tests/ -v

# Run a single test
python3 -m pytest tests/test_build_csv.py::test_name -v
```

## Data

- `data/words.csv` — generated file, committed to repo.
  Columns: `simplified, pinyin, traditional, pos, classifier, definition, source`
  One row per definition. Re-run `build_csv.py` to regenerate.
- Sources: old HSK5 + new HSK3 from `drkameleon/complete-hsk-vocabulary` on GitHub.
  Words in both lists use new HSK3 definitions; `source` column tracks provenance.

## Architecture

- `scripts/build_csv.py` — four pure functions (`fetch_json`, `merge_entries`, `to_rows`, `write_csv`) plus `main()`
- `tests/test_build_csv.py` — unit tests using in-memory fixtures (no network calls except `test_fetch_json_returns_list`)
