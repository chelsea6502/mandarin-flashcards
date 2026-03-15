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


def fetch_file(url: str) -> str:
    raise NotImplementedError


def write_xlsx(rows: list, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(COLUMNS)
    for row in rows:
        ws.append([row.get(col) or None for col in COLUMNS])
    wb.save(path)


def main():
    raise NotImplementedError


if __name__ == "__main__":
    main()
