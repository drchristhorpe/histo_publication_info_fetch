# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.0] - 2026-08-17

### Added
- **Journal enrichment from PDBe**: fetch complete publication metadata (journal, volume, issue, pages, abstract, authors, DOI, year) directly from PDBe's `/entry/publications/{pdb_id}` endpoint.
- **BibJSON format**: output now complies with BibJSON (standard bibliographic JSON format used by Zotero, Mendeley, etc.).
- **New fields**: `type`, `year`, `journal`, `volume`, `issue`, `pages`, `abstract` (all from PDBe).
- **Publication type field**: `type` is `"article"` if journal data found, `"dataset"` if structure-only.
- `Author` dataclass exported in public API.
- Optional Europe PMC fallback module for abstract lookup if PDBe is missing it.
- 10 new tests for publication parsing and BibJSON formatting.

### Changed
- **Schema version bumped to 0.2.0** (breaking change for consumers parsing v0.1).
- Output format now BibJSON: `authors` are objects with `name` field (not strings).
- CLI output format unchanged (still JSON/CSV), but JSON structure is now BibJSON.
- Fetch strategy: PDBe `/entry/publications/{pdb_id}` endpoint provides complete publication metadata — no secondary API calls needed in most cases.
- `PublicationRecord` dataclass expanded with BibJSON fields: `type`, `year`, `journal`, `volume`, `issue`, `pages`, `doi`, `abstract`.
- CSV output now includes all BibJSON fields.

### Technical Details
- Single-endpoint design: PDBe publications endpoint contains all needed publication metadata (journal, pages, authors, DOI, abstract, year).
- Optional Europe PMC fallback: only used if abstract is missing from PDBe (rare for recent structures).
- Graceful degradation: missing journal data results in `type: "dataset"` output, not a fetch error.
- Cached per PDB code and endpoint.

## [0.1.0] - 2026-07-13

### Added
- Initial release: fetch PDB structure metadata from PDBe API.
- CLI tool: `histo-publication-info-fetch` accepts one or more PDB codes, outputs JSON or CSV.
- Library API: `PublicationFetcher` with `fetch_one()`, `fetch_many()`, `write_json()`, `write_csv()`.
- Disk-based response caching keyed by URL hash (default `~/.cache/histo_publication_info_fetch`), with `--refresh` flag.
- JSON Schema validation for output shape (`src/.../schema/publication.schema.json`).
- Full test suite against real PDBe API fixtures (no mocks).

### Changed
- **Post-freeze mid-build correction** (per WAYS_OF_WORKING.md): 
  - Initial PLAN.md assumed PDBe `/entry/summary` endpoint would include full publication metadata (journal, DOI, pages, abstract).
  - Live API inspection revealed this endpoint only provides structure metadata: title, authors, release date, deposition date, experimental method.
  - Scope pivoted to "structure publication info" rather than "full publication info" — matches what PDBe API actually exposes without requiring secondary lookups (PubMed, CrossRef).
  - Output schema updated to reflect actual available fields.
  - This is a deliberate design choice: the tool fetches structure-level metadata from a single fast endpoint, not a research-paper-level citation with enrichment.

### Notes
- Full publication details (journal name, volume, issue, pages, DOI, PubMed ID, abstract) are not available from PDBe's `/entry/summary` endpoint and would require secondary API calls to PubMed or CrossRef — out of v0.1 scope.
- If a future use case requires those fields, consider: (a) adding a separate enrichment step via PubMed/CrossRef, or (b) switching to a different primary source (e.g., PDB API's other endpoints if they exist).
