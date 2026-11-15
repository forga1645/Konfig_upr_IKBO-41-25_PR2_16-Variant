"""Graphviz DOT and optional ASCII-tree rendering for dependency graphs."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from dependency_visualizer.graph import GraphResult


def generate_dot(result: GraphResult) -> str:
    """Return a complete Graphviz DOT directed graph."""
    lines = [
        "digraph dependencies {",
        '  graph [label="Dependency graph", labelloc="t", rankdir="LR"];',
        '  node [shape="box", style="rounded,filled", fillcolor="lightgoldenrod1"];',
        '  edge [color="slategray"];',
    ]
    nodes = list(result.edges)
    for package in nodes:
        version = result.resolved_versions.get(package)
        label = f"{package}\\n{version}" if version else package
        attrs = [f"label={json.dumps(label, ensure_ascii=False)}"]
        if package.casefold() == result.root.casefold():
            attrs.extend(['shape="doubleoctagon"', 'fillcolor="palegreen"'])
        lines.append(f"  {json.dumps(package, ensure_ascii=False)} [{', '.join(attrs)}];")
    for source, dependencies in result.edges.items():
        for target in dependencies:
            attrs = ' [color="firebrick", penwidth="2"]' if (source, target) in result.cycles else ""
            lines.append(
                f"  {json.dumps(source, ensure_ascii=False)} -> "
                f"{json.dumps(target, ensure_ascii=False)}{attrs};"
            )
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_svg(dot_source: str, output_path: str | Path) -> Path:
    """Render DOT to SVG using the Graphviz `dot` executable."""
    executable = shutil.which("dot")
    if executable is None:
        raise RuntimeError(
            "Не найдена команда Graphviz 'dot'. Установите Graphviz и добавьте "
            "папку с dot.exe в PATH. DOT-описание можно сохранить отдельно."
        )
    path = Path(output_path)
    try:
        completed = subprocess.run(
            [executable, "-Tsvg", "-o", str(path)],
            input=dot_source,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
    except OSError as error:
        raise RuntimeError(f"Не удалось запустить Graphviz: {error}") from error
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "неизвестная ошибка Graphviz"
        raise RuntimeError(f"Graphviz не смог создать SVG: {detail}")
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("Graphviz завершился без ошибки, но SVG-файл не создан.")
    return path


def format_ascii_tree(result: GraphResult) -> str:
    """Render dependencies as an ASCII-only tree, marking shared nodes/cycles."""
    lines = [result.root]
    visited = {result.root.casefold()}

    def visit(package: str, prefix: str) -> None:
        children = result.edges.get(package, [])
        for index, child in enumerate(children):
            last = index == len(children) - 1
            branch = "`-- " if last else "|-- "
            key = child.casefold()
            if key in visited:
                marker = " [cycle]" if any(
                    a.casefold() == package.casefold() and b.casefold() == key
                    for a, b in result.cycles
                ) else " [already shown]"
                lines.append(prefix + branch + child + marker)
                continue
            lines.append(prefix + branch + child)
            visited.add(key)
            visit(child, prefix + ("    " if last else "|   "))

    visit(result.root, "")
    return "\n".join(lines)
