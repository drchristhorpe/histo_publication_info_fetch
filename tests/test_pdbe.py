import json
from pathlib import Path

import pytest

from histo_publication_info_fetch.sources.pdbe import (
    fetch_pdbe_entry,
    parse_entry_summary,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "pdbe"


@pytest.fixture
def fixture_1ao7():
    with open(FIXTURES_DIR / "1ao7.json") as f:
        return f.read()


@pytest.fixture
def fixture_1hla():
    with open(FIXTURES_DIR / "1hla.json") as f:
        return f.read()


def test_parse_entry_summary_1ao7(fixture_1ao7):
    """Test parsing a real PDBe API response for 1ao7."""
    result = parse_entry_summary(fixture_1ao7, "1ao7")

    assert result["pdb_id"] == "1ao7"
    assert result["title"]
    assert "COMPLEX" in result["title"]
    assert "HLA-A" in result["title"]
    assert isinstance(result["authors"], list)
    assert len(result["authors"]) > 0
    assert all(isinstance(a, str) for a in result["authors"])
    assert result["release_date"]
    assert result["experimental_method"]


def test_parse_entry_summary_1hla(fixture_1hla):
    """Test parsing a real PDBe API response for 1hla."""
    result = parse_entry_summary(fixture_1hla, "1hla")

    assert result["pdb_id"] == "1hla"
    assert result["title"]
    assert isinstance(result["authors"], list)
    assert result["release_date"]


def test_parse_entry_summary_fields():
    """Test that all expected fields are present."""
    data = {
        "test": [
            {
                "title": "Test Title",
                "entry_authors": ["Author One", "Author Two"],
                "release_date": "20200101",
                "deposition_date": "20191201",
                "experimental_method": ["X-ray diffraction"],
            }
        ]
    }
    json_text = json.dumps(data)
    result = parse_entry_summary(json_text, "test")

    assert result["pdb_id"] == "test"
    assert result["title"] == "Test Title"
    assert result["authors"] == ["Author One", "Author Two"]
    assert result["release_date"] == "2020-01-01"
    assert result["deposition_date"] == "20191201"
    assert result["experimental_method"] == "X-ray diffraction"


def test_parse_entry_summary_missing_fields():
    """Test parsing when some fields are missing."""
    data = {
        "test": [
            {
                "title": "Test Title",
            }
        ]
    }
    json_text = json.dumps(data)
    result = parse_entry_summary(json_text, "test")

    assert result["pdb_id"] == "test"
    assert result["title"] == "Test Title"
    assert result["authors"] == []
    assert result["release_date"] is None


def test_parse_entry_summary_invalid_pdb_code(fixture_1ao7):
    """Test that invalid PDB codes raise ValueError."""
    with pytest.raises(ValueError):
        parse_entry_summary(fixture_1ao7, "invalid")


def test_fetch_pdbe_entry_invalid_code(tmp_path):
    """Test that invalid PDB codes raise ValueError."""
    with pytest.raises(ValueError):
        fetch_pdbe_entry("toolong", tmp_path)

    with pytest.raises(ValueError):
        fetch_pdbe_entry("", tmp_path)
