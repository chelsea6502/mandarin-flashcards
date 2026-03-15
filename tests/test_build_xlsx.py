import sys
import pytest
import openpyxl
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.build_xlsx import load_words, load_hsk_levels, to_rows, write_xlsx, fetch_anki_definitions, split_meaning


ENTRY_A = {
    "simplified": "爱",
    "pos": ["verb"],
    "forms": [{"traditional": "愛", "transcriptions": {"pinyin": "ài"}, "meanings": ["to love", "to like"]}]
}
ENTRY_B = {
    "simplified": "本",
    "pos": ["noun"],
    "forms": [{"traditional": "本", "transcriptions": {"pinyin": "běn"}, "meanings": ["root", "origin"]}]
}

def test_load_words_returns_list(tmp_path):
    data = [{"simplified": "爱", "pos": ["verb"], "forms": []}]
    f = tmp_path / "test.json"
    f.write_text(__import__("json").dumps(data), encoding="utf-8")
    result = load_words(f)
    assert isinstance(result, list)
    assert result[0]["simplified"] == "爱"



def test_to_rows_one_row_per_meaning():
    rows = to_rows([ENTRY_A])
    assert len(rows) == 2  # ENTRY_A has 2 meanings


def test_to_rows_columns():
    row = to_rows([ENTRY_A])[0]
    assert row["simplified"] == "爱"
    assert row["pinyin"] == "ài"
    assert row["traditional"] == "愛"
    assert row["pos"] == "verb"  # ENTRY_A has pos=["verb"] — not an abbreviated tag
    assert row["classifier"] == ""
    assert row["definition"] == "to love"
    assert row["new_hsk"] == ""


def test_load_hsk_levels(tmp_path):
    # Write all required level files; only 1 and 2 have content
    (tmp_path / "hsk_level1.txt").write_text("爱\n八\n", encoding="utf-8")
    (tmp_path / "hsk_level2.txt").write_text("本\n", encoding="utf-8")
    for level in [3, 4, 5, 6, "7-9"]:
        (tmp_path / f"hsk_level{level}.txt").write_text("", encoding="utf-8")
    levels = load_hsk_levels(tmp_path)
    assert levels["爱"] == "L1"
    assert levels["八"] == "L1"
    assert levels["本"] == "L2"


def test_to_rows_uses_levels():
    row = to_rows([ENTRY_A], levels={"爱": "L1"})[0]
    assert row["new_hsk"] == "L1"


def test_to_rows_missing_level_is_empty():
    row = to_rows([ENTRY_A], levels={})[0]
    assert row["new_hsk"] == ""


def test_to_rows_classifier_joined():
    entry = {
        "simplified": "书",
        "pos": ["noun"],
        "forms": [{"traditional": "書", "transcriptions": {"pinyin": "shū"},
                   "meanings": ["book"], "classifiers": ["本", "册"]}]
    }
    row = to_rows([entry])[0]
    assert row["classifier"] == "本, 册"


def test_to_rows_multiple_forms():
    entry = {
        "simplified": "好",
        "pos": ["adjective"],
        "forms": [
            {"traditional": "好", "transcriptions": {"pinyin": "hǎo"}, "meanings": ["good"]},
            {"traditional": "好", "transcriptions": {"pinyin": "hào"}, "meanings": ["to be fond of"]},
        ]
    }
    rows = to_rows([entry])
    assert len(rows) == 2
    assert rows[0]["pinyin"] == "hǎo"
    assert rows[1]["pinyin"] == "hào"


def test_to_rows_pos_joined():
    entry = {
        "simplified": "爱",
        "pos": ["verb", "noun"],
        "forms": [{"traditional": "愛", "transcriptions": {"pinyin": "ài"}, "meanings": ["love"]}]
    }
    row = to_rows([entry])[0]
    assert row["pos"] == "verb, noun"  # not abbreviated tags, passed through as-is


def test_to_rows_anki_fallback():
    """Words use anki_defs when available."""
    rows = to_rows([ENTRY_A], anki_defs={"爱": ["anki definition"]})
    assert len(rows) == 1
    assert rows[0]["definition"] == "anki definition"


