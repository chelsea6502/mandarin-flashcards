# Build Grammar XLSX Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `scripts/build_grammar.py` that fetches HSK grammar files from GitHub, parses them into structured rows, and writes `data/grammar.xlsx` with columns: id, name, hsk_level, description, sentence_1, translation_1, sentence_2, translation_2, sentence_3, translation_3.

**Architecture:** Three pure functions (`parse_grammar_points`, `fetch_file`, `write_xlsx`) plus `main()`. `parse_grammar_points` handles all parsing logic and is independently testable with no I/O. `fetch_file` wraps urllib. `write_xlsx` handles openpyxl output. `main()` wires them together.

**Tech Stack:** Python 3.7+ stdlib, openpyxl

**Spec:** `docs/superpowers/specs/2026-03-15-grammar-xlsx-design.md`

---

## Chunk 1: scripts package + parse_grammar_points

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/build_grammar.py` (parse_grammar_points only)
- Create: `tests/test_build_grammar.py`

### Task 1: Create scripts package and skeleton

- [ ] **Step 1: Create `scripts/__init__.py`**

```bash
mkdir -p scripts && touch scripts/__init__.py
```

- [ ] **Step 2: Create `scripts/build_grammar.py` with stub**

```python
from pathlib import Path
import urllib.request
import urllib.error
import openpyxl


COLUMNS = [
    "id", "name", "hsk_level", "description",
    "sentence_1", "translation_1",
    "sentence_2", "translation_2",
    "sentence_3", "translation_3",
]

SOURCES = [
    ("L1",   "https://raw.githubusercontent.com/krmanik/HSK-3.0/main/New%20HSK%20(2021)/HSK%20Grammar/HSK%201.txt"),
    ("L2",   "https://raw.githubusercontent.com/krmanik/HSK-3.0/main/New%20HSK%20(2021)/HSK%20Grammar/HSK%202.txt"),
    ("L3",   "https://raw.githubusercontent.com/krmanik/HSK-3.0/main/New%20HSK%20(2021)/HSK%20Grammar/HSK%203.txt"),
    ("L4",   "https://raw.githubusercontent.com/krmanik/HSK-3.0/main/New%20HSK%20(2021)/HSK%20Grammar/HSK%204.txt"),
    ("L5",   "https://raw.githubusercontent.com/krmanik/HSK-3.0/main/New%20HSK%20(2021)/HSK%20Grammar/HSK%205.txt"),
    ("L6",   "https://raw.githubusercontent.com/krmanik/HSK-3.0/main/New%20HSK%20(2021)/HSK%20Grammar/HSK%206.txt"),
    ("L7-9", "https://raw.githubusercontent.com/krmanik/HSK-3.0/main/New%20HSK%20(2021)/HSK%20Grammar/HSK%207-9.txt"),
]


def parse_grammar_points(text: str, level: str) -> list:
    raise NotImplementedError


def fetch_file(url: str) -> str:
    raise NotImplementedError


def write_xlsx(rows: list, path) -> None:
    raise NotImplementedError


def main():
    raise NotImplementedError


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create `tests/test_build_grammar.py` with imports**

```python
import sys
import pytest
import openpyxl
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.build_grammar import parse_grammar_points, write_xlsx
```

- [ ] **Step 4: Verify import works**

```bash
python3 -m pytest tests/test_build_grammar.py --collect-only
```

Expected: `no tests ran` (not an import error)

---

### Task 2: parse_grammar_points — basic grammar point extraction

- [ ] **Step 1: Write failing test for basic id/name extraction**

Add to `tests/test_build_grammar.py`:

```python
SAMPLE_L1 = """\
A.1 一级语法点
A.1.1 词类
A.1.1.1 名词
【一01】方位名词：上、下、里

书在桌子上。
手机在书包里。
房间里没有人。

A.1.1.2 动词
【一02】能愿动词：会、能
我不会说中文。
明天你能来吗？
"""


def test_parse_extracts_ids():
    rows = parse_grammar_points(SAMPLE_L1, "L1")
    assert len(rows) == 2
    assert rows[0]["id"] == "一01"
    assert rows[1]["id"] == "一02"


def test_parse_extracts_names():
    rows = parse_grammar_points(SAMPLE_L1, "L1")
    assert rows[0]["name"] == "方位名词：上、下、里"
    assert rows[1]["name"] == "能愿动词：会、能"
```

- [ ] **Step 2: Run to verify tests fail**

```bash
python3 -m pytest tests/test_build_grammar.py::test_parse_extracts_ids tests/test_build_grammar.py::test_parse_extracts_names -v
```

Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: Implement parse_grammar_points**

Replace the stub in `scripts/build_grammar.py`:

