"""Command-line entry point for the dependency visualizer."""

import argparse
import sys

from dependency_visualizer.config import load_config
from dependency_visualizer.nuget import (
    NuGetError,
    fetch_dependencies,
    load_test_dependencies,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dependency-visualizer",
        description="Получение прямых зависимостей NuGet-пакета (этап 2).",
    )
    parser.add_argument(
        "-c", "--config",
        default="config.toml",
        help="путь к TOML-конфигурации (по умолчанию: config.toml)",
    )
    return parser


def main() -> int:
    args = create_parser().parse_args()
    try:
        config = load_config(args.config)
        if config.test_mode:
            dependencies = load_test_dependencies(
                config.repository, config.package_name, config.package_version
            )
        else:
            dependencies = fetch_dependencies(
                config.package_name, config.package_version, config.repository
            )
    except (OSError, ValueError, NuGetError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2

    print("Прямые зависимости NuGet-пакета")
    print(f"Пакет: {config.package_name}")
    print(f"Версия: {config.package_version}")
    print(f"Репозиторий: {config.repository}")
    print(f"Количество прямых зависимостей: {len(dependencies)}")
    if not dependencies:
        print("Прямые зависимости отсутствуют.")
    else:
        for index, dependency in enumerate(dependencies, start=1):
            print(
                f"{index}. {dependency.package_id} "
                f"(версия: {dependency.version_range}; "
                f"целевой framework: {dependency.target_framework})"
            )
    print("\nЭтап 2 завершён: прямые зависимости получены.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
