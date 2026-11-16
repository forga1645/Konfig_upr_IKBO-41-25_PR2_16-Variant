"""Recursive DFS operations for dependency graphs."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from dependency_visualizer.nuget import Dependency


@dataclass(frozen=True)
class GraphResult:
    """Dependency graph and metadata collected during traversal."""

    root: str
    edges: dict[str, list[str]]
    cycles: list[tuple[str, str]]
    resolved_versions: dict[str, str]


@dataclass
class _GraphBuilder:
    """Mutable state used internally by the recursive DFS traversal."""

    get_dependencies: Callable[[str, str], list[tuple[Dependency, str]]]
    edges: dict[str, list[str]] = field(default_factory=dict)
    cycles: list[tuple[str, str]] = field(default_factory=list)
    resolved_versions: dict[str, str] = field(default_factory=dict)
    expanded: set[tuple[str, str]] = field(default_factory=set)
    active: list[str] = field(default_factory=list)

    def visit(self, package: str, version: str) -> None:
        """Visit a package and recursively expand its dependencies."""
        key = (package.casefold(), version.casefold())
        if key in self.expanded:
            return
        self.active.append(package)
        self.edges.setdefault(package, [])
        try:
            self._visit_children(package, version)
        finally:
            self.active.pop()
            self.expanded.add(key)

    def _visit_children(self, package: str, version: str) -> None:
        """Add outgoing edges and descend into non-cyclic children."""
        for dependency, concrete_version in self.get_dependencies(
            package, version
        ):
            child = dependency.package_id
            if child not in self.edges[package]:
                self.edges[package].append(child)
            self.resolved_versions.setdefault(child, concrete_version)
            if self._is_active(child):
                self._record_cycle(package, child)
                self.edges.setdefault(child, [])
                continue
            self.visit(child, concrete_version)

    def _is_active(self, package: str) -> bool:
        """Check whether a package is already on the current DFS path."""
        key = package.casefold()
        return any(item.casefold() == key for item in self.active)

    def _record_cycle(self, source: str, target: str) -> None:
        """Record a cycle edge once."""
        cycle = (source, target)
        if cycle not in self.cycles:
            self.cycles.append(cycle)


def build_graph_dfs(
    root_name: str,
    root_version: str,
    get_dependencies: Callable[[str, str], list[tuple[Dependency, str]]],
) -> GraphResult:
    """Build all reachable dependencies using recursive depth-first search.

    The callback returns dependency metadata paired with a concrete version.
    Edges to ancestors are retained, but recursion stops at those edges.
    """
    builder = _GraphBuilder(get_dependencies=get_dependencies)
    builder.resolved_versions[root_name] = root_version
    builder.visit(root_name, root_version)
    return GraphResult(
        root=root_name,
        edges=builder.edges,
        cycles=builder.cycles,
        resolved_versions=builder.resolved_versions,
    )


def _format_adjacency(result: GraphResult) -> list[str]:
    """Format graph edges as an adjacency list."""
    lines = ["Граф зависимостей (список смежности):"]
    for package, dependencies in result.edges.items():
        suffix = (
            ", ".join(dependencies)
            if dependencies
            else "(нет зависимостей)"
        )
        lines.append(f"{package} -> {suffix}")
    return lines


def _draw_tree(result: GraphResult, lines: list[str]) -> None:
    """Append a readable DFS tree to the output lines."""
    printed: set[str] = set()

    def draw(
        package: str, prefix: str, is_last: bool, root: bool = False
    ) -> None:
        if root:
            lines.append(package)
        else:
            branch = "└── " if is_last else "├── "
            lines.append(prefix + branch + package)
        if package in printed:
            return
        printed.add(package)
        children = result.edges.get(package, [])
        next_prefix = (
            "" if root else prefix + ("    " if is_last else "│   ")
        )
        for index, child in enumerate(children):
            last = index == len(children) - 1
            if child in printed:
                _append_seen_child(
                    result, lines, next_prefix, package, child, last
                )
            else:
                draw(child, next_prefix, last)

    draw(result.root, "", True, root=True)


def _append_seen_child(
    result: GraphResult,
    lines: list[str],
    prefix: str,
    package: str,
    child: str,
    is_last: bool,
) -> None:
    """Append a tree entry for a cycle or an already visited node."""
    branch = "└── " if is_last else "├── "
    marker = (
        " [цикл]"
        if (package, child) in result.cycles
        else " [уже посещён]"
    )
    lines.append(prefix + branch + child + marker)


def format_graph(result: GraphResult) -> str:
    """Render adjacency list, DFS tree, and detected cycles."""
    lines = _format_adjacency(result)
    lines.extend(["", "Обход DFS (дерево зависимостей):"])
    _draw_tree(result, lines)
    lines.extend(["", "Обнаружены циклические зависимости:"])
    if result.cycles:
        lines.extend(
            f"{source} -> {target}" for source, target in result.cycles
        )
    else:
        lines[-1] = "Циклические зависимости не обнаружены."
    return "\n".join(lines)


class GraphError(ValueError):
    """Raised when a requested graph operation cannot be completed."""


def _find_target(result: GraphResult, target: str) -> str:
    """Find the graph's canonical spelling for a target package."""
    target_key = target.casefold()
    for package in result.edges:
        if package.casefold() == target_key:
            return package
    raise GraphError(
        f"Пакет '{target}' отсутствует в построенном графе зависимостей."
    )


def _collect_reverse(result: GraphResult, target: str) -> list[str]:
    """Traverse the graph and collect direct dependants of target."""
    target_key = target.casefold()
    reverse: list[str] = []
    visited: set[str] = set()

    def visit(package: str) -> None:
        key = package.casefold()
        if key in visited:
            return
        visited.add(key)
        dependencies = result.edges.get(package, [])
        has_target = any(item.casefold() == target_key for item in dependencies)
        if has_target and key != target_key:
            reverse.append(package)
        for dependency in dependencies:
            visit(dependency)

    visit(result.root)
    return reverse


def find_reverse_dependencies_dfs(
    result: GraphResult, target: str
) -> list[str]:
    """Return reachable packages that directly depend on *target*."""
    actual_target = _find_target(result, target)
    return _collect_reverse(result, actual_target)


def format_reverse_dependencies(target: str, packages: list[str]) -> str:
    """Format direct reverse dependencies for terminal output."""
    lines = [f"Обратные зависимости пакета '{target}':"]
    if packages:
        lines.extend(f"- {package}" for package in packages)
    else:
        lines.append("(в построенном графе таких пакетов нет)")
    lines.append(f"Всего: {len(packages)}")
    return "\n".join(lines)
