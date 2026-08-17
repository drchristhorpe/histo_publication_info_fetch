# histo_publication_info_fetch design plan

## 1. Purpose

Fetch complete publication metadata for PDB codes from PDBe API endpoints. Given one or
more PDB codes, retrieve: structure metadata (title, authors, release date, experimental
method), publication details (journal, volume, issue, pages, DOI, abstract), and output
as BibJSON.

Primary output: JSON documents in BibJSON format, optionally CSV for batch processing.
Single PDB code as the atomic unit — structure analysis tools and downstream pipelines
need publication context alongside structural data.

## 2. Decisions & assumptions made while scoping

### v0.1 decisions (structure metadata only)

These were resolved by inspecting the live PDBe API (not guessed):

- **API endpoints**: PDBe exposes two relevant endpoints:
  - `/entry/summary/{pdb_id}` — structure metadata (title, authors, release_date, experimental_method)
  - `/entry/publications/{pdb_id}` — publication details including DOI
- **PDB code casing**: always lowercase throughout (input converted, output lowercase,
  cache keys lowercase) — consistent with project convention (see CONVENTIONS.md §9).
- **Caching strategy**: disk-cached per endpoint per PDB code, default under
  `~/.cache/histo_publication_info_fetch/`, with `--refresh` flag to bypass.

### v0.2 mid-build expansion: Journal enrichment via PDBe publications endpoint

After v0.1 release, scope expanded to include full publication details. **Strategy**:
- Fetch all publication metadata from PDBe's `/entry/publications/{pdb_id}` endpoint, which
  already provides journal, volume, issue, pages, abstract, author list, DOI, and PubMed ID
- PDBe publications endpoint is the authoritative source for PDB structure publications
- Optional fallback to Europe PMC only if abstract is missing from PDBe (for older entries)
- **Why PDBe**: single endpoint, authoritative for PDB structures, complete metadata
- **Graceful degradation**: if no journal data in PDBe, output structure-only format with
  `type: "dataset"` and PDB-specific fields

**Output format**: BibJSON (standard bibliographic JSON format used by Zotero, Mendeley, etc.),
compatible with downstream citation tools.

## 3. Source fetching & parsing

### PDBe structure & publication metadata (`sources/pdbe.py`)

```python
# sources/pdbe.py
def parse_entry_summary(json_text: str, pdb_id: str) -> dict: ...  # structure fields from /entry/summary
def parse_publications(json_text: str, pdb_id: str) -> dict: ...  # publication metadata from /entry/publications
def fetch_pdbe_entry(pdb_id: str, cache_dir: Path, refresh: bool) -> dict: ...  # fetch both endpoints, merge results
```

- **`/entry/summary/{pdb_id}`**: structure metadata (title, entry_authors, release_date,
  experimental_method, deposition_date, etc.)
- **`/entry/publications/{pdb_id}`**: publication metadata (journal, volume, issue, pages,
  abstract, authors, DOI, PubMed ID, year)
- Parser normalizes release_date from YYYYMMDD → YYYY-MM-DD, joins experimental_method array
  into semicolon-separated string, extracts full publication metadata from publications endpoint
- `fetch_pdbe_entry()` calls both endpoints and merges results into a single dict

### Europe PMC fallback (`sources/europepmc.py`)

Optional module for abstract lookup if PDBe response is missing abstract:
- `fetch_article_by_doi()`: queries Europe PMC by DOI if PDBe abstract is missing
- Cached per PDB code to avoid duplicate requests
- Non-critical: if Europe PMC fetch fails, continues with PDBe-only data

## 4. Collation & normalization

1. For each input PDB code:
   - Lowercase it (input validation).
   - Fetch from PDBe `/entry/summary` and `/entry/publications`, extract structure + publication metadata.
   - If abstract is missing and DOI present, optionally fetch from Europe PMC (non-critical).
   - Convert to `PublicationRecord` (BibJSON format).
2. Assemble result: list of `PublicationRecord` dicts (one per input PDB, in order).

Normalization:
- All dates: ISO YYYY-MM-DD format (both release_date and deposition_date).
- Authors: from PDBe author_list (extracted from publications endpoint).
- experimental_method: array from PDBe → semicolon-separated string.
- journal fields: from PDBe publications endpoint (set to `null` if not available).
- BibJSON fields: `type` is `"article"` if journal data present, `"dataset"` if structure-only.

## 5. JSON Schema (BibJSON v0.2+)

Bundled at `src/histo_publication_info_fetch/schema/publication.schema.json`,
describing the output shape. Implements **BibJSON** (standard bibliographic JSON format):

```jsonc
{
  "schema_version": "0.2.0",
  "generated_at": "2026-08-17T00:00:00+00:00",
  "pdb_ids": ["1ao7", "1hla"],
  "publications": [
    {
      "type": "article",
      "title": "COMPLEX BETWEEN HUMAN T-CELL RECEPTOR, VIRAL PEPTIDE (TAX), AND HLA-A 0201",
      "authors": [
        { "name": "Garboczi, D.N." },
        { "name": "Ghosh, P." },
        ...
      ],
      "year": 1997,
      "journal": "The EMBO Journal",
      "volume": "16",
      "issue": "21",
      "pages": "6514-6525",
      "doi": "10.1093/emboj/16.21.6514",
      "abstract": "The crystal structure of...",
      "pdb_id": "1ao7",
      "release_date": "1997-09-17",
      "deposition_date": "1997-07-21",
      "experimental_method": "X-ray diffraction"
    }
  ]
}
```

**BibJSON compliance:**
- Standard fields: `type`, `title`, `authors` (array of objects with `name`), `year`, `journal`, `volume`, `issue`, `pages`, `doi`, `abstract`
- PDB-specific extensions: `pdb_id`, `release_date`, `deposition_date`, `experimental_method`
- Empty/null fields set to `null`, not omitted — consistent schema shape
- `type` is `"article"` if journal enrichment succeeded, `"dataset"` if structure-only

## 6. Library API

```python
from histo_publication_info_fetch import PublicationFetcher, PublicationRecord

fetcher = PublicationFetcher(cache_dir=None, refresh=False)

# Single PDB (fetches structure + journal enrichment)
record = fetcher.fetch_one("1ao7")  # -> PublicationRecord (dataclass, BibJSON-compliant)

# Multiple PDBs, ordered
records = fetcher.fetch_many(["1ao7", "1hla", "4ozh"])  # -> list[PublicationRecord]

# Write to BibJSON
fetcher.write_json(records, "pubs.json")  # -> BibJSON document

# Write to CSV
fetcher.write_csv(records, "pubs.csv")  # -> CSV (one record per row)
```

- `PublicationRecord` is a dataclass with BibJSON fields plus PDB-specific extensions.
- `fetch_one` performs two-phase fetch (PDBe structure + Europe PMC journal enrichment).
- `fetch_many` returns all records in input order.
- Graceful fallback: if Europe PMC lookup fails, returns PDB structure data only (type="dataset")

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
