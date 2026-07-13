# histo_publication_info_fetch design plan

## 1. Purpose

Fetch structure publication metadata for PDB codes from the PDBe API
(Protein Data Bank in Europe). Given one or more PDB codes, retrieve structured
publication information: title, authors, release date, deposition date, and
experimental method. Primary output: JSON documents keyed by PDB code, optionally
CSV for batch processing.

Single PDB code as the atomic unit — structure analysis tools (like `histo_com`)
and downstream pipelines need publication context alongside structural data.

## 2. Decisions & assumptions made while scoping

These were resolved by inspecting the live PDBe API (not guessed):

- **API endpoint**: PDBe exposes `https://www.ebi.ac.uk/pdbe/api/pdb/entry/summary/{pdb_id}`
  (one request per PDB code, no bulk endpoint). The endpoint provides structure metadata
  but NOT publication-level details (journal, DOI, pages, abstract).
- **PDB code casing**: always lowercase throughout (input converted, output lowercase,
  cache keys lowercase) — consistent with project convention (see CONVENTIONS.md §9).
- **Input granularity**: CLI accepts multiple PDB codes (space-separated, comma-separated,
  or newline-separated from stdin; flexible parsing) — each fetched independently.
- **Structure fields kept**: `title`, `authors` (from `entry_authors` list), `release_date`
  (normalized from YYYYMMDD to YYYY-MM-DD), `deposition_date`, `experimental_method`.
  These match what PDBe's `/entry/summary` endpoint actually returns.
- **Caching strategy**: disk-cached per PDB code, keyed by lowercase PDB id, default
  under `~/.cache/histo_publication_info_fetch/`, with `--refresh` flag to bypass.
- **Design scope**: structure metadata only, no enrichment from secondary sources (PubMed,
  CrossRef). Journal/DOI/pages/abstract are not available from this endpoint; adding them
  would require multi-endpoint orchestration, out of v0.1 scope.

### Post-freeze mid-build correction

Initial design assumed PDBe's `/entry/summary` would provide full publication details
(journal, DOI, pages, abstract) nested under a `publication` key. **Live API inspection
during implementation** found this was incorrect — the endpoint returns only structure
metadata. No `publication` key exists in the response.

**Decision taken**: pivot to "structure publication info" scope (what PDBe provides) rather
than "full publication info" (which would require secondary lookups). This keeps the tool
single-endpoint, fast, and honest about its data source. Journal/DOI enrichment is a good
v0.2 candidate if requested, but not v0.1.

All following sections reflect the corrected implementation.

## 3. Source fetching & parsing

One source module, `pdbe.py`, splits pure parsing from network fetching:

```python
# sources/pdbe.py
def parse_entry_summary(json_text: str, pdb_id: str) -> dict: ...  # extract structure fields from API response
def fetch_pdbe_entry(pdb_id: str, cache_dir: Path, refresh: bool) -> dict: ...  # fetch + cache + parse
```

- PDBe API: `https://www.ebi.ac.uk/pdbe/api/pdb/entry/summary/{pdb_id}` returns
  a JSON object keyed by lowercase PDB id; the value is a list with one entry dict
  containing title, entry_authors, release_date, experimental_method, deposition_date, etc.
- Parser extracts these fields, normalizes release_date from YYYYMMDD to YYYY-MM-DD,
  joins experimental_method array into a semicolon-separated string.
- No multi-PDB bulk endpoint found; per-PDB queries are the standard.

## 4. Collation & normalization

1. For each input PDB code:
   - Lowercase it (input validation).
   - Check cache; if cached and not `--refresh`, use cached response.
   - Fetch from PDBe API otherwise, cache the full entry response.
   - Parse the structure fields, normalize to a flat `StructureRecord`.
2. Assemble result: a list of `StructureRecord` dicts (one per input PDB, in order).

Normalization:
- `entry_authors` (array of strings) from PDBe is passed through as-is to `authors`.
- `release_date` (YYYYMMDD format) is converted to ISO YYYY-MM-DD.
- `experimental_method` (list like `["X-ray diffraction"]`) is joined into a string
  with `"; "` separator.

## 5. JSON Schema (v0.1.0 — initial)

Bundled at `src/histo_publication_info_fetch/schema/publication.schema.json`,
describing the output shape:

```jsonc
{
  "schema_version": "0.1.0",
  "generated_at": "2026-07-13T00:00:00+00:00",
  "pdb_ids": ["1ao7", "1hla"],
  "publications": [
    {
      "pdb_id": "1ao7",
      "title": "COMPLEX BETWEEN HUMAN T-CELL RECEPTOR, VIRAL PEPTIDE (TAX), AND HLA-A 0201",
      "authors": ["Garboczi, D.N.", "Ghosh, P.", ...],
      "release_date": "1997-09-17",
      "deposition_date": "19970721",
      "experimental_method": "X-ray diffraction"
    }
  ]
}
```

