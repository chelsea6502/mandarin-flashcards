"""Build the Listening Anki deck from cards.tsv.

One Audio → Meaning card per sentence in cards.tsv, mirroring the Reading
deck. Notes are emitted only when the corresponding audio file exists at
audio/output/{sanitize_key(key)}.m4a.

GUIDs: sentences that also appeared in the legacy hsk4_sentences.tsv reuse
the legacy `l|{word}|{sentence}` key so review history on those notes is
preserved. New sentences use `l|{cards_key}`.

Output: mandarin_listening.apkg
"""

import csv
from pathlib import Path

import genanki

from build_anki import MODEL as MAIN_MODEL, make_key, sanitize_key

LISTENING_MODEL_ID = 1_773_737_749_953
LISTENING_DECK_ID  = 1_718_000_003

AUDIO_TEMPLATE = next(
    t for t in MAIN_MODEL.templates if t["name"] == "Audio → Meaning"
)

LISTENING_MODEL = genanki.Model(
    LISTENING_MODEL_ID,
    "Mandarin Sentence (Listening)",
    fields=MAIN_MODEL.fields,
    templates=[AUDIO_TEMPLATE],
    css=MAIN_MODEL.css,
)


def load_legacy_guid_map(path: Path) -> dict[str, str]:
    """sentence → legacy guid key (l|word|sentence) from hsk4_sentences.tsv."""
    mapping: dict[str, str] = {}
    if not path.exists():
        return mapping
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f, dialect="excel-tab"):
            sentence = r["sentence"].strip()
            word = r["word"].strip()
            if sentence:
                mapping[sentence] = f"l|{word}|{sentence}"
    return mapping


def main():
    root = Path(__file__).parent
    src = root / "cards.tsv"
    out = root / "mandarin_listening.apkg"
    audio_dir = root / "audio" / "output"

    legacy = load_legacy_guid_map(root / "hsk4_sentences.tsv")

    deck = genanki.Deck(LISTENING_DECK_ID, "Listening")
    media_files = []
    note_count = 0
    legacy_reused = 0
    skipped_no_audio = 0
    legacy_claimed: set[str] = set()

    with open(src, encoding="utf-8") as f:
        for row in csv.DictReader(f, dialect="excel-tab"):
            level = row.get("level", "").strip()
            for n in (1, 2, 3):
                sentence = row.get(f"sentence_{n}", "").strip()
                if not sentence:
                    continue

                cards_key = make_key(row, n)
                fname = f"{sanitize_key(cards_key)}.m4a"
                audio_path = audio_dir / fname
                if not audio_path.exists():
                    skipped_no_audio += 1
                    continue

                if sentence in legacy and sentence not in legacy_claimed:
                    guid_key = legacy[sentence]
                    legacy_claimed.add(sentence)
                    legacy_reused += 1
                else:
                    guid_key = f"l|{cards_key}"

                deck.add_note(genanki.Note(
                    model=LISTENING_MODEL,
                    fields=[
                        sentence,
                        row.get(f"pinyin_{n}", "").strip(),
                        row.get(f"translation_{n}", "").strip(),
                        level,
                        "",
                        f"[sound:{fname}]",
                    ],
                    guid=genanki.guid_for(guid_key),
                ))
                media_files.append(str(audio_path))
                note_count += 1

    pkg = genanki.Package(deck)
    pkg.media_files = media_files
    pkg.write_to_file(out)
    print(f"Wrote {note_count} notes to {out}")
    print(f"  → {legacy_reused} reused legacy guids (review history preserved)")
    print(f"  → {note_count - legacy_reused} new notes")
    print(f"  → {skipped_no_audio} sentences skipped (no audio)")


if __name__ == "__main__":
    main()
