"""Strictly offline uppercase-letter repository used for stage 3."""
from __future__ import annotations

import json
from pathlib import Path
import re

from dependency_visualizer.graph import build_graph_dfs
from dependency_visualizer.nuget import Dependency, NuGetError


class TestRepositoryError(NuGetError):
    """Invalid test repository data or missing test package."""


def _read_graph_data(path: Path) -> dict:
    """Read JSON graph data and report file/format errors."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        message = f"Не удалось прочитать тестовый граф: {error}"
        raise TestRepositoryError(message) from error
    except json.JSONDecodeError as error:
        message = f"Некорректный JSON тестового графа: {error}"
        raise TestRepositoryError(message) from error


def _validate_graph_root(data: object) -> None:
    """Check that the fixture contains a non-empty JSON object."""
    if not isinstance(data, dict) or not data:
        message = 'Тестовый граф должен быть JSON-объектом вида {"A": ["B"]}.'
        raise TestRepositoryError(message)


def _validate_package_name(package: object) -> None:
    """Require test package names to contain uppercase Latin letters."""
    if not isinstance(package, str) or not re.fullmatch(r"[A-Z]+", package):
        message = "Имена пакетов тестового графа должны состоять "
        raise TestRepositoryError(message + "из больших латинских букв.")


def _validate_children(package: str, children: object) -> None:
    """Validate one package's dependency list."""
    valid_list = isinstance(children, list)
    if valid_list:
        valid_list = all(
            isinstance(child, str) and re.fullmatch(r"[A-Z]+", child)
            for child in children
        )
    if not valid_list:
        message = f"Список зависимостей пакета {package} "
        raise TestRepositoryError(
            message + "должен содержать только имена A-Z."
        )


def _add_implied_nodes(graph: dict[str, list[str]]) -> None:
    """Add leaf nodes that are mentioned but not explicitly declared."""
    for children in list(graph.values()):
        for child in children:
            graph.setdefault(child, [])


def load_test_graph(repository_file: str | Path) -> dict[str, list[str]]:
    """Load and validate an uppercase-letter JSON dependency graph."""
    path = Path(repository_file).expanduser()
    data = _read_graph_data(path)
    _validate_graph_root(data)
    graph: dict[str, list[str]] = {}
    for package, children in data.items():
        _validate_package_name(package)
        _validate_children(package, children)
        graph[package] = children
    _add_implied_nodes(graph)
    return graph


def build_test_graph(repository_file: str | Path, root: str):
    """Build a recursive DFS graph from the offline fixture."""
    graph = load_test_graph(repository_file)
    if root not in graph:
        raise TestRepositoryError(
            f"Корневой пакет '{root}' отсутствует в тестовом графе."
        )

    def get_dependencies(package: str, _version: str):
        """Adapt fixture edges to the common dependency callback format."""
        return [
            (Dependency(child, "*", "test"), "test")
            for child in graph[package]
        ]

    return build_graph_dfs(root, "test", get_dependencies)
