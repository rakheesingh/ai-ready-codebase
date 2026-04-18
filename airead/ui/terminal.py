"""Render scan results to the terminal using rich."""

from __future__ import annotations

from typing import List

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from airead.models import FunctionScore

DIMENSION_LABELS = {
    "naming": "Naming",
    "srp": "SRP",
    "side_effects": "Side-effects",
    "local_reasoning": "Local reasoning",
}

DIMENSION_SHORT = {
    "naming": "Name",
    "srp": "SRP",
    "side_effects": "SideFx",
    "local_reasoning": "Local",
}


def _color_for_score(score: int, max_score: int) -> str:
    ratio = score / max_score if max_score else 1.0
    if ratio >= 0.85:
        return "green"
    if ratio >= 0.5:
        return "yellow"
    return "red"


def _short_path(path: str, root: str | None = None) -> str:
    if root and path.startswith(root):
        return path[len(root):].lstrip("/")
    return path


def render_summary(
    console: Console,
    ranked: List[FunctionScore],
    root: str,
    limit: int,
) -> None:
    if not ranked:
        console.print("[yellow]No functions found.[/yellow]")
        return

    total = len(ranked)
    achieved = sum(fs.total for fs in ranked)
    possible = sum(fs.max_total for fs in ranked)
    overall_ratio = achieved / possible if possible else 1.0

    critical = sum(1 for fs in ranked if fs.total <= 2)
    needs_work = sum(1 for fs in ranked if 3 <= fs.total <= 5)
    ok = total - critical - needs_work

    color = _color_for_score(achieved, possible)
    header = Text.assemble(
        ("AI-readiness ", "bold"),
        (f"{achieved}/{possible}", f"bold {color}"),
        ("  ", ""),
        (f"({overall_ratio:.0%})", "dim"),
    )
    summary = Text.assemble(
        (f"{total} functions  ", ""),
        (f"{critical} critical  ", "red"),
        (f"{needs_work} needs work  ", "yellow"),
        (f"{ok} ok", "green"),
    )
    console.print(Panel.fit(Text("\n").join([header, summary]), border_style=color))

    width = console.width or 80
    score_w, dim_w = 6, 6
    side_w = 7
    padding_total = 7 * 3
    fixed_cols_width = score_w + dim_w + dim_w + side_w + dim_w + padding_total
    remaining = max(20, width - fixed_cols_width)
    fn_width = max(18, int(remaining * 0.55))
    loc_width = max(15, remaining - fn_width)

    table = Table(
        box=box.SIMPLE_HEAVY,
        title=f"Worst {min(limit, total)} of {total} functions (fix these first)",
        title_style="bold",
        show_lines=False,
        expand=False,
        pad_edge=False,
    )
    table.add_column("Score", justify="right", no_wrap=True, width=score_w)
    for key in DIMENSION_LABELS:
        col_w = side_w if key == "side_effects" else dim_w
        table.add_column(DIMENSION_SHORT[key], justify="center", no_wrap=True, width=col_w)
    table.add_column("Function", overflow="ellipsis", no_wrap=True, width=fn_width)
    table.add_column(
        "Location", style="dim", overflow="ellipsis", no_wrap=True, width=loc_width
    )

    for fs in ranked[:limit]:
        score_color = _color_for_score(fs.total, fs.max_total)
        score_cell = Text(f"{fs.total}/{fs.max_total}", style=f"bold {score_color}")
        dim_cells = []
        for dim in fs.dimensions:
            c = _color_for_score(dim.score, 2)
            dim_cells.append(Text(str(dim.score), style=c))

        sig = f"{fs.function.qualname}({', '.join(fs.function.param_names)})"
        loc = f"{_short_path(fs.function.file_path, root)}:{fs.function.lineno}"
        table.add_row(score_cell, *dim_cells, sig, loc)

    console.print(table)

    console.print()
    console.print(
        "[dim]Run [bold]airead report[/bold] to generate an HTML view of every function.[/dim]"
    )


def render_function_detail(console: Console, fs: FunctionScore, root: str) -> None:
    sig = f"{fs.function.qualname}({', '.join(fs.function.param_names)})"
    loc = f"{_short_path(fs.function.file_path, root)}:{fs.function.lineno}"
    score_color = _color_for_score(fs.total, fs.max_total)

    lines: List[Text] = []
    lines.append(
        Text.assemble(
            ("Score ", "bold"),
            (f"{fs.total}/{fs.max_total}", f"bold {score_color}"),
            (f"   {loc}", "dim"),
        )
    )
    lines.append(Text(""))

    for dim in fs.dimensions:
        c = _color_for_score(dim.score, 2)
        marker = "✓" if dim.score == 2 else ("~" if dim.score == 1 else "✗")
        lines.append(
            Text.assemble(
                (f"  {marker} ", c),
                (f"{DIMENSION_LABELS[dim.dimension]} ", "bold"),
                (f"({dim.score}/2)", c),
            )
        )
        if not dim.findings:
            lines.append(Text("      no issues detected", style="dim"))
        for f in dim.findings:
            lines.append(Text(f"      • {f.message}"))
        lines.append(Text(""))

    console.print(Panel(Text("\n").join(lines), title=sig, border_style=score_color))
