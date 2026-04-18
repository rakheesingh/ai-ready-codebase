"""Single Responsibility: function should be short, low complexity, do one thing."""

from __future__ import annotations

import ast

from radon.complexity import cc_visit

from airead.models import DimensionScore, Finding, FunctionInfo

DIMENSION = "srp"

MAX_LINES = 40
MAX_COMPLEXITY = 10
MAX_RETURNS = 4

IO_CALL_HINTS = {
    "open", "print", "input",
    "read", "write", "save", "load", "dump", "dumps",
    "get", "post", "put", "delete", "request", "fetch",
    "execute", "commit", "rollback", "query",
    "send", "publish", "emit",
}

FORMAT_CALL_HINTS = {"format", "join", "dumps", "render"}


def _complexity(fn: FunctionInfo) -> int:
    try:
        results = cc_visit(fn.source)
    except Exception:
        return 1
    return max((r.complexity for r in results), default=1)


def _count_returns(node: ast.AST) -> int:
    return sum(1 for n in ast.walk(node) if isinstance(n, ast.Return))


def _detect_concerns(node: ast.AST) -> set[str]:
    """Heuristically classify what the function body does."""

    concerns: set[str] = set()
    has_loop_or_compare = False
    has_arithmetic = False

    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            fname = ""
            if isinstance(n.func, ast.Attribute):
                fname = n.func.attr.lower()
            elif isinstance(n.func, ast.Name):
                fname = n.func.id.lower()
            if any(hint in fname for hint in IO_CALL_HINTS):
                concerns.add("io")
            if any(hint in fname for hint in FORMAT_CALL_HINTS):
                concerns.add("format")
        elif isinstance(n, ast.JoinedStr):
            concerns.add("format")
        elif isinstance(n, (ast.For, ast.While, ast.Compare, ast.IfExp)):
            has_loop_or_compare = True
        elif isinstance(n, ast.BinOp):
            has_arithmetic = True

    if has_loop_or_compare or has_arithmetic:
        concerns.add("logic")
    return concerns


def _parse_body(fn: FunctionInfo) -> ast.AST | None:
    try:
        module = ast.parse(fn.source)
    except SyntaxError:
        return None
    if module.body and isinstance(
        module.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)
    ):
        return module.body[0]
    return module


def analyze(fn: FunctionInfo) -> DimensionScore:
    findings: list[Finding] = []
    body_node = _parse_body(fn)

    line_count = max(1, fn.end_lineno - fn.lineno + 1)
    if line_count > MAX_LINES:
        findings.append(
            Finding(
                dimension=DIMENSION,
                message=f"Function is {line_count} lines (>{MAX_LINES}). Consider splitting.",
                severity=2 if line_count > MAX_LINES * 2 else 1,
            )
        )

    cx = _complexity(fn)
    if cx > MAX_COMPLEXITY:
        findings.append(
            Finding(
                dimension=DIMENSION,
                message=f"Cyclomatic complexity is {cx} (>{MAX_COMPLEXITY}). Too many branches.",
                severity=2 if cx > MAX_COMPLEXITY * 2 else 1,
            )
        )

    if body_node is not None:
        returns = _count_returns(body_node)
        if returns > MAX_RETURNS:
            findings.append(
                Finding(
                    dimension=DIMENSION,
                    message=f"{returns} return statements (>{MAX_RETURNS}). Multiple exit paths obscure intent.",
                    severity=1,
                )
            )

        concerns = _detect_concerns(body_node)
        if len(concerns) >= 3:
            findings.append(
                Finding(
                    dimension=DIMENSION,
                    message=f"Function mixes {len(concerns)} concerns: {', '.join(sorted(concerns))}. Split by responsibility.",
                    severity=2,
                )
            )

    if not findings:
        score = 2
    elif any(f.severity >= 2 for f in findings):
        score = 0
    else:
        score = 1

    return DimensionScore(dimension=DIMENSION, score=score, findings=findings)
