"""Command-line entry point for the dependency visualizer (stages 1-5)."""

import argparse
import sys

from dependency_visualizer.config import AppConfig, load_config
from dependency_visualizer.graph import (
    build_graph_dfs,
    find_reverse_dependencies_dfs,
    format_reverse_dependencies,
)
from dependency_visualizer.nuget import (
    Dependency,
    NuGetError,
    fetch_dependencies,
    resolve_dependency_version,
)
from dependency_visualizer.test_repository import build_test_graph
from dependency_visualizer.visualization import (
    format_ascii_tree,
    generate_dot,
    render_svg,
)


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI parser and register command-line options."""
    parser = argparse.ArgumentParser(
        prog="dependency-visualizer",
        description=(
            "Анализ и визуализация графа зависимостей "
            "NuGet-пакета (этапы 1–5)."
        ),
    )
    parser.add_argument(
        "-c", "--config",
        default="config.toml",
        help="путь к TOML-конфигурации (по умолчанию: config.toml)",
    )
    parser.add_argument(
        "--reverse-dependencies",
        nargs="?",
        const="",
        metavar="PACKAGE",
        help=(
            "вывести пакеты, которые напрямую зависят от PACKAGE; "
            "если PACKAGE не указан, используется package_name из TOML"
        ),
    )
    return parser


def _create_dependency_loader(config: AppConfig):
    """Create a cached NuGet dependency callback for graph traversal."""
    cache: dict[tuple[str, str], list[tuple[Dependency, str]]] = {}

    def get_dependencies(package: str, version: str):
        """Fetch direct dependencies and resolve their concrete versions."""
        key = (package.casefold(), version.casefold())
        if key not in cache:
            direct = fetch_dependencies(package, version, config.repository)
            cache[key] = [
                (
                    dependency,
                    resolve_dependency_version(
                        dependency.package_id,
                        dependency.version_range,
                        config.repository,
                    ),
                )
                for dependency in direct
            ]
        return cache[key]

    return get_dependencies


def _build_result(config: AppConfig):
    """Build a graph from either a local fixture or the NuGet feed."""
    if config.test_mode:
        return build_test_graph(config.repository, config.package_name)
    loader = _create_dependency_loader(config)
    return build_graph_dfs(
        config.package_name, config.package_version, loader
    )


def _print_graph(config: AppConfig, result) -> None:
    """Print graph edges, versions, and cycle information."""
    print("Анализ зависимостей NuGet-пакета")
    print(f"Корневой пакет: {config.package_name}")
    print(f"Версия: {config.package_version}")
    print(f"Режим тестового репозитория: {config.test_mode}")
    print("\nСписок смежности:")
    for package, dependencies in result.edges.items():
        suffix = (
            ", ".join(dependencies)
            if dependencies
            else "(нет зависимостей)"
        )
        print(f"{package} -> {suffix}")
    print("\nВерсии пакетов:")
    for package, version in result.resolved_versions.items():
        print(f"{package}: {version}")
    if result.cycles:
        print("\nЦиклические рёбра:")
        for source, target in result.cycles:
            print(f"{source} -> {target}")
    else:
        print("\nЦиклические зависимости не обнаружены.")

def _visualize(config: AppConfig, result) -> int:
    """Generate DOT/SVG output and optionally print an ASCII tree."""
    try:
        dot_source = generate_dot(result)
        print("\nОписание графа в формате Graphviz DOT:")
        print(dot_source, end="")
        output_path = render_svg(dot_source, config.output_file)
    except RuntimeError as error:
        print(f"Ошибка визуализации: {error}", file=sys.stderr)
        return 2
    if config.ascii_tree:
        print("\nASCII-дерево зависимостей:")
        print(format_ascii_tree(result))
    return 0


def _print_reverse_dependencies(result, target: str) -> int:
    """Print direct reverse dependencies for a selected package."""
    try:
        reverse = find_reverse_dependencies_dfs(result, target)
    except ValueError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2
    print()
    print(format_reverse_dependencies(target, reverse))
    return 0


def main() -> int:
    """Run the configured analysis and return a process exit code."""
    args = create_parser().parse_args()
    try:
        config = load_config(args.config)
        result = _build_result(config)
    except (OSError, ValueError, NuGetError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2

    _print_graph(config, result)
    visual_status = _visualize(config, result)
    if visual_status:
        return visual_status
    if args.reverse_dependencies is None:
        return 0
    target = args.reverse_dependencies or config.package_name
    return _print_reverse_dependencies(result, target)


if __name__ == "__main__":
    raise SystemExit(main())
