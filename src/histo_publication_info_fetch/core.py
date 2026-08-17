import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from histo_publication_info_fetch.sources.europepmc import (
    fetch_article_by_doi,
    fetch_article_by_title_authors,
)
from histo_publication_info_fetch.sources.pdbe import fetch_pdbe_entry


@dataclass
class Author:
    """BibJSON author object."""

    name: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name}


@dataclass
class PublicationRecord:
    """
    A publication record for a PDB structure in BibJSON format.

    Combines structure metadata from PDBe with journal details from Europe PMC.
    """

    # BibJSON core fields
    type: str  # "article" if journal data found, "dataset" otherwise
    title: str | None
    authors: list[Author]
    year: int | None
    journal: str | None
    volume: str | None
    issue: str | None
    pages: str | None
    doi: str | None
    abstract: str | None

    # PDB-specific extensions
    pdb_id: str
    release_date: str | None
    deposition_date: str | None
    experimental_method: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PublicationRecord":
        """Create a PublicationRecord from a dict, converting authors to Author objects."""
        # Convert author strings to Author objects
        authors = data.get("authors", [])
        if authors and isinstance(authors[0], str):
            authors = [Author(name=a) for a in authors]
        elif authors and isinstance(authors[0], dict):
            authors = [Author(**a) if isinstance(a, dict) else a for a in authors]

        data_copy = dict(data)
        data_copy["authors"] = authors
        return cls(**data_copy)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dict, with authors as dicts."""
        d = asdict(self)
        d["authors"] = [{"name": a.name} if isinstance(a, Author) else a for a in d["authors"]]
        return d

    def to_flat_dict(self) -> dict[str, Any]:
        """Convert to a flat dict for CSV output."""
        d = self.to_dict()
        d["authors"] = "; ".join([a["name"] for a in d["authors"]]) if d["authors"] else ""
        return d


class PublicationFetcher:
    """Fetch publication metadata for PDB structures (PDBe + Europe PMC enrichment)."""

    def __init__(self, cache_dir: Path | None = None, refresh: bool = False):
        """
        Initialize the fetcher.

        Args:
            cache_dir: Cache directory for API responses. Defaults to ~/.cache/histo_publication_info_fetch.
            refresh: If True, bypass cache on all requests.
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "histo_publication_info_fetch"
        self.cache_dir = Path(cache_dir)
        self.refresh = refresh

    def fetch_one(self, pdb_id: str) -> PublicationRecord:
        """
        Fetch publication metadata for a single PDB code.

        Two-phase fetch: (1) PDBe for structure metadata + DOI, (2) Europe PMC for
        journal details if DOI available.

        Args:
            pdb_id: PDB code (case-insensitive).

        Returns:
            PublicationRecord in BibJSON format.

        Raises:
            ValueError: If the PDB code is invalid.
            requests.RequestException: If the API request fails.
        """
        # Phase 1: Fetch structure metadata from PDBe (including DOI from publications endpoint)
        pdbe_data = fetch_pdbe_entry(pdb_id, self.cache_dir, refresh=self.refresh)

        # Phase 2: Enrich with journal metadata from Europe PMC
        doi = pdbe_data.get("doi")
        pmc_data = None

        if doi:
            # Try DOI lookup first (most reliable)
            pmc_data = fetch_article_by_doi(doi, self.cache_dir, refresh=self.refresh)
            if not pmc_data.get("journal"):
                # Fallback to title+authors if DOI lookup failed
                title = pdbe_data.get("title")
                authors = pdbe_data.get("authors", [])
                pmc_data = fetch_article_by_title_authors(title, authors, self.cache_dir, refresh=self.refresh)
        else:
            # No DOI; try title+authors as fallback
            title = pdbe_data.get("title")
            authors = pdbe_data.get("authors", [])
            pmc_data = fetch_article_by_title_authors(title, authors, self.cache_dir, refresh=self.refresh)

        # Merge results
        record_data = self._merge_pbe_pmc(pdbe_data, pmc_data or {})
        return PublicationRecord.from_dict(record_data)

    def _merge_pbe_pmc(self, pdbe_data: dict[str, Any], pmc_data: dict[str, Any]) -> dict[str, Any]:
        """
        Merge PDBe structure data with Europe PMC journal data.

        Returns:
            Dict ready for PublicationRecord.from_dict().
        """
        # Use PMC authors if available (fuller author list), otherwise PDBe
        authors = pmc_data.get("authors") or pdbe_data.get("authors", [])

        # Determine record type
        record_type = "article" if pmc_data.get("journal") else "dataset"

        return {
            "type": record_type,
            "title": pdbe_data.get("title"),
            "authors": authors,
            "year": pmc_data.get("year") or pdbe_data.get("publication_year"),
            "journal": pmc_data.get("journal"),
            "volume": pmc_data.get("volume"),
            "issue": pmc_data.get("issue"),
            "pages": pmc_data.get("pages"),
            "doi": pmc_data.get("doi") or pdbe_data.get("doi"),
            "abstract": pmc_data.get("abstract"),
            "pdb_id": pdbe_data.get("pdb_id"),
            "release_date": pdbe_data.get("release_date"),
            "deposition_date": pdbe_data.get("deposition_date"),
            "experimental_method": pdbe_data.get("experimental_method"),
        }

    def fetch_many(self, pdb_ids: list[str]) -> list[PublicationRecord]:
        """
        Fetch publication metadata for multiple PDB codes.

        Args:
            pdb_ids: List of PDB codes.

        Returns:
            List of PublicationRecord, in input order.
        """
        records = []
        for pdb_id in pdb_ids:
            try:
                records.append(self.fetch_one(pdb_id))
            except ValueError as e:
                # Skip invalid codes
                print(f"Warning: {e}")
                continue
        return records

    def write_json(self, records: list[PublicationRecord], output_path: Path | str) -> None:
        """
        Write publication records to a JSON file in BibJSON format.

        Args:
            records: List of PublicationRecord.
            output_path: Output file path.
        """
        output_path = Path(output_path)
        pdb_ids = [r.pdb_id for r in records]

        envelope = {
            "schema_version": "0.2.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pdb_ids": pdb_ids,
            "publications": [r.to_dict() for r in records],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")

    def write_csv(self, records: list[PublicationRecord], output_path: Path | str) -> None:
        """
        Write publication records to a CSV file.

        Args:
            records: List of PublicationRecord.
            output_path: Output file path.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not records:
            output_path.write_text("", encoding="utf-8")
            return

        fieldnames = [
            "pdb_id",
            "type",
            "title",
            "authors",
            "year",
            "journal",
            "volume",
            "issue",
            "pages",
            "doi",
            "abstract",
            "release_date",
            "deposition_date",
            "experimental_method",
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                row = record.to_flat_dict()
                writer.writerow(row)
