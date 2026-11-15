"""Strictly offline uppercase-letter repository used for stage 3."""
from __future__ import annotations

import json
from pathlib import Path
import re

from dependency_visualizer.graph import build_graph_dfs
from dependency_visualizer.nuget import Dependency, NuGetError


class TestRepositoryError(NuGetError):
    pass


def load_test_graph(repository_file: str | Path) -> dict[str, list[str]]:
    path = Path(repository_file).expanduser()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise TestRepositoryError(f"Не удалось прочитать тестовый граф: {error}") from error
    except json.JSONDecodeError as error:
        raise TestRepositoryError(f"Некорректный JSON тестового графа: {error}") from error
    if not isinstance(data, dict) or not data:
        raise TestRepositoryError("Тестовый граф должен быть JSON-объектом вида {\"A\": [\"B\"]}.")
    graph: dict[str, list[str]] = {}
    for package, children in data.items():
        if not isinstance(package, str) or not re.fullmatch(r"[A-Z]+", package):
            raise TestRepositoryError("Имена пакетов тестового графа должны состоять из больших латинских букв.")
        if not isinstance(children, list) or any(
            not isinstance(child, str) or not re.fullmatch(r"[A-Z]+", child)
            for child in children
        ):
            raise TestRepositoryError(f"Список зависимостей пакета {package} должен содержать только имена A-Z.")
        graph[package] = children
    # Nodes without outgoing edges may be explicitly listed or implied.
    for children in list(graph.values()):
        for child in children:
            graph.setdefault(child, [])
    return graph


def build_test_graph(repository_file: str | Path, root: str):
    graph = load_test_graph(repository_file)
    if root not in graph:
        raise TestRepositoryError(f"Корневой пакет '{root}' отсутствует в тестовом графе.")

    def get_dependencies(package: str, _version: str):
        return [(Dependency(child, "*", "test"), "test") for child in graph[package]]

    return build_graph_dfs(root, "test", get_dependencies)
