"""Check that generated sentences use only HSK 1-4 vocabulary + the row's own word.

The top1000 words are all HSK 5+/off-HSK, so the usual "vocabulary at or below
the row's level" rule from CLAUDE.md has no floor to sit on. The substitute
rule: every sentence may use the target word plus HSK 3.0 L1-L4 words, and
nothing else. That keeps exactly one unknown item per card.

Segmentation uses HanLP coarse-ELECTRA (not jieba). The model is downloaded on
first run and cached by HanLP.

Usage:
    python3 check_vocab.py work/top1000/chunk_0001.tsv
    python3 check_vocab.py cards_top1000.tsv
    python3 check_vocab.py --list-oov <file>   # just the OOV token frequency table
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
HSK_SRC = Path.home() / "hsk-2025-data" / "vocabulary.tsv"

LEVEL_NUM = {"一级": 1, "二级": 2, "三级": 3, "四级": 4,
             "五级": 5, "六级": 6, "七-九级": 7}
LEVEL_TOKEN = re.compile("|".join(LEVEL_NUM))
CJK = re.compile(r"[㐀-䶿一-鿿]")

# Function words, bound morphemes and colloquial particles that the HSK list
# does not enumerate as standalone entries but which are unavoidable in natural
# L1-L4 sentences. Kept deliberately short and reviewed by hand.
EXTRA_ALLOWED = {
    "的", "了", "着", "过", "是", "不", "在", "有", "和", "也", "都", "很",
    "就", "还", "又", "再", "才", "只", "会", "能", "要", "可以", "没",
    "没有", "把", "被", "给", "让", "对", "从", "到", "为", "跟", "比",
    "吗", "呢", "吧", "啊", "呀", "嘛", "的话", "个", "些", "这", "那",
    "哪", "我", "你", "他", "她", "它", "我们", "你们", "他们", "她们",
    "自己", "什么", "怎么", "为什么", "谁", "多少", "几", "上", "下",
    "里", "外", "前", "后", "中", "内", "间", "得", "地", "所以", "因为",
    "但是", "可是", "如果", "虽然", "而且", "或者", "然后", "已经", "正在",
    "一起", "一下", "一点", "一样", "一直", "一定", "一些",
}

PUNCT = set("。！？，、；：·—…《》“”‘’（）")

# Internet memes whose canonical form needs an above-L4 word (车祸现场, 蹭热度,
# 涨粉 …). Each exception is a (rank, phrase) pair: inside that row, any token
# that falls within the phrase is allowed, so the word stays blocked elsewhere.
MEME_SRC = HERE / "meme_exceptions.tsv"


def meme_exceptions() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if MEME_SRC.exists():
        with open(MEME_SRC, encoding="utf-8") as f:
            for r in csv.DictReader(f, dialect="excel-tab"):
                out.setdefault(r["rank"].strip(), []).append(r["phrase"].strip())
    return out


def hsk_levels() -> dict[str, int]:
    """word -> lowest HSK level it appears at (polysemes take the easiest sense)."""
    out: dict[str, int] = {}
    with open(HSK_SRC, encoding="utf-8") as f:
        for r in csv.DictReader(f, dialect="excel-tab"):
            word = r["word"].split("（")[0].strip()
            levels = [LEVEL_NUM[m] for m in LEVEL_TOKEN.findall(r["levelName"])]
            if not word or not levels:
                continue
            lvl = min(levels)
            if word not in out or lvl < out[word]:
                out[word] = lvl
    return out


def load_tokenizer():
    import hanlp
    return hanlp.load(hanlp.pretrained.tok.COARSE_ELECTRA_SMALL_ZH)


def decomposes(token: str, words: set[str], chars: set[str]) -> bool:
    """True if `token` tiles completely into L1-L4 words / L1-L4 characters.

    The HSK list enumerates words, not morphemes, so it has no entry for 别,
    等, 点, or for transparent compounds like 不是, 做完, 三个月, or for verb
    reduplication like 想想. A learner who knows every piece knows the whole,
    so a token that decomposes is not new vocabulary. 软件 does not decompose
    (软 is not an L1-L4 character) and is correctly still flagged.
    """
    n = len(token)
    reachable = [False] * (n + 1)
    reachable[0] = True
    for i in range(n):
        if not reachable[i]:
            continue
        for j in range(i + 1, n + 1):
            piece = token[i:j]
            if piece in words or (j - i == 1 and piece in chars):
                reachable[j] = True
    return reachable[n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--list-oov", action="store_true",
                    help="print only the OOV frequency table")
    ap.add_argument("--max-rows", type=int, default=0,
                    help="check only the first N rows (debugging)")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"missing: {path}", file=sys.stderr)
        return 2

    levels = hsk_levels()
    allowed = {w for w, l in levels.items() if l <= 4} | EXTRA_ALLOWED
    # Characters that appear in any L1-L4 word are themselves known morphemes.
    allowed_chars = {c for w in allowed for c in w if CJK.match(c)}
    print(f"HSK 1-4 vocabulary: {sum(1 for l in levels.values() if l <= 4)} words "
          f"(+{len(EXTRA_ALLOWED)} function words, {len(allowed_chars)} characters)",
          file=sys.stderr)

    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, dialect="excel-tab"))
    if args.max_rows:
        rows = rows[: args.max_rows]

    jobs = []  # (row, n, sentence)
    for row in rows:
        for n in (1, 2, 3):
            s = row[f"sentence_{n}"].strip()
            if s:
                jobs.append((row, n, s))

    tok = load_tokenizer()
    segmented = tok([s for _, _, s in jobs])

    memes = meme_exceptions()
    oov_counter: Counter[str] = Counter()
    violations: list[tuple[str, str, list[str]]] = []

    for (row, n, sentence), tokens in zip(jobs, segmented):
        target = row.get("name") or row["word"]
        phrases = [p for p in memes.get(str(row.get("rank") or row.get("level")), []) if p in sentence]
        bad = []
        for t in tokens:
            if not CJK.search(t) or set(t) <= PUNCT:
                continue
            if t == target or t in target or target in t:
                continue
            if t in allowed:
                continue
            if any(t in p for p in phrases):
                continue  # part of a whitelisted meme phrase in this row
            if t in levels and levels[t] > 4:
                bad.append(t)  # a real HSK 5+ word — decomposition is no excuse
                continue
            if decomposes(t, allowed, allowed_chars):
                continue
            bad.append(t)
        if bad:
            where = f"{target} (#{row.get('level') or row.get('rank')}) s{n}"
            violations.append((where, sentence, bad))
            oov_counter.update(bad)

    if args.list_oov:
        for word, n in oov_counter.most_common():
            lvl = levels.get(word)
            print(f"{n:4d}  {word}  {'L' + str(lvl) if lvl else 'not-in-HSK'}")
        return 1 if violations else 0

    for where, sentence, bad in violations:
        print(f"{where}: {sentence}")
        print(f"    OOV: {' '.join(bad)}")

    print(f"\n{len(violations)} of {len(jobs)} sentences use above-L4 vocabulary")
    print(f"{len(oov_counter)} distinct OOV words")
    if oov_counter:
        top = ", ".join(f"{w}({n})" for w, n in oov_counter.most_common(15))
        print(f"most common: {top}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
