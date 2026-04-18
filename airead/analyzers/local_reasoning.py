"""Local reasoning: function shouldn't depend on hidden state."""

from __future__ import annotations

import ast
import builtins

from airead.models import DimensionScore, Finding, FunctionInfo

DIMENSION = "local_reasoning"

BUILTIN_NAMES = set(dir(builtins))


def _parse_body(fn: FunctionInfo) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    try:
        module = ast.parse(fn.source)
    except SyntaxError:
        return None
    if module.body and isinstance(
        module.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)
    ):
        return module.body[0]
    return None


def _collect_local_bindings(func_node: ast.AST) -> set[str]:
    """Names introduced inside the function (params, assignments, imports, etc.)."""

    bindings: set[str] = set()

    if isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for arg in func_node.args.args:
            bindings.add(arg.arg)
        for arg in func_node.args.kwonlyargs:
            bindings.add(arg.arg)
        if func_node.args.vararg:
            bindings.add(func_node.args.vararg.arg)
        if func_node.args.kwarg:
            bindings.add(func_node.args.kwarg.arg)

    for n in ast.walk(func_node):
        if isinstance(n, ast.Assign):
            for tgt in n.targets:
                for nn in ast.walk(tgt):
                    if isinstance(nn, ast.Name):
                        bindings.add(nn.id)
        elif isinstance(n, (ast.AugAssign, ast.AnnAssign)):
            if isinstance(n.target, ast.Name):
                bindings.add(n.target.id)
        elif isinstance(n, ast.For) and isinstance(n.target, ast.Name):
            bindings.add(n.target.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for alias in n.names:
                bindings.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if n is not func_node:
                bindings.add(n.name)

    return bindings


def _find_in_body_imports(func_node: ast.AST) -> list[str]:
    out: list[str] = []
    for n in ast.walk(func_node):
        if isinstance(n, (ast.Import, ast.ImportFrom)) and n is not func_node:
            if isinstance(n, ast.Import):
                out.extend(a.name for a in n.names)
            else:
                mod = n.module or ""
                out.append(mod + ".*")
    return out


def _find_global_uses(
    func_node: ast.AST, local_bindings: set[str]
) -> list[str]:
    used_externals: set[str] = set()
    for n in ast.walk(func_node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            name = n.id
            if name in local_bindings:
                continue
            if name in BUILTIN_NAMES:
                continue
            if name in {"self", "cls"}:
                continue
            used_externals.add(name)
        elif isinstance(n, ast.Global):
            used_externals.update(n.names)
        elif isinstance(n, ast.Nonlocal):
            used_externals.update(n.names)
    return sorted(used_externals)


def analyze(fn: FunctionInfo) -> DimensionScore:
    findings: list[Finding] = []
    body_node = _parse_body(fn)
    if body_node is None:
        return DimensionScore(dimension=DIMENSION, score=2, findings=[])

    local_bindings = _collect_local_bindings(body_node)

    in_body_imports = _find_in_body_imports(body_node)
    if in_body_imports:
        sample = ", ".join(in_body_imports[:3])
        findings.append(
            Finding(
                dimension=DIMENSION,
                message=f"Imports inside the function body hide dependencies: {sample}.",
                severity=1,
            )
        )

    has_global = any(isinstance(n, ast.Global) for n in ast.walk(body_node))
    if has_global:
        findings.append(
            Finding(
                dimension=DIMENSION,
                message="Uses `global` — function depends on and mutates module-level state.",
                severity=2,
            )
        )

    externals = _find_global_uses(body_node, local_bindings)
    if len(externals) > 5:
        sample = ", ".join(externals[:5])
        findings.append(
            Finding(
                dimension=DIMENSION,
                message=f"References {len(externals)} external names (e.g. {sample}). Consider passing them in.",
                severity=1,
            )
        )

    if not findings:
        score = 2
    elif any(f.severity >= 2 for f in findings) or len(findings) >= 2:
        score = 0
    else:
        score = 1

    return DimensionScore(dimension=DIMENSION, score=score, findings=findings)
