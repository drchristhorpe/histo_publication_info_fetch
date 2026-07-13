# histo-publication-info-fetch

Fetch publication metadata for PDB structures from the PDBe API.

Ships as a Python library, CLI tool, and Claude skill.

Requires Python 3.14+.

## Install

```bash
uv sync                 # dev environment, from a checkout
uv tool install .       # install the CLI globally
# or
pip install .
```

## CLI usage

```bash
histo-publication-info-fetch 1ao7 1hla 4ozh [--output FILE] [--format json|csv] [--cache-dir DIR] [--refresh]
```

- `PDB` (positional, one or more): PDB codes to fetch (space-separated, comma-separated, or piped).
- `--output` (optional): write to this file. Default: stdout (JSON lines).
- `--format` (default `json`): output format (`json` or `csv`).
- `--cache-dir` (optional): override `~/.cache/histo_publication_info_fetch`.
- `--refresh`: bypass cache, re-fetch from PDBe.

Example:

```bash
$ histo-publication-info-fetch 1ao7 --output pubs.json --format json
```

## Library usage

```python
from histo_publication_info_fetch import PublicationFetcher

fetcher = PublicationFetcher()
record = fetcher.fetch_one("1ao7")  # -> PublicationRecord

records = fetcher.fetch_many(["1ao7", "1hla"])  # -> list[PublicationRecord]
fetcher.write_json(records, "output.json")
fetcher.write_csv(records, "output.csv")
```

## Notes and limitations

- PDB codes are normalized to lowercase everywhere (input, output, cache keys).
- If a PDB is not yet published or has no publication data, the record will have
  `publication: null` fields.
- The cache is keyed by URL hash, one response file per PDB code. Clear
  `~/.cache/histo_publication_info_fetch/` to reset.

## Development

```bash
uv sync && uv run pytest
```

See `docs/PLAN.md` for design rationale and `CHANGELOG.md` for release history.
