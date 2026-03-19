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
