# histo-publication-info-fetch

Fetch structure publication metadata for PDB codes from the PDBe API (Protein Data Bank in Europe).
Ships as a Python library, CLI tool, and Claude skill. See `README.md` for usage and `docs/PLAN.md`
for design rationale.

## Environment

Python 3.14+, `uv`-managed.

```bash
uv sync              # set up dev environment
uv run pytest        # run tests
uv run histo-publication-info-fetch --help
```

When working from a source checkout: `uv run histo-publication-info-fetch <pdb_code> ...`
(or after `uv tool install .`, just `histo-publication-info-fetch ...`).

## Layout

```
src/histo_publication_info_fetch/
  __init__.py                      # public exports (PublicationFetcher, PublicationRecord)
  core.py                          # PublicationFetcher, PublicationRecord, write_json/write_csv
  cli.py                           # Click CLI entry point (main)
  http.py                          # cached_get() — disk cache, refresh, User-Agent
  py.typed                         # PEP 561 marker
  sources/
    __init__.py
    pdbe.py                        # parse_entry_summary(), fetch_pdbe_entry()
  schema/
    publication.schema.json        # JSON Schema for output (v0.3.0)

tests/
  test_pdbe.py                     # parsing tests (fixtures: pdbe/1ao7.json, 1hla.json, 4ozh.json)
  test_core.py                     # PublicationFetcher, write_json/csv tests
  test_cli.py                      # CLI integration tests
  fixtures/pdbe/                   # real PDBe API responses (committed)

skills/histo-publication-info-fetch/SKILL.md
tmp/                               # scratch dir for outputs (.gitkeep tracked, * ignored)
```

## Key invariants

- **PDB codes are always lowercase** everywhere (input, output, cache keys, JSON fields).
  This is project-wide convention (see `CONVENTIONS.md` §9).
- **Structure metadata only, no enrichment**: the tool fetches from PDBe's `/entry/summary`
  endpoint, which provides title, authors, release date, deposition date, experimental method.
  Full publication details (journal, DOI, pages, abstract) are NOT available from this endpoint
  and are not added via secondary lookups (PubMed, CrossRef). This is deliberate — v0.1 is
  single-endpoint and fast. See `docs/PLAN.md` §2b for the mid-build steering correction that
  arrived at this scope.
- **Caching is per-PDB-code, not per-batch**: each PDB's response is cached individually
  (cache key = SHA256(url)), allowing cache reuse across different runs and batch sizes.
- **Tests use real PDBe API responses**: not mocks or synthetic fixtures. Committed `fixtures/pdbe/`
  files are actual JSON from `https://www.ebi.ac.uk/pdbe/api/pdb/entry/summary/{pdb_id}`.

## Testing

```bash
uv run pytest tests/
```

All tests use real committed fixtures (no network, no mocks). `test_pdbe.py` exercises
parsing; `test_core.py` exercises the fetcher and JSON/CSV writers with monkeypatched
fetching; `test_cli.py` exercises the Click CLI with `CliRunner` and mocked fetches.

To regenerate fixtures after an API change:
```bash
curl -s https://www.ebi.ac.uk/pdbe/api/pdb/entry/summary/1ao7 > tests/fixtures/pdbe/1ao7.json
# ... repeat for other PDB codes
```

## Scope

The CLI surface is deliberately minimal — only the options actually needed:

- `PDB` (positional, 1+): PDB codes to fetch.
- `--output FILE`: write JSON or CSV (default: stdout).
- `--format {json,csv}`: output format (default: json).
- `--cache-dir DIR`: override cache location.
- `--refresh`: bypass cache, re-fetch.

**Don't add more options without checking with the user first** — this constraint is deliberate.
Minor UX niceties (progress bars, sorting, filtering) or speculative formats (YAML, Parquet)
can be added later if a use case asks for them.

## Related tools

This is an external-data-fetch tool (like `histo_tcr_info_fetch`). See `CONVENTIONS.md` §10
and the shared family docs (`../CLAUDE.md`, `../WAYS_OF_WORKING.md`) for cross-tool patterns
and decision-making conventions.
