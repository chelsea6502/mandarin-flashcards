"""Build an Anki deck from cards.tsv.

Three sibling card types per note:
  Sentence → Meaning:      Front shows Chinese, back shows pinyin + translation + audio
  Audio → Meaning:          Front plays audio, back shows sentence + pinyin + translation
  Translation → Chinese:    Front shows English, back shows sentence + pinyin + audio

Audio → Meaning cards are only generated for notes that have audio files.

Audio files are expected as {sanitize_key(key)}.m4a in audio/output/.

Output: sentences.apkg
"""

import argparse
import csv
import hashlib
import json
import re

import genanki
from pathlib import Path

MODEL_ID = 1_773_737_749_952
DECK_ID  = 1_718_000_002

TONE_COLOR_SCRIPT = """
<script>
(function() {
  var T1 = /[\u0101\u0113\u012b\u014d\u016b\u01d6]/;
  var T2 = /[\u00e1\u00e9\u00ed\u00f3\u00fa\u01d8]/;
  var T3 = /[\u01ce\u011b\u01d0\u01d2\u01d4\u01da]/;
  var T4 = /[\u00e0\u00e8\u00ec\u00f2\u00f9\u01dc]/;

  var DOT_BELOW_I = '\u1ecb';
  var DOT_BELOW_U = '\u1ee5';

  function toneClass(syl) {
    if (syl.indexOf(DOT_BELOW_I) !== -1) return 'tone1';
    if (syl.indexOf(DOT_BELOW_U) !== -1) return 'tone4';
    if (T1.test(syl)) return 'tone1';
    if (T2.test(syl)) return 'tone2';
    if (T3.test(syl)) return 'tone3';
    if (T4.test(syl)) return 'tone4';
    return 'tone0';
  }

  function colorize(el) {
    if (!el) return;
    var text = el.textContent;
    var parts = text.split(/(\\s+)/);
    var html = '';
    for (var i = 0; i < parts.length; i++) {
      var p = parts[i];
      if (/^\\s+$/.test(p)) { html += p; continue; }
      if (!/[a-zA-Z\\u00C0-\\u024F\\u1E00-\\u1EFF]/.test(p)) { html += p; continue; }
      var cls = toneClass(p);
      html += '<span class="' + cls + '">' + p + '</span>';
    }
    el.innerHTML = html;
  }

  document.querySelectorAll('.pinyin').forEach(colorize);
})();
</script>
"""

MODEL = genanki.Model(
    MODEL_ID,
    "Mandarin Sentence",
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
                "<div class=audio>{{Audio}}</div>"
                + TONE_COLOR_SCRIPT
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
                + TONE_COLOR_SCRIPT
            ),
        },
        {
            "name": "Translation → Chinese",
            "qfmt": (
                "<div class=prompt>How do you say:</div>"
                "<div class=translation>{{Translation}}</div>"
            ),
            "afmt": (
                "{{FrontSide}}<hr>"
                "<div class=sentence>{{Sentence}}</div>"
                "<div class=pinyin>{{Pinyin}}</div>"
                "{{#Audio}}<div class=audio>{{Audio}}</div>{{/Audio}}"
                + TONE_COLOR_SCRIPT
            ),
        },
    ],
    css="""
        .card {
  font-family: Arial, sans-serif;
  text-align: center;
  position: absolute;
  top: 0; right: 0; bottom: 0; left: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}
        .prompt { font-size: 1em; color: #888; margin-bottom: 0.5em; }
        .sentence { font-size: 2em; margin: 0.5em 0; }
        .pinyin { font-size: 1.5em; color: #888; margin: 0.3em 0; }
        .translation { font-size: 2em; margin: 0.3em 0; }
        .level { font-size: 0.8em; color: #aaa; margin-top: 1em; }
        .register { font-size: 0.8em; color: #888; font-style: italic; }
        .audio { margin-top: 0.5em; }

.tone1 { color: #5daa5d; }
.tone2 { color: #c9a04a; }
.tone3 { color: #c06060; }
.tone4 { color: #6a9ad8; }
.tone0 { color: #aaaaaa; }
    """,
)



