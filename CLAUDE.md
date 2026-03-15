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

## Generation

Always generate content in-session (using your own knowledge and capabilities). Never call the Claude API or any external AI API to generate content. Prefer parallel batches when generating (e.g. use dispatching-parallel-agents or parallel tool calls to process multiple items simultaneously).

## Sentence Generation

When generating example sentences for flashcard rows:
- Use vocabulary at or below the HSK level of the word being illustrated (e.g. for an L1 word, use only L1 vocabulary; for an L2 word, L1–L2 vocabulary is fine)
- If the row has a classifier, try to use it naturally in at least one of the three sentences
- Write sentences that clearly illustrate the specific definition of that row, not the word's other meanings
- Prefer short sentences

## Architecture

- `scripts/build_csv.py` — four pure functions (`fetch_json`, `merge_entries`, `to_rows`, `write_csv`) plus `main()`
- `tests/test_build_csv.py` — unit tests using in-memory fixtures (no network calls except `test_fetch_json_returns_list`)
