"""Render scan results to a self-contained static HTML file."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from airead import __version__
from airead.models import FunctionScore
from airead.ui.terminal import DIMENSION_LABELS

TEMPLATE_DIR = Path(__file__).parent / "templates"


def _color(score: int, max_score: int) -> str:
    ratio = score / max_score if max_score else 1.0
    if ratio >= 0.85:
        return "green"
    if ratio >= 0.5:
        return "yellow"
    return "red"


def _short_path(path: str, root: str) -> str:
    if root and path.startswith(root):
        return path[len(root):].lstrip("/")
    return path


def _build_rows(ranked: List[FunctionScore], root: str) -> list[dict]:
    rows: list[dict] = []
    for fs in ranked:
        dims = []
        for d in fs.dimensions:
            dims.append(
                {
                    "label": DIMENSION_LABELS[d.dimension],
                    "score": d.score,
                    "color": _color(d.score, 2),
                    "findings": [f.message for f in d.findings],
                }
            )
        sig = f"{fs.function.qualname}({', '.join(fs.function.param_names)})"
        loc = f"{_short_path(fs.function.file_path, root)}:{fs.function.lineno}"
        search_blob = " ".join(
            [sig, loc] + [msg for d in dims for msg in d["findings"]]
        )
        rows.append(
            {
                "signature": sig,
                "name": fs.function.name,
                "location": loc,
                "total": fs.total,
                "max_total": fs.max_total,
                "score_color": _color(fs.total, fs.max_total),
                "dims": dims,
                "source": fs.function.source,
                "search_blob": search_blob,
            }
        )
    return rows


def write_report(
    ranked: List[FunctionScore],
    root: str,
    project_name: str,
    output_path: Path,
) -> Path:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html")

    total = len(ranked)
    achieved = sum(fs.total for fs in ranked)
    possible = sum(fs.max_total for fs in ranked)
    overall_pct = round(100 * achieved / possible) if possible else 100
    critical = sum(1 for fs in ranked if fs.total <= 2)
    needs_work = sum(1 for fs in ranked if 3 <= fs.total <= 5)
    ok = total - critical - needs_work

    html = template.render(
        project_name=project_name,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        achieved=achieved,
        possible=possible,
        overall_pct=overall_pct,
        total=total,
        critical=critical,
        needs_work=needs_work,
        ok=ok,
        rows=_build_rows(ranked, root),
        version=__version__,
    )
    output_path.write_text(html, encoding="utf-8")
    return output_path
