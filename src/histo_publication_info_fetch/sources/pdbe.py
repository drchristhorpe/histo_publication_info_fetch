import json
from pathlib import Path
from typing import Any

from histo_publication_info_fetch.http import cached_get


def parse_entry_summary(json_text: str, pdb_id: str) -> dict[str, Any]:
    """
    Parse PDBe API entry/summary response.

    Args:
        json_text: JSON response body from PDBe API.
        pdb_id: The PDB code (lowercase), for validation.

    Returns:
        A dict with keys: pdb_id, title, authors (list), release_date,
        experimental_method, deposition_date. Other publication metadata
        (journal, DOI, pages) not available from this endpoint.
    """
    data = json.loads(json_text)

    # PDBe API returns data keyed by lowercase PDB ID (per convention)
    pdb_id_lower = pdb_id.lower()
    if pdb_id_lower not in data:
        raise ValueError(f"PDB id {pdb_id_lower} not found in API response")

    entry = data[pdb_id_lower][0] if isinstance(data[pdb_id_lower], list) else data[pdb_id_lower]

    # Extract authors from entry_authors list
    authors = entry.get("entry_authors", [])
    if authors:
        # Ensure authors are strings
        authors = [str(a) if isinstance(a, str) else a.get("name", "") for a in authors if a]

    # Parse release_date: PDBe returns YYYYMMDD format, convert to YYYY-MM-DD
    release_date_raw = entry.get("release_date")
    release_date = None
    if release_date_raw:
        try:
            # Convert YYYYMMDD to YYYY-MM-DD
            release_date = f"{release_date_raw[:4]}-{release_date_raw[4:6]}-{release_date_raw[6:8]}"
        except (IndexError, ValueError):
            release_date = release_date_raw

    # Experimental method: PDBe returns as a list
    experimental_method = entry.get("experimental_method", [])
    if experimental_method and isinstance(experimental_method, list):
        experimental_method = "; ".join(experimental_method)
    elif not experimental_method:
        experimental_method = None

    return {
        "pdb_id": pdb_id,
        "title": entry.get("title") or None,
        "authors": authors,
        "release_date": release_date,
        "deposition_date": entry.get("deposition_date") or None,
        "experimental_method": experimental_method,
    }


def fetch_pdbe_entry(pdb_id: str, cache_dir: Path, refresh: bool = False) -> dict[str, Any]:
    """
    Fetch and parse a PDB entry from PDBe API.

    Args:
        pdb_id: PDB code (case-insensitive, converted to lowercase).
        cache_dir: Directory for caching API responses.
        refresh: If True, bypass cache and re-fetch.

    Returns:
        Parsed publication record dict (see parse_entry_summary).

    Raises:
        requests.RequestException: If the API request fails.
        ValueError: If the PDB code is invalid.
    """
    pdb_id = pdb_id.lower().strip()
    if not pdb_id or len(pdb_id) != 4:
        raise ValueError(f"Invalid PDB code: {pdb_id}")

    url = f"https://www.ebi.ac.uk/pdbe/api/pdb/entry/summary/{pdb_id}"
    json_text = cached_get(url, cache_dir, refresh=refresh)
    return parse_entry_summary(json_text, pdb_id)
