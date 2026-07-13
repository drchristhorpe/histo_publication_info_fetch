---
name: histo-publication-info-fetch
description: Fetch structure publication metadata for PDB codes from PDBe API. Use when you need to retrieve title, authors, release date, or experimental method for one or more PDB structures.
---

# histo-publication-info-fetch

Fetch structure publication metadata (title, authors, release date, deposition date, experimental method)
for PDB codes from the PDBe API. Output as JSON or CSV, with disk caching to avoid repeated API calls.

## When to use this skill

- Retrieve metadata for a specific PDB code or batch of codes.
- Build a dataset of PDB structure information for a downstream pipeline.
- Enrich a list of PDB ids with author and release information.

## Checking availability

```bash
histo-publication-info-fetch --help
```

If the command is not found, install it:

```bash
uv tool install histo-publication-info-fetch  # or pip install histo_publication_info_fetch
```

When working from a source checkout, use:

```bash
uv run histo-publication-info-fetch ...
```

## Usage

### Fetch metadata for one or more PDB codes

```bash
histo-publication-info-fetch 1ao7 1hla 4ozh --output structures.json
```

Output: JSON file with structure metadata for all three PDBs.

### Fetch with specific format

```bash
histo-publication-info-fetch 1ao7 --format csv --output structures.csv
```

Output: CSV file (header + one row per PDB).

### Refresh from API (bypass cache)

```bash
histo-publication-info-fetch 1ao7 --refresh --output structures.json
```

Default cache location: `~/.cache/histo_publication_info_fetch/`. Use `--cache-dir` to override.

### Multiple codes with flexible input

```bash
histo-publication-info-fetch 1ao7,1hla,4ozh --output structures.json
# or
histo-publication-info-fetch 1ao7 1hla 4ozh --output structures.json
# or echo "1ao7\n1hla\n4ozh" | histo-publication-info-fetch ...
```

## Output interpretation

### JSON format (default)

```json
{
  "schema_version": "0.1.0",
  "generated_at": "2026-07-13T15:49:22.545810+00:00",
  "pdb_ids": ["1ao7", "1hla"],
  "publications": [
    {
      "pdb_id": "1ao7",
      "title": "COMPLEX BETWEEN HUMAN T-CELL RECEPTOR, VIRAL PEPTIDE (TAX), AND HLA-A 0201",
      "authors": [
        "Garboczi, D.N.",
        "Ghosh, P.",
        ...
      ],
      "release_date": "1997-09-17",
      "deposition_date": "19970721",
      "experimental_method": "X-ray diffraction"
    }
    ...
  ]
}
```

- `pdb_ids`: list of requested PDB codes (lowercase).
- `publications`: list of structure records in input order.
- All date fields follow ISO 8601 format (`YYYY-MM-DD`) or PDBe's original format (`YYYYMMDD`).
- `authors`: array of author name strings (as provided by PDBe).

### CSV format

Header: `pdb_id,title,authors,release_date,deposition_date,experimental_method`

- `authors` are semicolon-separated in CSV (`Author1; Author2; ...`).
- One row per PDB code.

## Notes

- **Scope**: structure-level metadata only (what PDBe's `/entry/summary` endpoint provides).
  Journal name, volume, issue, pages, DOI, and abstract are **not** available from this endpoint.
- **Caching**: responses are cached per PDB code (hash of URL), default under `~/.cache/histo_publication_info_fetch/`.
  Use `--refresh` to bypass.
- **PDB codes**: always normalized to lowercase (input, output, cache keys).

## Example

```bash
# Fetch metadata for three structures, save as JSON
histo-publication-info-fetch 1ao7 1hla 4ozh --output tcr_mhc.json

# Review the JSON
cat tcr_mhc.json | jq '.publications[].title'

# Re-run with refresh to update from live API
histo-publication-info-fetch 1ao7 1hla 4ozh --output tcr_mhc.json --refresh
```

Report the result back to the user in whatever form they asked for — this skill only tells you
how to obtain it.

See `docs/PLAN.md` for design rationale and `CHANGELOG.md` for release notes.