def test_split_meaning_on_semicolon():
    assert split_meaning("to love; to like") == ["to love", "to like"]
    assert split_meaning("no semicolon") == ["no semicolon"]
    assert split_meaning("a; b; c") == ["a", "b", "c"]
    assert split_meaning("trailing;") == ["trailing"]


def test_to_rows_splits_definitions_on_semicolon():
    """Anki definitions containing semicolons produce one row per part."""
    rows = to_rows([ENTRY_A], anki_defs={"爱": ["to love; to like"]})
    assert len(rows) == 2
    assert rows[0]["definition"] == "to love"
    assert rows[1]["definition"] == "to like"


def test_fetch_anki_definitions_parses_correctly(tmp_path):
    """Build a minimal .apkg and verify parsing."""
    import zipfile, sqlite3, json as json_mod

    db_path = tmp_path / "collection.anki2"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE notes (flds TEXT)")
    conn.execute("CREATE TABLE col (models TEXT)")
    flds = "\x1f".join([
        "爱",                  # word
        "",                    # interferences
        "<table><tbody><tr><th>{{c1::ài}}</th></tr>"
        "<tr><td>㊀ {{c1::to love}}<br>㊁ {{c1::to like}}</td></tr></tbody></table>",
        "", "", "", ""
    ])
    conn.execute("INSERT INTO notes VALUES (?)", (flds,))
    conn.execute("INSERT INTO col VALUES (?)", (json_mod.dumps({}),))
    conn.commit()
    conn.close()

    apkg_path = tmp_path / "test.apkg"
    with zipfile.ZipFile(apkg_path, "w") as z:
        z.write(db_path, "collection.anki2")

    result = fetch_anki_definitions(apkg_path)
    assert "爱" in result
    assert result["爱"] == ["to love", "to like"]



ROW = {
    "simplified": "爱", "pinyin": "ài", "traditional": "愛",
    "pos": "verb", "classifier": "", "definition": "to love",
    "new_hsk": "L3",
    "sentence_1": "", "translation_1": "",
    "sentence_2": "", "translation_2": "",
    "sentence_3": "", "translation_3": "",
}


def test_write_xlsx_creates_file(tmp_path):
    out = tmp_path / "out.xlsx"
    write_xlsx([ROW], out)
    assert out.exists()


def test_write_xlsx_header(tmp_path):
    out = tmp_path / "out.xlsx"
    write_xlsx([], out)
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    assert [ws.cell(1, c).value for c in range(1, 14)] == [
        "simplified", "pinyin", "traditional", "pos", "classifier", "definition",
        "new_hsk",
        "sentence_1", "translation_1",
        "sentence_2", "translation_2",
        "sentence_3", "translation_3",
    ]


def test_write_xlsx_data_row(tmp_path):
    out = tmp_path / "out.xlsx"
    write_xlsx([ROW], out)
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    assert ws.cell(2, 1).value == "爱"
    assert ws.cell(2, 5).value in ("", None)
    assert ws.cell(2, 6).value == "to love"


def test_write_xlsx_creates_parent_dir(tmp_path):
    out = tmp_path / "subdir" / "out.xlsx"
    write_xlsx([], out)
    assert out.exists()


def test_write_xlsx_merges_same_word_rows(tmp_path):
    base = {"simplified": "爱", "pinyin": "ài", "traditional": "愛", "pos": "verb",
            "classifier": "", "new_hsk": "L3",
            "sentence_1": "", "translation_1": "",
            "sentence_2": "", "translation_2": "",
            "sentence_3": "", "translation_3": ""}
    rows = [
        {**base, "definition": "to love"},
        {**base, "definition": "to like"},
    ]
    out = tmp_path / "out.xlsx"
    write_xlsx(rows, out)
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    merged_ranges = [str(r) for r in ws.merged_cells.ranges]
    # simplified (col 1) should be merged across rows 2-3
    assert "A2:A3" in merged_ranges
    # definition (col 6) should NOT be merged
    assert not any("F2" in r for r in merged_ranges)


def test_write_xlsx_no_merge_single_definition(tmp_path):
    out = tmp_path / "out.xlsx"
    write_xlsx([ROW], out)
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    assert len(list(ws.merged_cells.ranges)) == 0
