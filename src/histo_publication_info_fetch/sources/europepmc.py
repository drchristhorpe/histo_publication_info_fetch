import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from histo_publication_info_fetch.http import cached_get


def parse_article(json_text: str) -> dict[str, Any]:
    """
    Parse Europe PMC REST API article response.

    Args:
        json_text: JSON response body from Europe PMC API.

    Returns:
        A dict with keys: journal, iso_abbreviation, volume, issue, pages,
        abstract, authors, year, doi, pmid, open_access, in_pmc, in_epmc,
        full_text_urls.
        Missing fields are None.
    """
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return _null_result()

    if not data.get("resultList") or not data["resultList"].get("result"):
        return _null_result()

    article = data["resultList"]["result"][0]

    # Journal details sit at the top level under resultType=lite but move into
    # `journalInfo` under `core`, so read both rather than depending on which
    # result type produced the response.
    journal_info = article.get("journalInfo") or {}
    journal_record = journal_info.get("journal") or {}

    journal = article.get("journalTitle") or journal_record.get("title")
    iso_abbreviation = journal_record.get("isoabbreviation") or journal
    volume = article.get("journalVolume") or journal_info.get("volume")
    issue = article.get("issue") or journal_info.get("issue")
    pages = article.get("pageInfo")
    abstract = article.get("abstractText")
    year = article.get("pubYear") or journal_info.get("yearOfPublication")
    doi = article.get("doi")
    pmid = article.get("pmid")

    # Open-access status and full-text links. `isOpenAccess`, `inPMC` and
    # `inEPMC` are "Y"/"N" flags; `fullTextUrlList` wraps a list of
    # {availability, availabilityCode, documentStyle, site, url}. The last of
    # these only appears with resultType=core.
    open_access = article.get("isOpenAccess")
    in_pmc = article.get("inPMC")
    in_epmc = article.get("inEPMC")
    full_text_urls = article.get("fullTextUrlList")

    # Parse authors from authorString (e.g. "Smith J, Jones B, ...")
    authors = []
    author_string = article.get("authorString")
    if author_string:
        # Split by comma and strip whitespace
        for author in author_string.split(","):
            author = author.strip()
            if author:
                authors.append(author)

    return {
        "journal": journal,
        "iso_abbreviation": iso_abbreviation,
        "volume": volume,
        "issue": issue,
        "pages": pages,
        "abstract": abstract,
        "authors": authors,
        "year": year,
        "doi": doi,
        "pmid": pmid,
        "open_access": open_access,
        "in_pmc": in_pmc,
        "in_epmc": in_epmc,
        "full_text_urls": full_text_urls,
    }


def _null_result() -> dict[str, Any]:
    """Return a dict with all article fields set to None."""
    return {
        "journal": None,
        "iso_abbreviation": None,
        "volume": None,
        "issue": None,
        "pages": None,
        "abstract": None,
        "authors": None,
        "year": None,
        "doi": None,
        "pmid": None,
        "open_access": None,
        "in_pmc": None,
        "in_epmc": None,
        "full_text_urls": None,
    }


def fetch_article_by_doi(doi: str, cache_dir: Path, refresh: bool = False) -> dict[str, Any]:
    """
    Fetch article metadata from Europe PMC by DOI.

    Args:
        doi: Digital Object Identifier (e.g. "10.1093/emboj/16.21.6514").
        cache_dir: Directory for caching API responses.
        refresh: If True, bypass cache and re-fetch.

    Returns:
        Parsed article metadata dict (see parse_article).
    """
    if not doi:
        return _null_result()

    # The DOI must be wrapped in double quotes. Percent-encoding alone is not
    # enough: Europe PMC's query parser reads bare parentheses as grouping
    # syntax, so a DOI like 10.1016/s1074-7613(00)80430-6 matches nothing.
    query = quote(f'DOI:"{doi}"')
    # resultType=core is what returns `abstractText` and `fullTextUrlList`;
    # the default `lite` carries neither.
    url = (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        f"?query={query}&format=json&pageSize=1&resultType=core"
    )

    try:
        json_text = cached_get(url, cache_dir, refresh=refresh)
        return parse_article(json_text)
    except Exception:
        return _null_result()


def fetch_article_by_title_authors(
    title: str, authors: list[str], cache_dir: Path, refresh: bool = False
) -> dict[str, Any]:
    """
    Fetch article metadata from Europe PMC by title and first author (fallback).

    Args:
        title: Article title.
        authors: List of author names; uses first author for the query.
        cache_dir: Directory for caching API responses.
        refresh: If True, bypass cache and re-fetch.

    Returns:
        Parsed article metadata dict (see parse_article), or None dict if not found.
    """
    if not title or not authors:
        return _null_result()

    first_author = authors[0] if authors else ""
    if not first_author:
        return _null_result()

    # Extract last name from author string (e.g. "Garboczi, D.N." -> "Garboczi")
    last_name = first_author.split(",")[0].strip()

    query = quote(f'TITLE:"{title}" AND AUTH:"{last_name}"')
    url = (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        f"?query={query}&format=json&pageSize=1&resultType=core"
    )

    try:
        json_text = cached_get(url, cache_dir, refresh=refresh)
        return parse_article(json_text)
    except Exception:
        return _null_result()
