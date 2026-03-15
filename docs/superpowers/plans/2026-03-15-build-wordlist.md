# Build Wordlist XLSX Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `scripts/build_wordlist.py` — a Python script that reads eight HSK word list text files, deduplicates them globally, and writes a four-column XLSX file ready for pinyin/definition annotation.

**Architecture:** A single script with two pure functions (`load_sources` and `build_wordlist`) plus a `main()` entry point. Tests use `tmp_path` fixtures and in-memory data — no dependency on the real `~/flashcards/source/` directory.

**Tech Stack:** Python 3.7+, `openpyxl` 3.x, `pytest`

---

## Chunk 1: Project scaffold and source-loading logic

### Task 1: Scaffold project structure

**Files:**
- Create: `requirements.txt`
- Create: `scripts/__init__.py` (empty)
- Create: `tests/__init__.py` (empty)

- [ ] **Step 1: Create `requirements.txt`**

```
openpyxl>=3.0
pytest>=7.0
```

- [ ] **Step 2: Create empty init files**

```bash
mkdir -p scripts tests
touch scripts/__init__.py tests/__init__.py
```

- [ ] **Step 3: Verify pytest discovers tests**

```bash
cd /Users/chelsea/worlds-greatest-flashcards && python3 -m pytest tests/ -v
```
Expected: `no tests ran` (0 errors)

- [ ] **Step 4: Commit**

```bash
git add requirements.txt scripts/__init__.py tests/__init__.py
git commit -m "chore: scaffold project structure"
```

---

### Task 2: `load_sources` — read and validate source files

**Files:**
- Create: `tests/test_build_wordlist.py`
- Create: `scripts/build_wordlist.py`

`load_sources(source_pairs)` takes an ordered list of `(label, path)` tuples, verifies all paths exist, reads each file as UTF-8, strips lines, drops blanks, and returns `dict[str, list[str]]` mapping each unique word to the list of labels it appeared in.

- [ ] **Step 1: Write failing tests for `load_sources`**

Create `tests/test_build_wordlist.py`:

