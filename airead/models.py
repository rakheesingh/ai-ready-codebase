"""Shared data classes used across analyzers, scoring, and UI layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class FunctionInfo:
    """A single function discovered in the codebase."""

    file_path: str
    qualname: str
    name: str
    lineno: int
    end_lineno: int
    source: str
    param_names: List[str]
    is_method: bool = False


@dataclass
class Finding:
    """One concrete issue detected by a single analyzer."""

    dimension: str
    message: str
    severity: int


@dataclass
class DimensionScore:
    """Score for one of the four AI-readiness dimensions (0..2)."""

    dimension: str
    score: int
    findings: List[Finding] = field(default_factory=list)


@dataclass
class FunctionScore:
    """Aggregate score for a function across all dimensions."""

    function: FunctionInfo
    dimensions: List[DimensionScore]

    @property
    def total(self) -> int:
        return sum(d.score for d in self.dimensions)

    @property
    def max_total(self) -> int:
        return 2 * len(self.dimensions)

    @property
    def all_findings(self) -> List[Finding]:
        out: List[Finding] = []
        for d in self.dimensions:
            out.extend(d.findings)
        return out