```python
def parse_grammar_points(text: str, level: str) -> list:
    rows = []
    lines = [line.strip() for line in text.splitlines()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if "【" in line:
            id_start = line.index("【") + 1
            id_end = line.index("】")
            gp_id = line[id_start:id_end]
            gp_name = line[id_end + 1:].strip()
            # Collect candidate lines until next grammar point line
            candidates = []
            i += 1
            while i < len(lines) and "【" not in lines[i]:
                if lines[i]:  # skip blank lines
                    candidates.append(lines[i])
                i += 1
            # Filter to sentences ending with Chinese punctuation
            sentences = [c for c in candidates if c and c[-1] in ("。", "？", "！")][:3]
            # Pad to 3
            while len(sentences) < 3:
                sentences.append("")
            rows.append({
                "id": gp_id,
                "name": gp_name,
                "hsk_level": level,
                "description": "",
                "sentence_1": sentences[0],
                "translation_1": "",
                "sentence_2": sentences[1],
                "translation_2": "",
                "sentence_3": sentences[2],
                "translation_3": "",
            })
        else:
            i += 1
    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_build_grammar.py::test_parse_extracts_ids tests/test_build_grammar.py::test_parse_extracts_names -v
```

Expected: PASS

---

### Task 3: parse_grammar_points — sentence extraction

- [ ] **Step 1: Write failing tests for sentence extraction**

Add to `tests/test_build_grammar.py`:

```python
def test_parse_extracts_sentences():
    rows = parse_grammar_points(SAMPLE_L1, "L1")
    assert rows[0]["sentence_1"] == "书在桌子上。"
    assert rows[0]["sentence_2"] == "手机在书包里。"
    assert rows[0]["sentence_3"] == "房间里没有人。"


def test_parse_skips_phrase_lists():
    """Bare phrase lists without sentence-final punctuation are skipped."""
    text = "【一01】方位名词：上\n\n桌子上 树下\n书在桌子上。\n"
    rows = parse_grammar_points(text, "L1")
    assert rows[0]["sentence_1"] == "书在桌子上。"


def test_parse_fewer_than_three_sentences():
    """Only 2 sentences available — sentence_3 is empty."""
    rows = parse_grammar_points(SAMPLE_L1, "L1")
    # 【一02】 block has exactly 2 sentences
    assert rows[1]["sentence_1"] == "我不会说中文。"
    assert rows[1]["sentence_2"] == "明天你能来吗？"
    assert rows[1]["sentence_3"] == ""


def test_parse_sets_hsk_level():
    rows = parse_grammar_points(SAMPLE_L1, "L3")
    assert rows[0]["hsk_level"] == "L3"
    assert rows[1]["hsk_level"] == "L3"


def test_parse_description_is_empty():
    rows = parse_grammar_points(SAMPLE_L1, "L1")
    assert rows[0]["description"] == ""


def test_parse_translations_are_empty():
    rows = parse_grammar_points(SAMPLE_L1, "L1")
    for row in rows:
        assert row["translation_1"] == ""
        assert row["translation_2"] == ""
        assert row["translation_3"] == ""
```

- [ ] **Step 2: Run to verify tests fail**

```bash
python3 -m pytest tests/test_build_grammar.py -v
```

Expected: several new tests FAIL (the ones just added)

- [ ] **Step 3: Run all tests to verify they now pass (implementation already handles these cases)**

```bash
python3 -m pytest tests/test_build_grammar.py -v
```

Expected: ALL PASS (the implementation from Task 2 already handles phrase list skipping, fewer-than-3 sentences, level and empty fields)

- [ ] **Step 4: Commit**

```bash
git add scripts/__init__.py scripts/build_grammar.py tests/test_build_grammar.py
git commit -m "feat: add parse_grammar_points with tests"
```

---

## Chunk 2: write_xlsx

**Files:**
- Modify: `scripts/build_grammar.py` (implement write_xlsx)
- Modify: `tests/test_build_grammar.py` (add write_xlsx tests)

### Task 4: write_xlsx

- [ ] **Step 1: Write failing tests for write_xlsx**

Add to `tests/test_build_grammar.py`:

