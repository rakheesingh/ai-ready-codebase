"""airead CLI entry point."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from airead import __version__
from airead.parser.py_functions import enumerate_functions
from airead.ranker import rank
from airead.scoring import score_functions
from airead.ui.html_report import write_report
from airead.ui.terminal import render_summary


@click.group()
@click.version_option(__version__, prog_name="airead")
def cli() -> None:
    """airead — score the AI-readiness of your Python code, one function at a time."""


@cli.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path),
    default=".",
)
@click.option(
    "--limit",
    "-n",
    type=int,
    default=20,
    show_default=True,
    help="How many of the worst functions to display.",
)
def scan(path: Path, limit: int) -> None:
    """Scan PATH and print the worst functions to the terminal."""

    console = Console()
    root = str(path.resolve())

    with console.status("[dim]Enumerating functions...[/dim]"):
        functions = enumerate_functions(path)
    if not functions:
        console.print("[yellow]No Python functions found.[/yellow]")
        return

    with console.status(f"[dim]Scoring {len(functions)} functions...[/dim]"):
        scores = score_functions(functions)
        ranked = rank(scores, path)

    render_summary(console, ranked, root=root, limit=limit)


@cli.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path),
    default=".",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("airead-report.html"),
    show_default=True,
    help="Where to write the HTML report.",
)
def report(path: Path, output: Path) -> None:
    """Scan PATH and write a static HTML report to OUTPUT."""

    console = Console()
    root = str(path.resolve())

    with console.status("[dim]Enumerating functions...[/dim]"):
        functions = enumerate_functions(path)
    if not functions:
        console.print("[yellow]No Python functions found.[/yellow]")
        return

    with console.status(f"[dim]Scoring {len(functions)} functions...[/dim]"):
        scores = score_functions(functions)
        ranked = rank(scores, path)

    project_name = path.resolve().name or "project"
    out = write_report(ranked, root=root, project_name=project_name, output_path=output)
    console.print(f"[green]Report written:[/green] {out.resolve()}")
    console.print(f"[dim]Open it in your browser:[/dim] file://{out.resolve()}")


if __name__ == "__main__":
    cli()
