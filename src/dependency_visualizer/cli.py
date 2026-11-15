"""Command-line entry point for the dependency visualizer (stages 1-5)."""

import argparse
import sys

from dependency_visualizer.config import load_config
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
from dependency_visualizer.visualization import generate_dot, render_svg, format_ascii_tree


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dependency-visualizer",
        description="Анализ и визуализация графа зависимостей NuGet-пакета (этапы 1–5).",
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


def main() -> int:
    args = create_parser().parse_args()
    try:
        config = load_config(args.config)
        if config.test_mode:
            result = build_test_graph(config.repository, config.package_name)
        else:
            # Cache resolved metadata to avoid repeating downloads for shared nodes.
            dependency_cache: dict[tuple[str, str], list[tuple[Dependency, str]]] = {}

            def get_dependencies(package: str, version: str):
                key = (package.casefold(), version.casefold())
                if key in dependency_cache:
                    return dependency_cache[key]
                direct = fetch_dependencies(package, version, config.repository)
                resolved = []
                for dependency in direct:
                    concrete = resolve_dependency_version(
                        dependency.package_id,
                        dependency.version_range,
                        config.repository,
                    )
                    resolved.append((dependency, concrete))
                dependency_cache[key] = resolved
                return resolved

            result = build_graph_dfs(
                config.package_name, config.package_version, get_dependencies
            )
    except (OSError, ValueError, NuGetError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2

    print("Анализ зависимостей NuGet-пакета")
    print(f"Корневой пакет: {config.package_name}")
    print(f"Версия: {config.package_version}")
    print(f"Режим тестового репозитория: {config.test_mode}")
    print("\nСписок смежности:")
    for package, dependencies in result.edges.items():
        print(f"{package} -> {', '.join(dependencies) if dependencies else '(нет зависимостей)'}")
    print("\nВерсии пакетов:")
    for package, version in result.resolved_versions.items():
        print(f"{package}: {version}")
    if result.cycles:
        print("\nЦиклические рёбра:")
        for source, target in result.cycles:
            print(f"{source} -> {target}")
    else:
        print("\nЦиклические зависимости не обнаружены.")
    print("Этап 3 завершён: граф зависимостей построен алгоритмом DFS.")

    try:
        dot_source = generate_dot(result)
        print("\nОписание графа в формате Graphviz DOT:")
        print(dot_source, end="")
        output_path = render_svg(dot_source, config.output_file)
        print(f"\nSVG-изображение графа сохранено: {output_path.resolve()}")
    except RuntimeError as error:
        print(f"Ошибка визуализации: {error}", file=sys.stderr)
        return 2

    if config.ascii_tree:
        print("\nASCII-дерево зависимостей:")
        print(format_ascii_tree(result))
    print("\nЭтап 5 завершён: описание Graphviz создано, SVG сформирован.")

    if args.reverse_dependencies is not None:
        target = args.reverse_dependencies or config.package_name
        try:
            reverse = find_reverse_dependencies_dfs(result, target)
        except ValueError as error:
            print(f"Ошибка: {error}", file=sys.stderr)
            return 2
        print()
        print(format_reverse_dependencies(target, reverse))
        print("\nЭтап 4 завершён: обратные зависимости найдены обходом DFS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
