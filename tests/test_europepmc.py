import json
from pathlib import Path

import pytest

from histo_publication_info_fetch.sources.europepmc import (
    fetch_article_by_doi,
    fetch_article_by_title_authors,
    parse_article,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "europepmc"


@pytest.fixture
def fixture_article():
    """Sample Europe PMC API response."""
    return json.dumps({
        "resultList": {
            "result": [
                {
                    "id": "9000000",
                    "pmid": "9000000",
                    "pmcid": "PMC1234567",
                    "doi": "10.1093/emboj/16.21.6514",
                    "title": "Test Article",
                    "journalTitle": "The EMBO Journal",
                    "journalVolume": "16",
                    "issue": "21",
                    "pageInfo": "6514-6525",
                    "pubYear": 1997,
                    "authorString": "Garboczi D, Ghosh P, Utz U",
                    "abstractText": "This is a test abstract.",
                    "isOpenAccess": True,
                    "inEPMC": True,
                    "citedByCount": 42,
                }
            ]
        }
    })


def test_parse_article_success(fixture_article):
    """Test parsing a successful Europe PMC API response."""
    result = parse_article(fixture_article)

    assert result["journal"] == "The EMBO Journal"
    assert result["volume"] == "16"
    assert result["issue"] == "21"
    assert result["pages"] == "6514-6525"
    assert result["year"] == 1997
    assert result["doi"] == "10.1093/emboj/16.21.6514"
    assert result["abstract"] == "This is a test abstract."
    assert len(result["authors"]) == 3
    assert result["authors"][0] == "Garboczi D"


def test_parse_article_empty_response():
    """Test parsing when no results are found."""
    empty_response = json.dumps({"resultList": {"result": []}})
    result = parse_article(empty_response)

    assert result["journal"] is None
    assert result["abstract"] is None


def test_parse_article_invalid_json():
    """Test parsing invalid JSON."""
    result = parse_article("not valid json")

    assert result["journal"] is None
    assert result["abstract"] is None


def test_parse_article_missing_fields(fixture_article):
    """Test parsing when some fields are missing."""
    data = json.loads(fixture_article)
    # Remove some optional fields
    del data["resultList"]["result"][0]["abstractText"]
    del data["resultList"]["result"][0]["doi"]

    result = parse_article(json.dumps(data))

    assert result["journal"] == "The EMBO Journal"
    assert result["abstract"] is None
    assert result["doi"] is None


def test_fetch_article_by_doi_no_doi():
    """Test DOI fetch with empty DOI."""
    # Should return null result immediately without making a request
    result = fetch_article_by_doi("", Path("/tmp"), refresh=False)

    assert result["journal"] is None


def test_fetch_article_by_title_authors_no_title():
    """Test title/author fetch with empty title."""
    # Should return null result immediately without making a request
    result = fetch_article_by_title_authors("", [], Path("/tmp"), refresh=False)

    assert result["journal"] is None


def test_fetch_article_by_title_authors_no_authors():
    """Test title/author fetch with empty author list."""
    # Should return null result if no authors
    result = fetch_article_by_title_authors("Test Article", [], Path("/tmp"), refresh=False)

    assert result["journal"] is None
