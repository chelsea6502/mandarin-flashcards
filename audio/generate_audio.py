"""
Generate Qwen3-TTS audio for every sentence in cards.tsv (local, Apple Silicon).

No API key needed — runs fully offline via MLX.

Setup:
  git clone https://github.com/kapi2800/qwen3-tts-apple-silicon.git
  cd qwen3-tts-apple-silicon
  pip install -r requirements.txt
  brew install ffmpeg          # if not already installed
  python main.py               # run once to download a model, then Ctrl-C

Run:
  source qwen3-tts-apple-silicon/.venv/bin/activate
  python generate_audio.py                  # all sentences
  python generate_audio.py --level L1       # one level only
  python generate_audio.py --start 500      # resume from row 500
  python generate_audio.py --all             # all rows (default: audited only)
  python generate_audio.py --changed         # only rows changed in cards.tsv vs git HEAD

Produces one wav file per sentence (random voice each time):
  output/{sanitized_key}.wav   e.g. w_爱_to_love_s1.wav

Copy wavs into Anki media folder:
  ~/Library/Application Support/Anki2/<profile>/collection.media/
"""

import argparse
import csv
import gc
import glob
import hashlib
import io
import os
import random
import re
import shutil
import subprocess
import tempfile

_DIR = os.path.dirname(os.path.abspath(__file__))

import transformers
transformers.logging.set_verbosity_error()

from mlx_audio.tts.generate import generate_audio
from mlx_audio.tts.utils import load_model

# ── Config ────────────────────────────────────────────────────────────────────

MODEL_PATH = os.path.join(_DIR, "models", "Qwen3-TTS-12Hz-1.7B-Base-8bit")

# Preset speaker — options: serena, vivian, uncle_fu, ryan, aiden, ono_anna, sohee, eric, dylan
VOICES = ["vivian", "ryan", "eric"]

OUTPUT_DIR = os.path.join(_DIR, "output")
CARDS_TSV = os.path.join(_DIR, "..", "cards.tsv")
AUDIT_PROGRESS = os.path.join(_DIR, "..", "data", "level_data", "audit_progress.txt")
CHUNK_SIZE = 50


# ── Helpers ──────────────────────────────────────────────────────────────────


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


def read_audit_progress():
    """Read audit_progress.txt and return (level_num, chunk_num) or None."""
    if not os.path.exists(AUDIT_PROGRESS):
        return None
    progress = {}
    with open(AUDIT_PROGRESS, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if '=' in line:
                k, v = line.split('=', 1)
                progress[k.strip()] = v.strip()
    if 'level' in progress and 'chunk' in progress:
        return int(progress['level']), int(progress['chunk'])
    return None


def count_rows_per_level(path):
    """Return dict of level -> row count from cards.tsv."""
    counts = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, dialect='excel-tab'):
            level = row.get("level", "")
            if level:
                counts[level] = counts.get(level, 0) + 1
    return counts


def build_audited_sentence_limit(audit_level, audit_chunk, rows_per_level):
    """Return dict of level -> max sentence count for audited rows.

    Fully audited levels get None (no limit). The partially audited level
    gets a cap based on how many chunks are complete. Levels beyond the
    audit level are excluded (limit 0).
    """
    limits = {}
    for lvl_num in range(1, 7):
        key = f"L{lvl_num}"
        if lvl_num < audit_level:
            limits[key] = None  # fully audited, no cap
        elif lvl_num == audit_level:
            # chunks before audit_chunk are done
            audited_words = (audit_chunk - 1) * CHUNK_SIZE
            limits[key] = audited_words * 3  # 3 sentences per word
        else:
            limits[key] = 0  # not audited yet
    return limits


