import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.build_csv import fetch_json, merge_entries, to_rows, write_csv


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
ENTRY_A_OLD = {
    "simplified": "爱",
    "pos": ["verb", "noun"],
    "forms": [{"traditional": "愛", "transcriptions": {"pinyin": "ài"}, "meanings": ["old definition"]}]
}


def test_fetch_json_returns_list():
    url = "https://raw.githubusercontent.com/drkameleon/complete-hsk-vocabulary/refs/heads/main/wordlists/exclusive/old/5.json"
    result = fetch_json(url)
    assert isinstance(result, list)
    assert len(result) > 0
    assert "simplified" in result[0]


def test_merge_entries_new_only():
    result = merge_entries([ENTRY_A], [])
    assert "爱" in result
    assert result["爱"]["source"] == "new-HSK3"
    assert result["爱"]["entry"] == ENTRY_A


def test_merge_entries_old_only():
    result = merge_entries([], [ENTRY_B])
    assert "本" in result
    assert result["本"]["source"] == "old-HSK5"
    assert result["本"]["entry"] == ENTRY_B


def test_merge_entries_prefers_new_data():
    result = merge_entries([ENTRY_A], [ENTRY_A_OLD])
    assert result["爱"]["entry"] == ENTRY_A
    assert result["爱"]["source"] == "old-HSK5, new-HSK3"


def test_to_rows_one_row_per_meaning():
    merged = merge_entries([ENTRY_A], [])
    rows = to_rows(merged)
    assert len(rows) == 2  # ENTRY_A has 2 meanings


def test_to_rows_columns():
    merged = merge_entries([ENTRY_A], [])
    row = to_rows(merged)[0]
    assert row["simplified"] == "爱"
    assert row["pinyin"] == "ài"
    assert row["traditional"] == "愛"
    assert row["pos"] == "verb"
    assert row["classifier"] == ""
    assert row["definition"] == "to love"
    assert row["source"] == "new-HSK3"


def test_to_rows_classifier_joined():
    entry = {
        "simplified": "书",
        "pos": ["noun"],
        "forms": [{"traditional": "書", "transcriptions": {"pinyin": "shū"},
                   "meanings": ["book"], "classifiers": ["本", "册"]}]
    }
    merged = merge_entries([entry], [])
    row = to_rows(merged)[0]
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
    merged = merge_entries([entry], [])
    rows = to_rows(merged)
    assert len(rows) == 2
    assert rows[0]["pinyin"] == "hǎo"
    assert rows[1]["pinyin"] == "hào"


def test_to_rows_pos_joined():
    entry = {
        "simplified": "爱",
        "pos": ["verb", "noun"],
        "forms": [{"traditional": "愛", "transcriptions": {"pinyin": "ài"}, "meanings": ["love"]}]
    }
    merged = merge_entries([entry], [])
    row = to_rows(merged)[0]
    assert row["pos"] == "verb, noun"


def test_merge_entries_both_present():
    result = merge_entries([ENTRY_A], [ENTRY_A_OLD, ENTRY_B])
    assert len(result) == 2
    assert result["爱"]["source"] == "old-HSK5, new-HSK3"
    assert result["本"]["source"] == "old-HSK5"


import csv as csv_module

ROW = {"simplified": "爱", "pinyin": "ài", "traditional": "愛",
       "pos": "verb", "classifier": "", "definition": "to love", "source": "new-HSK3"}


def test_write_csv_creates_file(tmp_path):
    out = tmp_path / "out.csv"
    write_csv([ROW], out)
    assert out.exists()


def test_write_csv_header(tmp_path):
    out = tmp_path / "out.csv"
    write_csv([], out)
    with open(out, encoding="utf-8", newline="") as f:
        reader = csv_module.DictReader(f)
        assert reader.fieldnames == ["simplified", "pinyin", "traditional", "pos", "classifier", "definition", "source"]


def test_write_csv_data_row(tmp_path):
    out = tmp_path / "out.csv"
    write_csv([ROW], out)
    with open(out, encoding="utf-8", newline="") as f:
        rows = list(csv_module.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["simplified"] == "爱"
    assert rows[0]["classifier"] == ""
    assert rows[0]["definition"] == "to love"


def test_write_csv_creates_parent_dir(tmp_path):
    out = tmp_path / "subdir" / "out.csv"
    write_csv([], out)
    assert out.exists()
