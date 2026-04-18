"""Naming clarity: function and parameter names should reveal intent."""

from __future__ import annotations

from airead.models import DimensionScore, Finding, FunctionInfo

DIMENSION = "naming"

VAGUE_NAMES = {
    "data", "info", "item", "items", "thing", "things", "stuff", "tmp", "temp",
    "obj", "object", "val", "value", "values", "result", "results", "res",
    "foo", "bar", "baz", "var", "param", "arg", "args", "kwargs",
    "do_stuff", "do_it", "do_thing", "doit",
    "handle", "handler", "process", "manage", "manager",
    "helper", "helpers", "util", "utils", "misc",
    "run", "exec", "execute", "perform",
    "stuff_handler", "thing_doer",
}

VAGUE_VERB_PREFIXES = {"do_", "handle_", "process_", "manage_", "perform_"}

ALLOWED_SHORT_NAMES = {"i", "j", "k", "n", "x", "y", "z", "id", "fn", "io", "df"}


def _is_vague_param(name: str) -> bool:
    if name in {"self", "cls"}:
        return False
    if name in VAGUE_NAMES:
        return True
    if len(name) <= 2 and name not in ALLOWED_SHORT_NAMES:
        return True
    return False


def _function_name_findings(fn: FunctionInfo) -> list[Finding]:
    findings: list[Finding] = []
    name = fn.name
    lower = name.lower().lstrip("_")

    if lower in VAGUE_NAMES:
        findings.append(
            Finding(
                dimension=DIMENSION,
                message=f"Function name `{name}` is vague — it gives an LLM no signal about intent.",
                severity=2,
            )
        )
    elif any(lower.startswith(p) for p in VAGUE_VERB_PREFIXES):
        rest = lower
        for p in VAGUE_VERB_PREFIXES:
            if rest.startswith(p):
                rest = rest[len(p):]
                break
        if not rest or rest in VAGUE_NAMES or len(rest) <= 2:
            findings.append(
                Finding(
                    dimension=DIMENSION,
                    message=f"Function name `{name}` uses a vague verb prefix without a specific noun.",
                    severity=1,
                )
            )

    if len(lower) <= 2 and lower not in ALLOWED_SHORT_NAMES:
        findings.append(
            Finding(
                dimension=DIMENSION,
                message=f"Function name `{name}` is too short to convey purpose.",
                severity=2,
            )
        )

    return findings


def _param_findings(fn: FunctionInfo) -> list[Finding]:
    bad = [p for p in fn.param_names if _is_vague_param(p)]
    if not bad:
        return []
    pretty = ", ".join(f"`{p}`" for p in bad)
    severity = 2 if len(bad) >= max(1, len(fn.param_names) // 2) else 1
    return [
        Finding(
            dimension=DIMENSION,
            message=f"Vague parameter name(s): {pretty}. Use intention-revealing names.",
            severity=severity,
        )
    ]


def analyze(fn: FunctionInfo) -> DimensionScore:
    findings = _function_name_findings(fn) + _param_findings(fn)

    if not findings:
        score = 2
    elif any(f.severity >= 2 for f in findings) or len(findings) >= 2:
        score = 0
    else:
        score = 1

    return DimensionScore(dimension=DIMENSION, score=score, findings=findings)
