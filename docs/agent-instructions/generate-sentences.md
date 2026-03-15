# Agent Instructions: Generate Example Sentences

Generate 3 example sentences (with English translations) **per definition** in `data/words.xlsx`.

Each row in the sheet is one definition. A word like 好 may appear in multiple rows with different definitions (e.g. "good", "to be fond of") — each definition gets its own independent set of 3 sentences, tailored to that specific meaning.

---

## Your Task

You will be given a filter such as `--old-hsk L1` or `--new-hsk L2`. Find all rows matching that filter that have empty `sentence_1` cells. Generate sentences for each row in-session (do not call an external API), then write them directly to the XLSX.

Batches are always 150 rows.

---

## Step 1: Read the target rows

Run this to see what needs filling:

```python
import openpyxl
from pathlib import Path

wb = openpyxl.load_workbook('data/words.xlsx')
ws = wb.active
headers = [ws.cell(1, c).value for c in range(1, ws.max_column+1)]
col = {h: i+1 for i, h in enumerate(headers)}

FILTER_COL = 'old_hsk'   # or 'new_hsk'
FILTER_VAL = 'L1'        # e.g. L1, L2, L3

rows = []
for r in range(2, ws.max_row+1):
    if ws.cell(r, col[FILTER_COL]).value == FILTER_VAL \
       and not ws.cell(r, col['sentence_1']).value:
        rows.append({
            'row': r,
            'simplified': ws.cell(r, col['simplified']).value,
            'pinyin':     ws.cell(r, col['pinyin']).value,
            'definition': ws.cell(r, col['definition']).value,
        })

for x in rows:
    print(x['row'], x['simplified'], x['pinyin'], x['definition'])
```

---

## Step 2: Generate sentences

For each row (= one definition), generate **3 sentences**. Each set of sentences belongs to that definition only — if the same word appears in another row with a different definition, that row gets its own entirely separate set of sentences.

### Sentence rules
- **Each sentence must contain the target word** (simplified characters).
- Sentences should be **natural, everyday Mandarin** — not textbook-stilted.
- Complexity should match the HSK level:
  - L1/L2: very simple structures, high-frequency vocabulary only
  - L3/L4: can introduce slightly more complex grammar
  - L5+: normal adult-level sentences
- **Prefer vocabulary at or below the word's HSK level.** For an old HSK L2 word, the other words in the sentence should ideally be old HSK L1–L2. Avoid introducing vocabulary significantly above the target level — the sentence should be readable by a student who has studied up to that level.
- **Sentences must demonstrate the specific meaning in the `definition` column.** If 好 appears twice — once as "good" and once as "to be fond of" — the sentences for each row must use that specific sense. Do not write generic sentences that could apply to any meaning of the word.
- Vary sentence types across the 3 (statement, question, dialogue snippet, etc.).
- If the row's `classifier` column is non-empty, **integrate at least one of those classifiers into one of the three sentences** (e.g. if the classifier for 书 is 本, write a sentence like 我有三本书). This reinforces the correct measure word alongside the noun.
- For **grammatical particles** (的, 了, 吗, 呢, 着, 过…): ensure the sentence clearly demonstrates the grammatical function described, not just incidental use.
- For **measure words** (个, 本, 块, 张…): show the measure word in a counting context.
- For **numbers** (一 through 十, 零): use the numeral naturally — don't rely on it appearing only as part of a compound.

### Translation rules
- Translations should be natural English, not word-for-word.
- Preserve the nuance of the Chinese.
- For dialogue snippets (A/B format), translate both turns.

---

## Step 3: Write a Python script with the data

Create `scripts/write_sentences_<filter>.py` (e.g. `write_sentences_old_hsk_l2.py`).

Structure:

```python
#!/usr/bin/env python3
from pathlib import Path
import openpyxl

REPO_ROOT = Path(__file__).parent.parent
XLSX_PATH = REPO_ROOT / "data" / "words.xlsx"

# row_number: [(sentence, translation), (sentence, translation), (sentence, translation)]
SENTENCES = {
    <row_num>: [
        ("<sentence 1>", "<translation 1>"),
        ("<sentence 2>", "<translation 2>"),
        ("<sentence 3>", "<translation 3>"),
    ],
    # ... one entry per row
}


def main():
    wb = openpyxl.load_workbook(XLSX_PATH)
    ws = wb.active
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    col = {h: i + 1 for i, h in enumerate(headers)}

    for row_num, sentences in SENTENCES.items():
        for i, (sentence, translation) in enumerate(sentences, 1):
            ws.cell(row_num, col[f"sentence_{i}"]).value = sentence
            ws.cell(row_num, col[f"translation_{i}"]).value = translation

    wb.save(XLSX_PATH)
    print(f"Filled {len(SENTENCES)} rows in {XLSX_PATH}")


if __name__ == "__main__":
    main()
```

---

## Step 4: Run the script

```bash
python3 scripts/write_sentences_<filter>.py
```

---

## Step 5: Audit

Run this audit after writing:

```python
import openpyxl

wb = openpyxl.load_workbook('data/words.xlsx')
ws = wb.active
headers = [ws.cell(1, c).value for c in range(1, ws.max_column+1)]
col = {h: i+1 for i, h in enumerate(headers)}

FILTER_COL = 'old_hsk'
FILTER_VAL = 'L1'

issues = []
for r in range(2, ws.max_row+1):
    if ws.cell(r, col[FILTER_COL]).value != FILTER_VAL:
        continue
    word = ws.cell(r, col['simplified']).value
    defn = ws.cell(r, col['definition']).value
    sentences = []
    for i in range(1, 4):
        s = ws.cell(r, col[f'sentence_{i}']).value or ''
        t = ws.cell(r, col[f'translation_{i}']).value or ''
        if not s:
            issues.append(f'MISSING sentence_{i}: row {r} {word}')
        elif word not in s:
            issues.append(f'WORD NOT IN SENTENCE: row {r} {word} ({defn}) | {s}')
        sentences.append(s)
    if len(set(sentences)) < 3:
        issues.append(f'DUPLICATE sentences: row {r} {word}')

print(f'Issues: {len(issues)}')
for iss in issues:
    print(iss)
```

Fix any issues before finishing. Zero issues is the target.

After the mechanical audit passes, do a **qualitative review** of a random sample (~15 rows). Check:
- Sentences demonstrate the specific definition meaning, not just any usage of the word
- No vocabulary significantly above the HSK level appears in supporting words
- Classifiers are used where the row has them listed (at least once per word)
- Sentences feel natural, not constructed just to include the word

Fix any rows that fail the qualitative check by updating the SENTENCES dict and re-running the script.
