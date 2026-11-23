"""Recursive DFS construction of a dependency graph with cycle detection."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from dependency_visualizer.nuget import Dependency


@dataclass(frozen=True)
class GraphResult:
    root: str
    edges: dict[str, list[str]]
    cycles: list[tuple[str, str]]
    resolved_versions: dict[str, str]


def build_graph_dfs(
    root_name: str,
    root_version: str,
    get_dependencies: Callable[[str, str], list[tuple[Dependency, str]]],
) -> GraphResult:
    """Build all reachable dependencies using recursive depth-first search.

    get_dependencies(package, version) returns (dependency metadata,
    concrete version to inspect) pairs. Edges to an ancestor are retained,
    but recursion stops there to avoid an infinite cycle.
    """
    edges: dict[str, list[str]] = {}
    cycles: list[tuple[str, str]] = []
    resolved_versions: dict[str, str] = {root_name: root_version}
    expanded: set[tuple[str, str]] = set()
    active: list[str] = []

    def visit(package: str, version: str) -> None:
        key = (package.casefold(), version.casefold())
        if key in expanded:
            return
        active.append(package)
        edges.setdefault(package, [])
        try:
            for dependency, concrete_version in get_dependencies(package, version):
                child = dependency.package_id
                if child not in edges[package]:
                    edges[package].append(child)
                resolved_versions.setdefault(child, concrete_version)
                if any(item.casefold() == child.casefold() for item in active):
                    cycle = (package, child)
                    if cycle not in cycles:
                        cycles.append(cycle)
                    edges.setdefault(child, [])
                    continue
                visit(child, concrete_version)
        finally:
            active.pop()
            expanded.add(key)

    visit(root_name, root_version)
    return GraphResult(root_name, edges, cycles, resolved_versions)


def format_graph(result: GraphResult) -> str:
    """Render adjacency list and a readable DFS tree."""
    lines = ["Граф зависимостей (список смежности):"]
    for package, dependencies in result.edges.items():
        suffix = ", ".join(dependencies) if dependencies else "(нет зависимостей)"
        lines.append(f"{package} -> {suffix}")

    lines.extend(["", "Обход DFS (дерево зависимостей):"])
    printed: set[str] = set()

    def draw(package: str, prefix: str, is_last: bool, root: bool = False) -> None:
        if root:
            lines.append(package)
        else:
            lines.append(prefix + ("└── " if is_last else "├── ") + package)
        if package in printed:
            return
        printed.add(package)
        children = result.edges.get(package, [])
        next_prefix = prefix + ("    " if is_last else "│   ") if not root else ""
        for index, child in enumerate(children):
            last = index == len(children) - 1
            if child in printed:
                marker = " [цикл]" if (package, child) in result.cycles else " [уже посещён]"
                lines.append(next_prefix + ("└── " if last else "├── ") + child + marker)
            else:
                draw(child, next_prefix, last)

    draw(result.root, "", True, root=True)
    if result.cycles:
        lines.extend(["", "Обнаружены циклические зависимости:"])
        lines.extend(f"{source} -> {target}" for source, target in result.cycles)
    else:
        lines.extend(["", "Циклические зависимости не обнаружены."])
    return "\n".join(lines)


class GraphError(ValueError):
    """Raised when a requested graph operation cannot be completed."""


def find_reverse_dependencies_dfs(result: GraphResult, target: str) -> list[str]:
    """Return reachable packages that directly depend on *target*.

    The graph is traversed with recursive DFS, matching the algorithm used to
    build the stage-3 graph. Each vertex is inspected once, so cycles are safe.
    The result preserves DFS discovery order.
    """
    target_key = target.casefold()
    actual_target = next(
        (package for package in result.edges if package.casefold() == target_key),
        None,
    )
    if actual_target is None:
        raise GraphError(
            f"Пакет '{target}' отсутствует в построенном графе зависимостей."
        )

    reverse: list[str] = []
    visited: set[str] = set()

    def visit(package: str) -> None:
        if package in visited:
            return
        visited.add(package)

        if any(
            dependency.casefold() == target_key
            for dependency in result.edges.get(package, [])
        ) and package.casefold() != target_key:
            if package not in reverse:
                reverse.append(package)

        for dependency in result.edges.get(package, []):
            visit(dependency)

    visit(result.root)
    return reverse


def format_reverse_dependencies(target: str, packages: list[str]) -> str:
    """Format direct reverse dependencies for terminal output."""
    lines = [f"Обратные зависимости пакета '{target}':"]
    if not packages:
        lines.append("(в построенном графе таких пакетов нет)")
    else:
        lines.extend(f"- {package}" for package in packages)
    lines.append(f"Всего: {len(packages)}")
    return "\n".join(lines)
