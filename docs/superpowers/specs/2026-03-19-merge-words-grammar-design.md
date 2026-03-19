# Merge words.tsv and grammar.tsv into cards.tsv

## Overview

Replace `words.tsv` and `grammar.tsv` with a single `cards.tsv` that holds both word and grammar flashcard rows under a unified schema. This simplifies the pipeline (one source file, one set of columns) and unifies the data model so both card types share the same structure.

## Schema

17 tab-separated columns:

| # | Column | Word rows | Grammar rows |
|---|--------|-----------|--------------|
| 1 | `name` | headword (e.g. `爱`) | grammar content (e.g. `小—、第—`) |
| 2 | `pinyin` | tone-marked pinyin | empty (for now) |
| 3 | `pos` | part of speech | empty |
| 4 | `classifier` | measure word(s) | empty |
| 5 | `definition` | English gloss | empty |
| 6 | `level` | `L1`–`L6` | `L1`–`L6` |
| 7 | `type` | `word` | `grammar` |
| 8 | `grammar_category` | empty | category label (see below) |
| 9 | `sentence_1` | Chinese sentence | Chinese sentence |
| 10 | `pinyin_1` | empty (for now) | empty (for now) |
| 11 | `translation_1` | English translation | English translation |
| 12 | `sentence_2` | Chinese sentence | Chinese sentence |
| 13 | `pinyin_2` | empty (for now) | empty (for now) |
| 14 | `translation_2` | English translation | English translation |
| 15 | `sentence_3` | Chinese sentence | Chinese sentence |
| 16 | `pinyin_3` | empty (for now) | empty (for now) |
| 17 | `translation_3` | English translation | English translation |

## Column mapping

### From words.tsv

| Old column | New column |
|-----------|-----------|
| `simplified` | `name` |
| `pinyin` | `pinyin` |
| `pos` | `pos` |
| `classifier` | `classifier` |
| `definition` | `definition` |
| `new_hsk` | `level` |
| `sentence_N` | `sentence_N` |
| `translation_N` | `translation_N` |
| (new) | `type` = `word` |
| (new) | `grammar_category` = empty |
| (new) | `pinyin_N` = empty |

### From grammar.tsv

| Old column | New column |
|-----------|-----------|
| `content` | `name` |
| `hsk_level` | `level` |
| `grammar_type` | dropped |
| `category_type` | dropped |
| `grammar_detail` | collapsed into `grammar_category` |
| `description` | dropped |
| `sentence_N` | `sentence_N` |
| `translation_N` | `translation_N` |
| (new) | `type` = `grammar` |
| (new) | `pinyin` = empty |
| (new) | `pos` = empty |
| (new) | `classifier` = empty |
| (new) | `definition` = empty |
| (new) | `pinyin_N` = empty |

### grammar_category derivation

The old grammar.tsv has three taxonomy columns: `grammar_type`, `category_type`, `grammar_detail`. These collapse into a single `grammar_category` using the most specific non-empty value: `grammar_detail` if present, else `category_type` if present, else `grammar_type`.

## Row ordering

Within the file, rows are grouped by level (L1 first, then L2, etc.). Within each level, all word rows appear first (preserving their original order), followed by all grammar rows (preserving their original order).

## Downstream changes

### build_sentences_xlsx.py

- Read `cards.tsv` instead of `words.tsv` + `grammar.tsv`
- Merge `extract_words` and `extract_grammar` into one function that branches on `type`
- Column name changes: `simplified` → `name`, `new_hsk`/`hsk_level` → `level`
- Key format preserved for Anki GUID stability:
  - Word keys: `w|{name}|{definition}|s{n}` (same shape as before)
  - Grammar keys: `g|{grammar_category}|{name}|s{n}` (same shape — `grammar_category` replaces `grammar_detail`, `name` replaces `content`)

### export_chunk_data.py

- Read `cards.tsv` instead of `words.tsv`
- Update column references: `simplified` → `name`, `new_hsk` → `level`
- Export both word and grammar chunks (grammar rows get their own chunk files)

### audio/generate_audio.py

- Update TSV path: `words.tsv` → `cards.tsv`
- Update column reference: `new_hsk` → `level`
- `count_words_per_level` reads `level` column instead of `new_hsk`

### build_anki_sentences.py

- No change (reads `data/sentences.tsv`, not the source files)

### docs/agent-instructions/generate-sentences.md

- Update all references from `words.tsv` to `cards.tsv`
- Update column names: `simplified` → `name`, `new_hsk` → `level`

### CLAUDE.md

- Update file references, column names, and quality guidelines to reflect `cards.tsv`
- Merge the "Row Quality: words.tsv" and "Row Quality: grammar.tsv" sections

## Files deleted after merge

- `words.tsv`
- `grammar.tsv`

## Migration

A one-time Python script (`merge_to_cards.py`) reads both old files, maps columns, and writes `cards.tsv`. After verifying the output, delete the old files and the migration script.
