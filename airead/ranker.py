"""Rank functions by where a fix delivers the most AI-readability gain."""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List

from airead.models import FunctionScore
from airead.parser.py_functions import _iter_py_files


_CALLABLE_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")


def _name_call_counts(root: Path) -> Dict[str, int]:
    """Approximate per-name call counts across the codebase.

    Cheap regex scan — we only need a relative signal, not perfect accuracy.
    """

    counts: Counter[str] = Counter()
    for py_file in _iter_py_files(root):
        try:
            text = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in _CALLABLE_RE.finditer(text):
            counts[m.group(1)] += 1
    return dict(counts)


def rank(scores: Iterable[FunctionScore], root: Path) -> List[FunctionScore]:
    """Return the scores sorted: worst + most-called functions first."""

    call_counts = _name_call_counts(root)
    scored = list(scores)

    def key(fs: FunctionScore) -> tuple[float, int]:
        gap = fs.max_total - fs.total
        callers = call_counts.get(fs.function.name, 1)
        impact = gap * (1 + (callers ** 0.5))
        return (-impact, fs.function.lineno)

    return sorted(scored, key=key)