def sanitize_key(key: str) -> str:
    """Convert a sentence key to a filesystem-safe filename (without extension).

    Keeps the full key if short enough, otherwise truncates and appends a short
    hash for uniqueness. macOS limit is 255 bytes for filenames.
    """
    s = key.replace("|", "_")
    s = s.replace(" ", "_")
    s = re.sub(r'[<>:"/\\?*]', '', s)
    # Leave room for .wav extension (4 bytes) and hash suffix (_abcdef = 7 bytes)
    max_bytes = 244
    encoded = s.encode('utf-8')
    if len(encoded) <= max_bytes:
        return s
    # Truncate to fit, then append a short hash of the full key for uniqueness
    h = hashlib.md5(key.encode('utf-8')).hexdigest()[:8]
    while len(s.encode('utf-8')) > max_bytes - 9:  # 9 = len("_") + 8 hex chars
        s = s[:-1]
    return f"{s}_{h}"


def load_sentences(path: str, level_filter: list[str] | None = None,
                   sentence_limits: dict | None = None) -> list[tuple[str, str, str]]:
    """Return list of (level, sentence, key) from cards.tsv.

    Iterates over sentence_1/2/3 per card row, generating keys inline.
    level_filter: if provided, only include rows whose level is in the list.
    sentence_limits: if provided, dict of level -> max sentences to include
        for that level (None means no limit, 0 means skip entirely).
    """
    rows = []
    level_counts = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, dialect='excel-tab'):
            level = row.get("level", "")
            if not level:
                continue
            if level_filter and str(level) not in level_filter:
                continue
            for n in (1, 2, 3):
                sentence = row.get(f"sentence_{n}", "").strip()
                if not sentence:
                    continue
                key = make_key(row, n)
                if sentence_limits is not None:
                    limit = sentence_limits.get(str(level))
                    if limit is not None:
                        count = level_counts.get(str(level), 0)
                        if count >= limit:
                            continue
                        level_counts[str(level)] = count + 1
                rows.append((str(level), sentence, key))
    return rows


def _read_cards_sentences(source: str) -> dict[str, tuple[str, str]]:
    """Read cards.tsv content and return {key: (sentence, translation)} for all sentences."""
    result = {}
    reader = csv.DictReader(io.StringIO(source), dialect='excel-tab')
    for row in reader:
        for n in (1, 2, 3):
            sentence = row.get(f"sentence_{n}", "").strip()
            translation = row.get(f"translation_{n}", "").strip()
            if sentence:
                key = make_key(row, n)
                result[key] = (sentence, translation)
    return result


def git_changed_keys(tsv_path: str) -> set[str]:
    """Return set of keys for sentences in cards.tsv that changed vs HEAD.

    Reads the current file and the HEAD version, then returns keys whose
    sentence or translation differs (or keys that are new).
    """
    repo_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    rel_path = os.path.relpath(tsv_path, repo_root)

    # Read HEAD version
    result = subprocess.run(
        ["git", "show", f"HEAD:{rel_path}"],
        capture_output=True, text=True, cwd=repo_root,
    )
    old_sentences = {}
    if result.returncode == 0 and result.stdout.strip():
        old_sentences = _read_cards_sentences(result.stdout)

    # Read current version
    with open(tsv_path, encoding='utf-8') as f:
        cur_sentences = _read_cards_sentences(f.read())

    changed = set()
    for key, cur in cur_sentences.items():
        if key not in old_sentences or old_sentences[key] != cur:
            changed.add(key)
    return changed


def wav_filename(key: str) -> str:
    """e.g. w_爱_to_love_s1.wav"""
    return f"{sanitize_key(key)}.wav"


# ── TTS ──────────────────────────────────────────────────────────────────────