```python
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.build_wordlist import load_sources


def test_load_sources_single_file(tmp_path):
    f = tmp_path / "words.txt"
    f.write_text("爱\n本\n读\n", encoding="utf-8")
    result = load_sources([("HSK2-L1", f)])
    assert list(result.keys()) == ["爱", "本", "读"]
    assert result["爱"] == ["HSK2-L1"]


def test_load_sources_deduplicates_across_files(tmp_path):
    f1 = tmp_path / "a.txt"
    f1.write_text("爱\n本\n", encoding="utf-8")
    f2 = tmp_path / "b.txt"
    f2.write_text("本\n读\n", encoding="utf-8")
    result = load_sources([("HSK2-L1", f1), ("HSK2-L2", f2)])
    assert list(result.keys()) == ["爱", "本", "读"]
    assert result["本"] == ["HSK2-L1", "HSK2-L2"]
    assert result["读"] == ["HSK2-L2"]


def test_load_sources_deduplicates_within_file(tmp_path):
    f = tmp_path / "words.txt"
    f.write_text("爱\n爱\n本\n", encoding="utf-8")
    result = load_sources([("HSK2-L1", f)])
    assert list(result.keys()) == ["爱", "本"]
    assert result["爱"] == ["HSK2-L1"]


def test_load_sources_skips_blank_lines(tmp_path):
    f = tmp_path / "words.txt"
    f.write_text("爱\n\n  \n本\n", encoding="utf-8")
    result = load_sources([("HSK2-L1", f)])
    assert list(result.keys()) == ["爱", "本"]


def test_load_sources_strips_whitespace(tmp_path):
    f = tmp_path / "words.txt"
    f.write_text("  爱  \n本\n", encoding="utf-8")
    result = load_sources([("HSK2-L1", f)])
    assert "爱" in result


def test_load_sources_aborts_on_missing_file(tmp_path):
    missing = tmp_path / "nope.txt"
    with pytest.raises(SystemExit) as exc:
        load_sources([("HSK2-L1", missing)])
    assert exc.value.code == 1


def test_load_sources_empty_file_is_ok(tmp_path):
    f = tmp_path / "empty.txt"
    f.write_text("", encoding="utf-8")
    result = load_sources([("HSK2-L1", f)])
    assert result == {}
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
cd /Users/chelsea/worlds-greatest-flashcards && python3 -m pytest tests/test_build_wordlist.py -v
```
Expected: `ImportError` or `ModuleNotFoundError` (file doesn't exist yet)

- [ ] **Step 3: Create `scripts/build_wordlist.py` with `load_sources`**

```python
#!/usr/bin/env python3
"""Build data/words.xlsx from HSK source word lists."""

import sys
from pathlib import Path


def load_sources(source_pairs: list) -> dict:
    """Read source files and return ordered dict: word -> [label, ...]."""
    for label, path in source_pairs:
        if not Path(path).exists():
            print(f"Error: source file not found: {path}", file=sys.stderr)
            sys.exit(1)

    words: dict = {}
    for label, path in source_pairs:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            word = line.strip()
            if not word:
                continue
            if word not in words:
                words[word] = [label]
            elif label not in words[word]:
                words[word].append(label)
    return words
```

- [ ] **Step 4: Run tests to confirm they all pass**

```bash
cd /Users/chelsea/worlds-greatest-flashcards && python3 -m pytest tests/test_build_wordlist.py -v
```
Expected: 7 PASSED

- [ ] **Step 5: Commit**

```bash
git add scripts/build_wordlist.py tests/test_build_wordlist.py
git commit -m "feat: add load_sources with deduplication and validation"
```

---

## Chunk 2: XLSX writing and main entry point

### Task 3: `write_xlsx` — write the word dict to a workbook

**Files:**
- Modify: `scripts/build_wordlist.py`
- Modify: `tests/test_build_wordlist.py`

`write_xlsx(words, output_path)` creates a workbook with a single sheet, writes the header row (`Word`, `Pinyin`, `Definition`, `Sources`), then one data row per entry in `words`, with Sources joined as `", "`. Creates parent directory if needed; exits 1 on failure.

- [ ] **Step 1: Add failing tests for `write_xlsx`**

Append to `tests/test_build_wordlist.py`:

```python
from scripts.build_wordlist import write_xlsx
import openpyxl


def test_write_xlsx_creates_file(tmp_path):
    out = tmp_path / "out.xlsx"
    write_xlsx({"爱": ["HSK2-L1"]}, out)
    assert out.exists()


def test_write_xlsx_header_row(tmp_path):
    out = tmp_path / "out.xlsx"
    write_xlsx({}, out)
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    assert [ws.cell(1, c).value for c in range(1, 5)] == ["Word", "Pinyin", "Definition", "Sources"]


def test_write_xlsx_data_row(tmp_path):
    out = tmp_path / "out.xlsx"
    write_xlsx({"爱": ["HSK2-L1", "HSK3-L1"]}, out)
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    assert ws.cell(2, 1).value == "爱"
    assert ws.cell(2, 2).value is None
    assert ws.cell(2, 3).value is None
    assert ws.cell(2, 4).value == "HSK2-L1, HSK3-L1"


def test_write_xlsx_row_count(tmp_path):
    out = tmp_path / "out.xlsx"
    words = {"爱": ["HSK2-L1"], "本": ["HSK2-L1"], "读": ["HSK2-L2"]}
    write_xlsx(words, out)
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    assert ws.max_row == 4  # 1 header + 3 data


def test_write_xlsx_creates_parent_dir(tmp_path):
    out = tmp_path / "subdir" / "out.xlsx"
    write_xlsx({"爱": ["HSK2-L1"]}, out)
    assert out.exists()


def test_write_xlsx_overwrites_existing(tmp_path):
    out = tmp_path / "out.xlsx"
    write_xlsx({"爱": ["HSK2-L1"]}, out)
    write_xlsx({"本": ["HSK2-L2"]}, out)
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    assert ws.max_row == 2  # only new data, not appended
```

- [ ] **Step 2: Run tests to confirm new ones fail**

```bash
cd /Users/chelsea/worlds-greatest-flashcards && python3 -m pytest tests/test_build_wordlist.py -v
```
Expected: 7 PASSED, 6 FAILED (`ImportError` on `write_xlsx`)

- [ ] **Step 3: Add `write_xlsx` to `scripts/build_wordlist.py`**

Add after `load_sources`:

```python
def write_xlsx(words: dict, output_path) -> None:
    """Write word dict to an XLSX file at output_path."""
    import openpyxl
    output_path = Path(output_path)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error: could not create output directory: {e}", file=sys.stderr)
        sys.exit(1)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Word", "Pinyin", "Definition", "Sources"])
    for word, labels in words.items():
        ws.append([word, None, None, ", ".join(labels)])
    wb.save(output_path)
```

- [ ] **Step 4: Run all tests to confirm they pass**

```bash
cd /Users/chelsea/worlds-greatest-flashcards && python3 -m pytest tests/test_build_wordlist.py -v
```
Expected: 13 PASSED

- [ ] **Step 5: Commit**

```bash
git add scripts/build_wordlist.py tests/test_build_wordlist.py
git commit -m "feat: add write_xlsx"
```

---

### Task 4: `main()` — wire it all together

**Files:**
- Modify: `scripts/build_wordlist.py`

`main()` defines the eight hard-coded `(label, path)` pairs, calls `load_sources`, then `write_xlsx`, and prints a summary line on success.

- [ ] **Step 1: Add `main()` to `scripts/build_wordlist.py`**

Append at the bottom of the file:

```python
SOURCE_BASE = Path.home() / "flashcards" / "source"
REPO_ROOT = Path(__file__).parent.parent

SOURCES = [
    ("HSK2-L1", SOURCE_BASE / "HSK2" / "HSK1.txt"),
    ("HSK2-L2", SOURCE_BASE / "HSK2" / "HSK2.txt"),
    ("HSK2-L3", SOURCE_BASE / "HSK2" / "HSK3.txt"),
    ("HSK2-L4", SOURCE_BASE / "HSK2" / "HSK4.txt"),
    ("HSK2-L5", SOURCE_BASE / "HSK2" / "HSK5.txt"),
    ("HSK3-L1", SOURCE_BASE / "HSK3" / "HSK1.txt"),
    ("HSK3-L2", SOURCE_BASE / "HSK3" / "HSK2.txt"),
    ("HSK3-L3", SOURCE_BASE / "HSK3" / "HSK3.txt"),
]

OUTPUT_PATH = REPO_ROOT / "data" / "words.xlsx"


def main() -> None:
    words = load_sources(SOURCES)
    write_xlsx(words, OUTPUT_PATH)
    print(f"Wrote {len(words)} words to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run all existing tests to confirm nothing broke**

```bash
cd /Users/chelsea/worlds-greatest-flashcards && python3 -m pytest tests/ -v
```
Expected: 13 PASSED

- [ ] **Step 3: Run the script end-to-end**

```bash
cd /Users/chelsea/worlds-greatest-flashcards && python3 scripts/build_wordlist.py
```
Expected output: `Wrote N words to .../data/words.xlsx`

- [ ] **Step 4: Verify the XLSX looks right**

```bash
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('data/words.xlsx')
ws = wb.active
print('Rows:', ws.max_row)
print('Header:', [ws.cell(1,c).value for c in range(1,5)])
print('Row 2:', [ws.cell(2,c).value for c in range(1,5)])
print('Row 3:', [ws.cell(3,c).value for c in range(1,5)])
"
```
Expected: header row + Chinese words in col 1, Sources in col 4.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_wordlist.py data/words.xlsx
git commit -m "feat: add main() and generate initial words.xlsx"
```

---

### Task 5: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add commands section to `CLAUDE.md`**

Add after the Project Overview section:

```markdown
## Commands

```bash
# Generate data/words.xlsx from source files
python3 scripts/build_wordlist.py

# Run tests
python3 -m pytest tests/ -v

# Run a single test
python3 -m pytest tests/test_build_wordlist.py::test_name -v
```

## Data

- `data/words.xlsx` — generated file, committed to repo. Columns: Word, Pinyin (manual), Definition (manual), Sources.
- Re-run `build_wordlist.py` to regenerate from source files.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add commands and data section to CLAUDE.md"
```
