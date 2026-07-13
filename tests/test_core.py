import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from histo_publication_info_fetch.core import PublicationFetcher, PublicationRecord

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "pdbe"


@pytest.fixture
def fixture_1ao7():
    with open(FIXTURES_DIR / "1ao7.json") as f:
        return f.read()


@pytest.fixture
def publication_record():
    return PublicationRecord(
        pdb_id="1ao7",
        title="Test Title",
        authors=["Author One", "Author Two"],
        release_date="2020-01-01",
        deposition_date="2019-12-01",
        experimental_method="X-ray diffraction",
    )


def test_publication_record_to_dict(publication_record):
    """Test PublicationRecord.to_dict()."""
    d = publication_record.to_dict()

    assert d["pdb_id"] == "1ao7"
    assert d["title"] == "Test Title"
    assert d["authors"] == ["Author One", "Author Two"]
    assert d["release_date"] == "2020-01-01"


def test_publication_record_from_dict(publication_record):
    """Test PublicationRecord.from_dict()."""
    d = publication_record.to_dict()
    record = PublicationRecord.from_dict(d)

    assert record.pdb_id == publication_record.pdb_id
    assert record.title == publication_record.title
    assert record.authors == publication_record.authors


def test_fetcher_write_json(publication_record, tmp_path):
    """Test writing records to JSON."""
    fetcher = PublicationFetcher(cache_dir=tmp_path)
    output = tmp_path / "output.json"

    fetcher.write_json([publication_record], output)

    assert output.exists()
    data = json.loads(output.read_text())

    assert "schema_version" in data
    assert "generated_at" in data
    assert "pdb_ids" in data
    assert "publications" in data
    assert data["pdb_ids"] == ["1ao7"]
    assert len(data["publications"]) == 1
    assert data["publications"][0]["pdb_id"] == "1ao7"


def test_fetcher_write_csv(publication_record, tmp_path):
    """Test writing records to CSV."""
    fetcher = PublicationFetcher(cache_dir=tmp_path)
    output = tmp_path / "output.csv"

    fetcher.write_csv([publication_record], output)

    assert output.exists()
    lines = output.read_text().strip().split("\n")

    # Should have header + 1 record
    assert len(lines) == 2
    assert "pdb_id" in lines[0]
    assert "1ao7" in lines[1]


def test_fetcher_write_csv_empty(tmp_path):
    """Test writing empty records to CSV."""
    fetcher = PublicationFetcher(cache_dir=tmp_path)
    output = tmp_path / "output.csv"

    fetcher.write_csv([], output)

    assert output.exists()
    content = output.read_text()
    assert content == ""


@patch("histo_publication_info_fetch.core.fetch_pdbe_entry")
def test_fetcher_fetch_one(mock_fetch, tmp_path):
    """Test fetching a single PDB code."""
    mock_data = {
        "pdb_id": "1ao7",
        "title": "Test",
        "authors": ["Author"],
        "release_date": "2020-01-01",
        "deposition_date": "2019-12-01",
        "experimental_method": "X-ray diffraction",
    }
    mock_fetch.return_value = mock_data

    fetcher = PublicationFetcher(cache_dir=tmp_path)
    record = fetcher.fetch_one("1ao7")

    assert record.pdb_id == "1ao7"
    assert record.title == "Test"
    mock_fetch.assert_called_once()


@patch("histo_publication_info_fetch.core.fetch_pdbe_entry")
def test_fetcher_fetch_many(mock_fetch, tmp_path):
    """Test fetching multiple PDB codes."""
    mock_data_1 = {
        "pdb_id": "1ao7",
        "title": "Test 1",
        "authors": [],
        "release_date": None,
        "deposition_date": None,
        "experimental_method": None,
    }
    mock_data_2 = {
        "pdb_id": "1hla",
        "title": "Test 2",
        "authors": [],
        "release_date": None,
        "deposition_date": None,
        "experimental_method": None,
    }
    mock_fetch.side_effect = [mock_data_1, mock_data_2]

    fetcher = PublicationFetcher(cache_dir=tmp_path)
    records = fetcher.fetch_many(["1ao7", "1hla"])

    assert len(records) == 2
    assert records[0].pdb_id == "1ao7"
    assert records[1].pdb_id == "1hla"
    assert mock_fetch.call_count == 2
