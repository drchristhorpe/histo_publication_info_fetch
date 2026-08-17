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


def test_doi_query_is_quoted_for_parenthesised_dois():
    """Europe PMC's parser reads bare parentheses as grouping syntax, so a DOI
    like 10.1016/s1074-7613(00)80430-6 matches nothing unless it is quoted.
    Percent-encoding alone is not enough."""
    from unittest.mock import patch

    from histo_publication_info_fetch.sources import europepmc

    with patch.object(europepmc, "cached_get", return_value="{}") as mock_get:
        europepmc.fetch_article_by_doi("10.1016/s1074-7613(00)80430-6", Path("/tmp"))

    url = mock_get.call_args[0][0]
    assert "%22" in url, "the DOI must be wrapped in double quotes"
    assert "resultType=core" in url, "core is required for abstract and full-text links"


def test_parse_article_reads_core_journal_layout():
    """Under resultType=core the journal details move into `journalInfo`;
    parse_article must read either layout."""
    from histo_publication_info_fetch.sources.europepmc import parse_article

    core_response = json.dumps({
        "resultList": {"result": [{
            "pmid": "8624812",
            "doi": "10.1016/s1074-7613(00)80430-6",
            "pageInfo": "215-28",
            "abstractText": "The structure of the human MHC class I molecule",
            "isOpenAccess": "N", "inPMC": "N", "inEPMC": "N",
            "fullTextUrlList": {"fullTextUrl": [{"url": "https://doi.org/x"}]},
            "journalInfo": {
                "volume": "4", "issue": "3", "yearOfPublication": 1996,
                "journal": {"title": "Immunity", "isoabbreviation": "Immunity"},
            },
        }]}
    })

    result = parse_article(core_response)

    assert result["journal"] == "Immunity"
    assert result["iso_abbreviation"] == "Immunity"
    assert result["volume"] == "4"
    assert result["issue"] == "3"
    assert result["year"] == 1996
    assert result["open_access"] == "N"
    assert result["in_pmc"] == "N"
    assert result["in_epmc"] == "N"
    assert len(result["full_text_urls"]["fullTextUrl"]) == 1


def test_parse_article_still_reads_the_lite_layout():
    """The older top-level layout must keep working."""
    from histo_publication_info_fetch.sources.europepmc import parse_article

    lite_response = json.dumps({
        "resultList": {"result": [{
            "journalTitle": "Immunity", "journalVolume": "4", "issue": "3",
            "pageInfo": "215-28", "pubYear": "1996",
        }]}
    })

    result = parse_article(lite_response)

    assert result["journal"] == "Immunity"
    assert result["volume"] == "4"
    assert result["issue"] == "3"
    assert result["year"] == "1996"


def test_null_result_carries_the_new_fields():
    """A miss must still return every key, so callers can read them blindly."""
    from histo_publication_info_fetch.sources.europepmc import parse_article

    result = parse_article("not json")

    for field in ("open_access", "in_pmc", "in_epmc", "full_text_urls", "iso_abbreviation"):
        assert field in result and result[field] is None
