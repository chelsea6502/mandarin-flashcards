"""Build an Anki deck from cards.tsv.

Three sibling card types per note:
  Sentence → Meaning:      Front shows Chinese, back shows pinyin + translation + audio
  Audio → Meaning:          Front plays audio, back shows sentence + pinyin + translation
  Translation → Chinese:    Front shows English, back shows sentence + pinyin + audio

Audio → Meaning cards are only generated for notes that have audio files.

Audio files are expected as {sanitize_key(key)}.wav in audio/output/.

Output: sentences.apkg
"""

import argparse
import csv
import hashlib
import re

import genanki
from pathlib import Path

MODEL_ID = 1_718_000_003
DECK_ID  = 1_718_000_002

MODEL = genanki.Model(
    MODEL_ID,
    "WGF Sentence",
    fields=[
        {"name": "Sentence"},
        {"name": "Pinyin"},
        {"name": "Translation"},
        {"name": "Level"},
        {"name": "Register"},
        {"name": "Audio"},
    ],
    templates=[
        {
            "name": "Sentence → Meaning",
            "qfmt": "<div class=sentence>{{Sentence}}</div>",
            "afmt": (
                "{{FrontSide}}<hr>"
                "<div class=pinyin>{{Pinyin}}</div>"
                "<div class=translation>{{Translation}}</div>"
                "<div class=level>{{Level}}</div>"
                "{{#Register}}<div class=register>{{Register}}</div>{{/Register}}"
                "<div class=audio>{{Audio}}</div>"
            ),
        },
        {
            "name": "Audio → Meaning",
            "qfmt": (
                "{{#Audio}}"
                "<div class=prompt>Listen and recall:</div>"
                "<div class=audio>{{Audio}}</div>"
                "{{/Audio}}"
            ),
            "afmt": (
                "{{FrontSide}}<hr>"
                "<div class=sentence>{{Sentence}}</div>"
                "<div class=pinyin>{{Pinyin}}</div>"
                "<div class=translation>{{Translation}}</div>"
                "<div class=level>{{Level}}</div>"
                "{{#Register}}<div class=register>{{Register}}</div>{{/Register}}"
            ),
        },
        {
            "name": "Translation → Chinese",
            "qfmt": (
                "<div class=prompt>How do you say:</div>"
                "<div class=translation>{{Translation}}</div>"
                "<div class=level>{{Level}}</div>"
            ),
            "afmt": (
                "{{FrontSide}}<hr>"
                "<div class=sentence>{{Sentence}}</div>"
                "<div class=pinyin>{{Pinyin}}</div>"
                "{{#Register}}<div class=register>{{Register}}</div>{{/Register}}"
                "{{#Audio}}<div class=audio>{{Audio}}</div>{{/Audio}}"
            ),
        },
    ],
    css="""
        .card { font-family: Arial, sans-serif; text-align: center; }
        .prompt { font-size: 1em; color: #888; margin-bottom: 0.5em; }
        .sentence { font-size: 2em; margin: 0.5em 0; }
        .pinyin { font-size: 1.2em; color: #555; margin: 0.3em 0; }
        .translation { font-size: 1.1em; margin: 0.3em 0; }
        .level { font-size: 0.8em; color: #aaa; margin-top: 1em; }
        .register { font-size: 0.8em; color: #888; font-style: italic; }
        .audio { margin-top: 0.5em; }
    """,
)



def sanitize_key(key: str) -> str:
    """Convert a sentence key to a filesystem-safe filename (without extension)."""
    s = key.replace("|", "_")
    s = s.replace(" ", "_")
    s = re.sub(r'[<>:"/\\?*]', '', s)
    max_bytes = 244
    encoded = s.encode('utf-8')
    if len(encoded) <= max_bytes:
        return s
    h = hashlib.md5(key.encode('utf-8')).hexdigest()[:8]
    while len(s.encode('utf-8')) > max_bytes - 9:
        s = s[:-1]
    return f"{s}_{h}"


def make_key(row, n):
    """Generate sentence key from a cards.tsv row and sentence number."""
    row_type = row.get("type", "")
    name = row.get("name", "")
    if row_type == "grammar":
        grammar_category = row.get("grammar_category", "")
        parts = [p for p in [grammar_category, name] if p]
        return f"g|{'|'.join(parts)}|s{n}"
    else:
        definition = row.get("definition", "")
        return f"w|{name}|{definition}|s{n}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-level", type=int, default=None,
                        help="Only include levels up to this number (e.g. 3 for L1-L3)")
    args = parser.parse_args()

    root = Path(__file__).parent
    cards_path = root / "cards.tsv"
    out_path = root / "sentences.apkg"
    output_dir = root / "audio" / "output"

    deck = genanki.Deck(DECK_ID, "Sentences")
    notes = []
    media_files = []

    with open(cards_path, encoding='utf-8') as f:
        reader = csv.DictReader(f, dialect='excel-tab')
        for row in reader:
            level = row.get("level", "")

            if args.max_level is not None:
                level_num = int(level.lstrip("L")) if level.startswith("L") else 0
                if level_num > args.max_level:
                    continue

            for n in (1, 2, 3):
                sentence = row.get(f"sentence_{n}", "").strip()
                translation = row.get(f"translation_{n}", "").strip()
                if not sentence:
                    continue

                key = make_key(row, n)
                pyin = row.get(f"pinyin_{n}", "").strip()

                # Check for audio file (key-based naming)
                fname = f"{sanitize_key(key)}.wav"
                audio_path = output_dir / fname
                if audio_path.exists():
                    audio_ref = f"[sound:{fname}]"
                    media_files.append(str(audio_path))
                else:
                    audio_ref = ""

                note = genanki.Note(
                    model=MODEL,
                    fields=[
                        sentence,
                        pyin,
                        translation,
                        level,
                        "",
                        audio_ref,
                    ],
                    guid=genanki.guid_for(key),
                )
                notes.append(note)

    # Sort by level so new cards appear in order
    notes.sort(key=lambda n: n.fields[3])
    for note in notes:
        deck.add_note(note)

    pkg = genanki.Package(deck)
    pkg.media_files = media_files
    pkg.write_to_file(out_path)
    audio_count = sum(1 for n in notes if n.fields[5])
    print(f"Wrote {len(notes)} notes to {out_path} ({len(media_files)} audio files bundled)")
    print(f"  → {len(notes)} Sentence → Meaning cards")
    print(f"  → {audio_count} Audio → Meaning cards")
    print(f"  → {len(notes)} Translation → Chinese cards")


if __name__ == "__main__":
    main()
