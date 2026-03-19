# Agent Instructions: Generate Example Sentences

Generate 3 example sentences (with English translations) **per definition** in `cards.tsv`.

Each row in the file is one definition. A word like 好 may appear in multiple rows with different definitions (e.g. "good", "to be fond of") — each definition gets its own independent set of 3 sentences, tailored to that specific meaning.

---

## Your Task

You will be given a filter such as `level=L1` or `level=L2`. Find all rows matching that filter that have empty `sentence_1` cells. Generate sentences for each row in-session (do not call an external API), then write them directly to the TSV.

Batches are always 150 rows.

---

## Step 1: Read the target rows

Read `cards.tsv` using the Read tool with offset/limit to find rows needing sentences. The file is tab-delimited with a header row. Column order:

```
name	pinyin	pos	classifier	definition	level	type	grammar_category	sentence_1	pinyin_1	translation_1	sentence_2	pinyin_2	translation_2	sentence_3	pinyin_3	translation_3
```

Identify rows where `sentence_1` is empty and the level matches your filter.

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
- **Prefer vocabulary at or below the word's HSK level.** For an L2 word, the other words in the sentence should ideally be L1–L2. Avoid introducing vocabulary significantly above the target level — the sentence should be readable by a student who has studied up to that level.
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

## Step 3: Write sentences directly to the TSV

Use the Edit tool to update `cards.tsv` directly. Each row is one line — find the row by its line number and replace the empty sentence/translation fields with your generated content.

Tab-separate all fields. Make sure your edits preserve the existing tab structure.

---

## Step 4: Audit

After writing, read back the rows you edited and verify:
- Every target row has all 3 sentence/translation pairs filled
- The target word appears in each sentence
- No duplicate sentences within a row

Fix any issues by editing the TSV directly.

After the mechanical audit passes, do a **qualitative review** of a random sample (~15 rows). Check:
- Sentences demonstrate the specific definition meaning, not just any usage of the word
- No vocabulary significantly above the HSK level appears in supporting words
- Classifiers are used where the row has them listed (at least once per word)
- Sentences feel natural, not constructed just to include the word

Fix any rows that fail the qualitative check by editing the TSV directly.
