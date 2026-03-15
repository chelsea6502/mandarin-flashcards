# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Blueprints and tooling for designing Mandarin Chinese flashcards. The source of truth is an XLSX file; scripts process it into flashcard formats. The long-term target output format is Anki (`.apkg`).

## Stack

- **Python** for all scripts
- **XLSX** as the primary data source
- **Anki** as the eventual export target (via `genanki` or similar)

## Architecture

- XLSX file holds the card data (headword, definition, pinyin, example sentences, tags, etc.)
- Python scripts read the XLSX and transform/export it
- Anki export will use a library like `genanki` to produce `.apkg` files
