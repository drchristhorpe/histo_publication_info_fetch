# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
