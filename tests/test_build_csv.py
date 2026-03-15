import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.build_csv import fetch_json, merge_entries, to_rows, write_csv


def test_fetch_json_returns_list():
    url = "https://raw.githubusercontent.com/drkameleon/complete-hsk-vocabulary/refs/heads/main/wordlists/exclusive/old/5.json"
    result = fetch_json(url)
    assert isinstance(result, list)
    assert len(result) > 0
    assert "simplified" in result[0]