def sanitize_key(key: str) -> str:
    """Convert a sentence key to a filesystem-safe filename (without extension)."""
    s = key.replace("|", "_")
    s = s.replace(" ", "_")
    s = re.sub(r'[<>:"/\\?*]', '', s)
    max_bytes = 114
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
    parser.add_argument("--max-level", type=int, default=4,
                        help="Only include levels up to this number (e.g. 3 for L1-L3)")
    parser.add_argument("--card-type", type=str, default=None,
                        choices=["sentence", "audio", "translation"],
                        help="Only include this card type (default: all)")
    args = parser.parse_args()

    # Filter templates if --card-type specified
    if args.card_type:
        type_prefix = {"sentence": "Sentence", "audio": "Audio", "translation": "Translation"}
        prefix = type_prefix[args.card_type]
        model = genanki.Model(
            MODEL_ID,
            MODEL.name,
            fields=MODEL.fields,
            templates=[t for t in MODEL.templates if t["name"].startswith(prefix)],
            css=MODEL.css,
        )
    else:
        model = MODEL

    root = Path(__file__).parent
    cards_path = root / "cards.tsv"
    out_path = root / "mandarin.apkg"
    output_dir = root / "audio" / "output"

    # Load HSK 2.0 L4 word list for priority sorting
    hsk2_l4_path = root / "hsk2_l4.json"
    if hsk2_l4_path.exists():
        with open(hsk2_l4_path, encoding='utf-8') as f:
            hsk2_l4_words = set(json.load(f))
    else:
        hsk2_l4_words = set()

    deck = genanki.Deck(DECK_ID, "Mandarin")
    notes = []  # list of (level, sentence_text, note)
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
                fname = f"{sanitize_key(key)}.m4a"
                audio_path = output_dir / fname
                if audio_path.exists():
                    audio_ref = f"[sound:{fname}]"
                    media_files.append(str(audio_path))
                else:
                    audio_ref = ""

                note = genanki.Note(
                    model=model,
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
                notes.append((level, sentence, note))

    # Greedy set-cover: order notes to cover HSK 2.0 L4 words as fast as possible.
    # For each note, find which L4 words appear in its sentence text.
    # Greedily pick notes that cover the most uncovered L4 words first.
    if hsk2_l4_words:
        # Precompute L4 words in each sentence
        note_l4_words = []
        for level, sentence, note in notes:
            found = frozenset(w for w in hsk2_l4_words if w in sentence)
            note_l4_words.append(found)

        uncovered = set(hsk2_l4_words)
        ordered = []
        remaining = list(range(len(notes)))

        # Phase 1: greedily pick notes that cover uncovered L4 words
        while uncovered and remaining:
            best_idx = None
            best_score = (-1, "")
            for i in remaining:
                new_covered = len(note_l4_words[i] & uncovered)
                if new_covered > 0:
                    # Break ties by level (lower first)
                    score = (new_covered, notes[i][0])
                    if best_idx is None or score[0] > best_score[0] or (
                        score[0] == best_score[0] and score[1] < best_score[1]
                    ):
                        best_idx = i
                        best_score = score
            if best_idx is None:
                break
            ordered.append(best_idx)
            uncovered -= note_l4_words[best_idx]
            remaining.remove(best_idx)

        # Phase 2: remaining notes sorted by level
        remaining.sort(key=lambda i: notes[i][0])
        ordered.extend(remaining)

        notes = [notes[i] for i in ordered]
        hsk2_count = len(ordered) - len(remaining)
        covered_count = len(hsk2_l4_words) - len(uncovered)
        print(f"Set-cover: {covered_count}/{len(hsk2_l4_words)} HSK 2.0 L4 words covered in first {hsk2_count} notes")
    else:
        notes.sort(key=lambda t: t[0])

    for _, _, note in notes:
        deck.add_note(note)

    pkg = genanki.Package(deck)
    pkg.media_files = media_files
    pkg.write_to_file(out_path)
    audio_count = sum(1 for _, _, n in notes if n.fields[5])
    print(f"Wrote {len(notes)} notes to {out_path} ({len(media_files)} audio files bundled)")
    print(f"  → {len(notes)} Sentence → Meaning cards")
    print(f"  → {audio_count} Audio → Meaning cards")
    print(f"  → {len(notes)} Translation → Chinese cards")


if __name__ == "__main__":
    main()
