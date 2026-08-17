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
        A dict with keys: journal, volume, issue, pages, abstract, authors, year, doi, pmid.
        Missing fields are None.
    """
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return _null_result()

    if not data.get("resultList") or not data["resultList"].get("result"):
        return _null_result()

    article = data["resultList"]["result"][0]

    # Extract fields
    journal = article.get("journalTitle")
    volume = article.get("journalVolume")
    issue = article.get("issue")
    pages = article.get("pageInfo")
    abstract = article.get("abstractText")
    year = article.get("pubYear")
    doi = article.get("doi")
    pmid = article.get("pmid")

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
        "volume": volume,
        "issue": issue,
        "pages": pages,
        "abstract": abstract,
        "authors": authors,
        "year": year,
        "doi": doi,
        "pmid": pmid,
    }


def _null_result() -> dict[str, Any]:
    """Return a dict with all article fields set to None."""
    return {
        "journal": None,
        "volume": None,
        "issue": None,
        "pages": None,
        "abstract": None,
        "authors": None,
        "year": None,
        "doi": None,
        "pmid": None,
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

    query = f"DOI:{quote(doi)}"
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={query}&format=json&pageSize=1"

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

    query = f'TITLE:"{quote(title)}" AND AUTH:"{quote(last_name)}"'
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={query}&format=json&pageSize=1"

    try:
        json_text = cached_get(url, cache_dir, refresh=refresh)
        return parse_article(json_text)
    except Exception:
        return _null_result()