- Empty/null fields are set to `null`, not omitted — consistent schema shape.
- `deposition_date` remains in YYYYMMDD format (as returned by PDBe); only `release_date`
  is normalized to ISO YYYY-MM-DD for consistency with downstream tools.

## 6. Library API

```python
from histo_publication_info_fetch import PublicationFetcher, PublicationRecord

fetcher = PublicationFetcher(cache_dir=None, refresh=False)

# Single PDB
record = fetcher.fetch_one("1ao7")  # -> PublicationRecord (dataclass)

# Multiple PDBs, ordered
records = fetcher.fetch_many(["1ao7", "1hla", "4ozh"])  # -> list[PublicationRecord]

# Write to JSON
fetcher.write_json(records, "pubs.json")  # -> pubs.json file

# Write to CSV
fetcher.write_csv(records, "pubs.csv")  # -> pubs.csv file
```

- `PublicationRecord` is a dataclass with fields matching the JSON schema.
- `fetch_one` returns a single record or raises if the PDB code is invalid.
- `fetch_many` returns all records in input order.

## 7. CLI

```
histo-publication-info-fetch [--output FILE] [--format {json,csv}] [--cache-dir DIR] [--refresh] PDB [PDB ...]
```

- `PDB` (positional, one or more): PDB codes to fetch. Can be space-separated, comma-separated,
  or piped via stdin (one per line).
- `--output` (optional): write to this file. Default: write to stdout (JSON lines, one object per line).
- `--format` (default `json`): output format. `json` (pretty-printed JSON document)
  or `csv` (header + rows).
- `--cache-dir` (optional): override `~/.cache/histo_publication_info_fetch`.
- `--refresh` (flag): bypass cache, re-fetch from PDBe.

Rich console output: a summary table (one row per PDB fetched) showing PDB id, title,
release date, and experimental method — human-readable scan of what was fetched.

## 8. Claude skill

`skills/histo-publication-info-fetch/SKILL.md`, same frontmatter shape as siblings.
Documents `histo-publication-info-fetch <pdb_code> [...]` and what the JSON output
contains, so a downstream agent can fetch structure metadata for a PDB on request
("get the structure info for 1ao7", "fetch metadata for these PDBs").

## 9. Package layout

```
histo_publication_info_fetch/
  .gitignore
  .python-version
  pyproject.toml
  README.md
  CLAUDE.md
  CHANGELOG.md
  docs/
    PLAN.md
  src/histo_publication_info_fetch/
    __init__.py
    core.py                # PublicationFetcher, PublicationRecord, write_json/write_csv
    cli.py                 # Click CLI entry point
    http.py                # cached_get(): disk cache, refresh, User-Agent
    py.typed
    sources/
      __init__.py
      pdbe.py              # parse_entry_summary(), fetch_pdbe_entry()
    schema/
      publication.schema.json
  skills/histo-publication-info-fetch/SKILL.md
  tests/
    fixtures/
      pdbe/                # real PDBe API responses for 1ao7, 1hla, 4ozh
    test_pdbe.py
    test_core.py
    test_cli.py
  tmp/
    .gitkeep
```

## 10. Testing plan

- `test_pdbe.py`: parsing `parse_entry_summary()` against committed real PDBe API
  responses (no network, no synthetic fixtures).
- `test_core.py`: `PublicationFetcher`, `write_json`, `write_csv` against pre-populated
  fixture data (monkeypatching the fetch layer).
- `test_cli.py`: Click CLI integration using `click.testing.CliRunner`, fixture-based
  (no live network).
- `jsonschema.validate` test: validate a real collated sample against the bundled schema.

## 11. Workflow

1. Write this plan (done).
2. Scaffold the package layout + `.gitignore`.
3. Implement `http.py` (cached HTTP GET with disk cache and refresh logic).
4. Implement `sources/pdbe.py`: parse function first (fixture-tested), then fetch wrapper.
5. Implement `core.py`: `PublicationFetcher`, `PublicationRecord`, JSON/CSV writers.
6. Implement `cli.py`: Click entry point, argument parsing (flexible PDB input).
7. Write `CHANGELOG.md` as work proceeds (Keep a Changelog format).
8. Write tests against real committed API responses.
9. **Mid-build API discovery**: update PLAN §2, implement, and tests to match actual PDBe
   structure (no full publication metadata).
10. Run the full pipeline live for real PDB codes, output to `tmp/`.
11. Pause for approval — commit and write `README.md` only once approved.
