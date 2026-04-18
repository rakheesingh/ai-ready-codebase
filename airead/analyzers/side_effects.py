"""Side-effect honesty: the verb in the function name should match what it does."""

from __future__ import annotations

import ast

from airead.models import DimensionScore, Finding, FunctionInfo

DIMENSION = "side_effects"

GETTER_PREFIXES = ("get_", "fetch_", "read_", "find_", "load_", "list_", "lookup_")
PURE_PREFIXES = ("is_", "has_", "should_", "can_", "calculate_", "compute_", "format_", "to_")
MUTATING_PREFIXES = ("set_", "save_", "write_", "update_", "delete_", "create_", "insert_", "remove_", "add_")

MUTATING_CALL_KEYWORDS = {
    "save", "write", "delete", "insert", "update", "commit",
    "remove", "pop", "clear", "append", "extend",
    "send", "post", "put", "publish", "emit", "execute",
}

IO_CALL_KEYWORDS = {"open", "print", "input", "request"}


def _parse_body(fn: FunctionInfo) -> ast.AST | None:
    try:
        module = ast.parse(fn.source)
    except SyntaxError:
        return None
    if module.body and isinstance(
        module.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)
    ):
        return module.body[0]
    return None


def _has_mutating_call(node: ast.AST) -> str | None:
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            fname = ""
            if isinstance(n.func, ast.Attribute):
                fname = n.func.attr.lower()
            elif isinstance(n.func, ast.Name):
                fname = n.func.id.lower()
            if fname in MUTATING_CALL_KEYWORDS or fname in IO_CALL_KEYWORDS:
                return fname
    return None


def _mutates_object(node: ast.AST, watch_names: set[str]) -> bool:
    """Detect mutation of self/cls or any name in ``watch_names`` (params)."""

    def _hits(target: ast.AST) -> bool:
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
            return target.value.id in watch_names
        if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
            return target.value.id in watch_names
        return False

    for n in ast.walk(node):
        if isinstance(n, ast.Assign):
            for tgt in n.targets:
                if _hits(tgt):
                    return True
        elif isinstance(n, ast.AugAssign):
            if _hits(n.target):
                return True
    return False


def _has_return_value(node: ast.AST) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Return) and n.value is not None:
            return True
    return False


def analyze(fn: FunctionInfo) -> DimensionScore:
    findings: list[Finding] = []
    body_node = _parse_body(fn)
    if body_node is None:
        return DimensionScore(dimension=DIMENSION, score=2, findings=[])

    name = fn.name.lower().lstrip("_")
    watch = {"self", "cls"} | set(fn.param_names)
    mutating_call = _has_mutating_call(body_node)
    writes_self = _mutates_object(body_node, watch)
    returns_value = _has_return_value(body_node)

    is_getter = name.startswith(GETTER_PREFIXES)
    is_pure = name.startswith(PURE_PREFIXES)
    is_mutator = name.startswith(MUTATING_PREFIXES)

    if is_getter and (mutating_call or writes_self):
        cause = f"call `{mutating_call}`" if mutating_call else "argument/self mutation"
        findings.append(
            Finding(
                dimension=DIMENSION,
                message=(
                    f"Name `{fn.name}` implies a read, but the body mutates "
                    f"({cause}). Rename or extract the side effect."
                ),
                severity=2,
            )
        )

    if is_pure and (mutating_call or writes_self):
        cause = f"call `{mutating_call}`" if mutating_call else "argument/self mutation"
        findings.append(
            Finding(
                dimension=DIMENSION,
                message=(
                    f"Predicate/computation `{fn.name}` should be pure but performs "
                    f"side effects ({cause})."
                ),
                severity=2,
            )
        )

    if is_mutator and not (mutating_call or writes_self) and returns_value:
        findings.append(
            Finding(
                dimension=DIMENSION,
                message=(
                    f"Name `{fn.name}` implies a write, but no mutation is visible — "
                    f"the function only computes a value. Consider renaming."
                ),
                severity=1,
            )
        )

    if not findings:
        score = 2
    elif any(f.severity >= 2 for f in findings):
        score = 0
    else:
        score = 1

    return DimensionScore(dimension=DIMENSION, score=score, findings=findings)
