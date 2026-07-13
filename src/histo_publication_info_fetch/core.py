import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from histo_publication_info_fetch.sources.pdbe import fetch_pdbe_entry


@dataclass
class PublicationRecord:
    """A structure publication record from PDBe."""

    pdb_id: str
    title: str | None
    authors: list[str]
    release_date: str | None
    deposition_date: str | None
    experimental_method: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PublicationRecord":
        """Create a PublicationRecord from a dict."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dict."""
        return asdict(self)


class PublicationFetcher:
    """Fetch publication metadata for PDB structures from PDBe API."""

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

        Args:
            pdb_id: PDB code (case-insensitive).

        Returns:
            PublicationRecord.

        Raises:
            ValueError: If the PDB code is invalid.
            requests.RequestException: If the API request fails.
        """
        data = fetch_pdbe_entry(pdb_id, self.cache_dir, refresh=self.refresh)
        return PublicationRecord.from_dict(data)

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
        Write publication records to a JSON file.

        Args:
            records: List of PublicationRecord.
            output_path: Output file path.
        """
        output_path = Path(output_path)
        pdb_ids = [r.pdb_id for r in records]

        envelope = {
            "schema_version": "0.1.0",
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
            "title",
            "authors",
            "release_date",
            "deposition_date",
            "experimental_method",
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                row = record.to_dict()
                row["authors"] = "; ".join(row["authors"]) if row["authors"] else ""
                writer.writerow(row)
