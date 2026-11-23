"""Graphviz DOT and optional ASCII-tree rendering for dependency graphs."""
from __future__ import annotations

import json
from pathlib import Path

from wasi_graphviz import render, RenderError

from dependency_visualizer.graph import GraphResult


NODE_STYLE = (
    '  node [shape="box", style="rounded,filled", '
    'fillcolor="lightgoldenrod1"];'
)
CYCLE_STYLE = ' [color="firebrick", penwidth="2"]'


def _node_attributes(package: str, result: GraphResult) -> str:
    """Build DOT attributes for a package node."""
    version = result.resolved_versions.get(package)
    label = f"{package}\\n{version}" if version else package
    attrs = [f"label={json.dumps(label, ensure_ascii=False)}"]
    if package.casefold() == result.root.casefold():
        attrs.extend(['shape="doubleoctagon"', 'fillcolor="palegreen"'])
    return ", ".join(attrs)


def _format_nodes(result: GraphResult, lines: list[str]) -> None:
    """Append all graph nodes to a DOT document."""
    for package in result.edges:
        name = json.dumps(package, ensure_ascii=False)
        attributes = _node_attributes(package, result)
        lines.append(f"  {name} [{attributes}];")


def _format_edges(result: GraphResult, lines: list[str]) -> None:
    """Append dependency edges, highlighting edges that close cycles."""
    for source, dependencies in result.edges.items():
        for target in dependencies:
            attrs = CYCLE_STYLE if (source, target) in result.cycles else ""
            source_name = json.dumps(source, ensure_ascii=False)
            target_name = json.dumps(target, ensure_ascii=False)
            lines.append(f"  {source_name} -> {target_name}{attrs};")


def generate_dot(result: GraphResult) -> str:
    """Return a complete Graphviz DOT directed graph."""
    lines = [
        "digraph dependencies {",
        '  graph [label="Dependency graph", labelloc="t", rankdir="LR"];',
        NODE_STYLE,
        '  edge [color="slategray"];',
    ]
    _format_nodes(result, lines)
    _format_edges(result, lines)
    lines.append("}")
    return "\n".join(lines) + "\n"   # ← было "\\n", стало "\n"


def render_svg(dot_source: str, output_path: str | Path) -> Path:
    """Render DOT to SVG using wasi-graphviz (no system Graphviz needed)."""
    try:
        svg_bytes = render(dot_source)
    except RenderError as error:
        raise RuntimeError(f"Ошибка рендеринга SVG: {error}") from error
    path = Path(output_path)
    path.write_bytes(svg_bytes)
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("wasi-graphviz не создал файл SVG.")
    return path

def _cycle_marker(result: GraphResult, package: str, child: str) -> str:
    """Return a marker for a repeated node in the ASCII tree."""
    is_cycle = any(
        source.casefold() == package.casefold()
        and target.casefold() == child.casefold()
        for source, target in result.cycles
    )
    return " [cycle]" if is_cycle else " [already shown]"


def _append_tree_child(
    result: GraphResult,
    lines: list[str],
    child: str,
    package: str,
    prefix: str,
    branch: str,
) -> None:
    """Append a repeated child node with its cycle/shared marker."""
    marker = _cycle_marker(result, package, child)
    lines.append(prefix + branch + child + marker)


def _draw_ascii_children(
    result: GraphResult,
    package: str,
    prefix: str,
    visited: set[str],
    lines: list[str],
) -> None:
    """Recursively append a package's child nodes to the ASCII tree."""
    children = result.edges.get(package, [])
    for index, child in enumerate(children):
        last = index == len(children) - 1
        branch = "`-- " if last else "|-- "
        key = child.casefold()
        if key in visited:
            _append_tree_child(result, lines, child, package, prefix, branch)
            continue
        lines.append(prefix + branch + child)
        visited.add(key)
        next_prefix = prefix + ("    " if last else "|   ")
        _draw_ascii_children(result, child, next_prefix, visited, lines)


def format_ascii_tree(result: GraphResult) -> str:
    """Render an ASCII-only dependency tree.

    Shared nodes and cycle edges receive explanatory markers.
    """
    lines = [result.root]
    visited = {result.root.casefold()}
    _draw_ascii_children(result, result.root, "", visited, lines)
    return "\n".join(lines)   # ← было "\\n", стало "\n"
