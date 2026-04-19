"""Walk a path and yield every function/method as a FunctionInfo."""

from __future__ import annotations

import ast
import os
import textwrap
from pathlib import Path
from typing import Iterable, Iterator, List

from airead.models import FunctionInfo


SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "build",
    "dist",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".airead",
    ".DS_Store",
    "requirements.txt",
    "README.md",
    "LICENSE",
}


def _iter_py_files(root: Path) -> Iterator[Path]:
    if root.is_file():
        if root.suffix == ".py":
            yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            if fname.endswith(".py"):
                yield Path(dirpath) / fname


def _function_source(source_lines: List[str], node: ast.AST) -> str:
    start = node.lineno - 1
    end = getattr(node, "end_lineno", node.lineno)
    raw = "".join(source_lines[start:end])
    return textwrap.dedent(raw)


def _qualname(stack: List[str], name: str) -> str:
    return ".".join(stack + [name]) if stack else name


def _walk_functions(
    file_path: str,
    source_lines: List[str],
    nodes: Iterable[ast.AST],
    class_stack: List[str],
) -> Iterator[FunctionInfo]:
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = [a.arg for a in node.args.args]
            yield FunctionInfo(
                file_path=file_path,
                qualname=_qualname(class_stack, node.name),
                name=node.name,
                lineno=node.lineno,
                end_lineno=getattr(node, "end_lineno", node.lineno),
                source=_function_source(source_lines, node),
                param_names=params,
                is_method=bool(class_stack),
            )
            yield from _walk_functions(file_path, source_lines, node.body, class_stack)
        elif isinstance(node, ast.ClassDef):
            yield from _walk_functions(
                file_path, source_lines, node.body, class_stack + [node.name]
            )


def enumerate_functions(root: Path) -> List[FunctionInfo]:
    """Return every function/method under ``root`` (recursive)."""

    out: List[FunctionInfo] = []
    for py_file in _iter_py_files(root):
        try:
            source = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            continue
        source_lines = source.splitlines(keepends=True)
        out.extend(
            _walk_functions(str(py_file), source_lines, tree.body, class_stack=[])
        )
    return out
