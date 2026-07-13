import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from histo_publication_info_fetch.core import PublicationFetcher

console = Console()


@click.command()
@click.argument("pdb_codes", nargs=-1, required=True)
@click.option(
    "--output",
    type=click.Path(),
    help="Output file path (default: stdout as JSON lines).",
)
@click.option(
    "--format",
    type=click.Choice(["json", "csv"]),
    default="json",
    help="Output format.",
)
@click.option(
    "--cache-dir",
    type=click.Path(),
    help="Cache directory (default: ~/.cache/histo_publication_info_fetch).",
)
@click.option(
    "--refresh",
    is_flag=True,
    help="Bypass cache, re-fetch from PDBe API.",
)
def main(pdb_codes, output, format, cache_dir, refresh):
    """
    Fetch publication metadata for PDB structures from PDBe API.

    Accepts one or more PDB codes as arguments.
    """
    try:
        fetcher = PublicationFetcher(
            cache_dir=Path(cache_dir) if cache_dir else None,
            refresh=refresh,
        )

        # Normalize PDB codes
        codes = []
        for code in pdb_codes:
            # Handle comma-separated or space-separated input
            codes.extend([c.strip() for c in code.split(",")])

        if not codes:
            console.print("[red]Error: no PDB codes provided[/red]", err=True)
            sys.exit(1)

        # Fetch records
        with console.status(f"[bold green]Fetching {len(codes)} PDB code(s)..."):
            records = fetcher.fetch_many(codes)

        if not records:
            console.print("[yellow]No valid records fetched[/yellow]")
            return

        # Output
        if output:
            output_path = Path(output)
            if format == "json":
                fetcher.write_json(records, output_path)
                console.print(f"[green]✓[/green] Wrote {len(records)} record(s) to {output_path}")
            else:  # csv
                fetcher.write_csv(records, output_path)
                console.print(f"[green]✓[/green] Wrote {len(records)} record(s) to {output_path}")
        else:
            # Stdout: JSON lines
            for record in records:
                click.echo(record.to_dict())

        # Summary table
        table = Table(title=f"Structure Records ({len(records)} records)")
        table.add_column("PDB ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Release Date", style="green")
        table.add_column("Method", style="blue")

        for record in records:
            method = record.experimental_method or "—"
            title_short = record.title[:40] + "..." if record.title and len(record.title) > 40 else (record.title or "—")
            table.add_row(
                record.pdb_id.upper(),
                title_short,
                record.release_date or "—",
                method[:20] + "..." if len(method) > 20 else method,
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