def tts(text: str, out_path: str, model, voice: str) -> bool:
    """Generate audio and write .wav to out_path. Returns True on success."""
    with tempfile.TemporaryDirectory() as tmp:
        generate_audio(
            model=model,
            text=text,
            voice=voice,
            lang_code="chinese",
            temperature=0.2,
            max_tokens=600,
            output_path=tmp,
        )
        wav_files = sorted(glob.glob(os.path.join(tmp, "**", "*.wav"), recursive=True))
        if not wav_files:
            print("    ERROR: generate_audio produced no .wav file")
            return False
        raw = wav_files[-1]
        # Trim leading/trailing silence with ffmpeg
        trimmed = os.path.join(tmp, "trimmed.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-i", raw,
             "-af", "silenceremove=start_periods=1:start_silence=0.05:start_threshold=-40dB,"
                     "areverse,silenceremove=start_periods=1:start_silence=0.05:start_threshold=-40dB,areverse,"
                     "loudnorm=I=-16:TP=-1.5:LRA=11,"
                     "adelay=200|200,apad=pad_dur=0.5",
             trimmed],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        shutil.copy2(trimmed if os.path.exists(trimmed) else raw, out_path)
    return True


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Generate TTS audio for cards.tsv sentences")
    parser.add_argument("--level", type=str, default=None, action="append",
                        help="Only generate for these levels (repeatable, e.g. --level L1 --level L2)")
    parser.add_argument("--start", type=str, default=None,
                        help="Start from this key (for resuming, matches key prefix)")
    parser.add_argument("--all", action="store_true",
                        help="Generate audio for all rows, ignoring audit progress")
    parser.add_argument("--changed", action="store_true",
                        help="Only regenerate audio for cards.tsv rows changed vs git HEAD")
    args = parser.parse_args()

    sentence_limits = None
    if not args.all:
        progress = read_audit_progress()
        if progress is None:
            print("No audit_progress.txt found — all levels fully audited, no limit applied.")
        else:
            audit_level, audit_chunk = progress
            rows_per_level = count_rows_per_level(CARDS_TSV)
            sentence_limits = build_audited_sentence_limit(audit_level, audit_chunk, rows_per_level)
            print(f"Audit progress: L{audit_level} chunk {audit_chunk}")
            for lvl_num in range(1, 7):
                key = f"L{lvl_num}"
                lim = sentence_limits[key]
                total = rows_per_level.get(key, 0) * 3
                if lim is None:
                    print(f"  {key}: all {total} sentences")
                elif lim == 0:
                    print(f"  {key}: skipped (not audited)")
                else:
                    print(f"  {key}: {lim}/{total} sentences")

    sentences = load_sentences(CARDS_TSV, level_filter=args.level,
                               sentence_limits=sentence_limits)

    # --changed: filter to only git-changed rows and delete their existing wavs
    if args.changed:
        changed_keys = git_changed_keys(CARDS_TSV)
        if not changed_keys:
            print("No changed rows in cards.tsv vs git HEAD.")
            return
        sentences = [(lv, s, k) for lv, s, k in sentences if k in changed_keys]
        # Delete stale wav files so they get regenerated
        for _, _, k in sentences:
            old_wav = os.path.join(OUTPUT_DIR, wav_filename(k))
            if os.path.exists(old_wav):
                os.remove(old_wav)
                print(f"  Deleted stale: {wav_filename(k)}")
        print(f"{len(sentences)} changed sentences to regenerate")

    print(f"{len(sentences)} sentences to process")
    if not sentences:
        return

    print(f"Loading model: {MODEL_PATH}")
    model = load_model(MODEL_PATH)
    print("Model ready.\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    ok = 0
    fail = 0

    for i, (level, sentence, key) in enumerate(sentences, 1):
        filename = wav_filename(key)
        out_path = os.path.join(OUTPUT_DIR, filename)

        # Skip if already generated
        if os.path.exists(out_path):
            print(f"[{i}/{len(sentences)}] SKIP (exists) {filename}")
            ok += 1
            continue

        voice_name = random.choice(VOICES)
        print(f"[{i}/{len(sentences)}] {filename}  |  {voice_name}  |  {sentence}")

        if tts(sentence, out_path, model, voice_name):
            kb = os.path.getsize(out_path) / 1024
            print(f"  → {out_path} ({kb:.0f} KB)")
            ok += 1
        else:
            print(f"  → FAILED")
            fail += 1

        gc.collect()  # free MLX buffers between sentences

    print(f"\n{'─' * 50}")
    print(f"Done: {ok} succeeded, {fail} failed")
    print(f"Audio files in: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
