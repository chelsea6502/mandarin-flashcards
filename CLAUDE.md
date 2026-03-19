# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Blueprints and tooling for designing Mandarin Chinese flashcards. Word lists are sourced from HSK JSON vocabularies, processed into a CSV, and will eventually be exported to Anki (`.apkg`).

## Stack

- **Python** for all scripts (stdlib only — no third-party deps except `pytest`)
- **TSV** as the working data format (`cards.tsv`) — directly readable/writable by Claude Code
- **Anki** as the eventual export target (via `genanki` or similar)

## Commands

```bash
# Generate data/words.csv from HSK JSON sources
python3 build_csv.py

# Run tests
python3 -m pytest tests/ -v

# Run a single test
python3 -m pytest tests/test_build_csv.py::test_name -v
```

## Data

- `data/words.csv` — generated file, committed to repo.
  Columns: `simplified, pinyin, pos, classifier, definition, source`
  One row per definition. Re-run `build_csv.py` to regenerate.
- Sources: old HSK5 + new HSK3 from `drkameleon/complete-hsk-vocabulary` on GitHub.
  Words in both lists use new HSK3 definitions; `source` column tracks provenance.

## Generation

Always generate content in-session (using your own knowledge and capabilities). Never call the Claude API or any external AI API to generate content. Prefer parallel batches when generating (e.g. use dispatching-parallel-agents or parallel tool calls to process multiple items simultaneously).

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

## Sentence Generation

When generating example sentences for flashcard rows:
- Use vocabulary at or below the HSK level of the word being illustrated (e.g. for an L1 word, use only L1 vocabulary; for an L2 word, L1–L2 vocabulary is fine)
- If the row has a classifier, try to use it naturally in at least one of the three sentences
- Write sentences that clearly illustrate the specific definition of that row, not the word's other meanings
- Prefer short sentences

## Architecture

- `build_csv.py` — four pure functions (`fetch_json`, `merge_entries`, `to_rows`, `write_csv`) plus `main()`
- `build_anki.py` — reads `cards.tsv`, writes `sentences.apkg`
- `audio/generate_audio.py` — TTS audio generation for flashcard sentences
- `tests/test_build_csv.py` — unit tests using in-memory fixtures (no network calls except `test_fetch_json_returns_list`)