```python
GRAMMAR_ROW = {
    "id": "一01",
    "name": "方位名词：上、下、里",
    "hsk_level": "L1",
    "description": "",
    "sentence_1": "书在桌子上。",
    "translation_1": "",
    "sentence_2": "手机在书包里。",
    "translation_2": "",
    "sentence_3": "",
    "translation_3": "",
}


def test_write_xlsx_creates_file(tmp_path):
    out = tmp_path / "grammar.xlsx"
    write_xlsx([GRAMMAR_ROW], out)
    assert out.exists()


def test_write_xlsx_header(tmp_path):
    out = tmp_path / "grammar.xlsx"
    write_xlsx([], out)
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    headers = [ws.cell(1, c).value for c in range(1, 11)]
    assert headers == [
        "id", "name", "hsk_level", "description",
        "sentence_1", "translation_1",
        "sentence_2", "translation_2",
        "sentence_3", "translation_3",
    ]


def test_write_xlsx_data_row(tmp_path):
    out = tmp_path / "grammar.xlsx"
    write_xlsx([GRAMMAR_ROW], out)
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    assert ws.cell(2, 1).value == "一01"
    assert ws.cell(2, 2).value == "方位名词：上、下、里"
    assert ws.cell(2, 3).value == "L1"
    assert ws.cell(2, 4).value in ("", None)
    assert ws.cell(2, 5).value == "书在桌子上。"
    assert ws.cell(2, 6).value in ("", None)


def test_write_xlsx_creates_parent_dir(tmp_path):
    out = tmp_path / "subdir" / "grammar.xlsx"
    write_xlsx([], out)
    assert out.exists()


def test_write_xlsx_empty_string_written_as_none_or_empty(tmp_path):
    """Empty string fields should be None or empty string in xlsx — not the string 'None'."""
    out = tmp_path / "grammar.xlsx"
    write_xlsx([GRAMMAR_ROW], out)
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    val = ws.cell(2, 4).value  # description
    assert val in ("", None)
```

- [ ] **Step 2: Run to verify tests fail**

```bash
python3 -m pytest tests/test_build_grammar.py -k "write_xlsx" -v
```

Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: Implement write_xlsx**

Replace the stub in `scripts/build_grammar.py`:

```python
def write_xlsx(rows: list, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(COLUMNS)
    for row in rows:
        ws.append([row.get(col) or None for col in COLUMNS])
    wb.save(path)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_build_grammar.py -k "write_xlsx" -v
```

Expected: PASS

- [ ] **Step 5: Run full test suite**

```bash
python3 -m pytest tests/test_build_grammar.py -v
```

Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/build_grammar.py tests/test_build_grammar.py
git commit -m "feat: add write_xlsx for grammar with tests"
```

---

## Chunk 3: fetch_file + main()

**Files:**
- Modify: `scripts/build_grammar.py` (implement fetch_file and main)

### Task 5: fetch_file

- [ ] **Step 1: Implement fetch_file**

Replace the stub in `scripts/build_grammar.py`:

```python
def fetch_file(url: str) -> str:
    import sys
    try:
        with urllib.request.urlopen(url) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        sys.exit(1)
```

- [ ] **Step 2: Smoke test fetch_file manually**

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.build_grammar import fetch_file
text = fetch_file('https://raw.githubusercontent.com/krmanik/HSK-3.0/main/New%20HSK%20(2021)/HSK%20Grammar/HSK%201.txt')
print(text[:200])
"
```

Expected: prints first 200 chars of HSK 1 grammar file (Chinese text with section headers)

---

### Task 6: main() + end-to-end run

- [ ] **Step 1: Implement main()**

Replace the stub in `scripts/build_grammar.py`:

```python
def main():
    import sys
    rows = []
    for level, url in SOURCES:
        text = fetch_file(url)
        rows.extend(parse_grammar_points(text, level))
    out = Path(__file__).parent.parent / "data" / "grammar.xlsx"
    write_xlsx(rows, out)
    print(f"Wrote {len(rows)} grammar points to {out}")
```

- [ ] **Step 2: Run the script end-to-end**

```bash
python3 scripts/build_grammar.py
```

Expected: output like `Wrote 4XX grammar points to .../data/grammar.xlsx`

- [ ] **Step 3: Verify the output**

```bash
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('data/grammar.xlsx')
ws = wb.active
print('Headers:', [ws.cell(1,c).value for c in range(1,11)])
print('Row 2:', [ws.cell(2,c).value for c in range(1,11)])
print('Total rows:', ws.max_row)
"
```

Expected:
- Headers match: `['id', 'name', 'hsk_level', 'description', 'sentence_1', 'translation_1', 'sentence_2', 'translation_2', 'sentence_3', 'translation_3']`
- Row 2 shows a real grammar point (id like `一01`, name in Chinese, level `L1`)
- Total rows: 400–550

- [ ] **Step 4: Run full test suite one final time**

```bash
python3 -m pytest tests/test_build_grammar.py -v
```

Expected: ALL PASS

- [ ] **Step 5: Commit everything**

```bash
git add scripts/build_grammar.py data/grammar.xlsx
git commit -m "feat: build_grammar.py generates data/grammar.xlsx from HSK source"
```
