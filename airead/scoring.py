"""Run all analyzers against a list of functions and produce FunctionScores."""

from __future__ import annotations

from typing import Iterable, List

from airead.analyzers import ANALYZERS
from airead.models import FunctionInfo, FunctionScore


def score_functions(functions: Iterable[FunctionInfo]) -> List[FunctionScore]:
    out: List[FunctionScore] = []
    for fn in functions:
        dims = [analyzer.analyze(fn) for analyzer in ANALYZERS]
        out.append(FunctionScore(function=fn, dimensions=dims))
    return out
