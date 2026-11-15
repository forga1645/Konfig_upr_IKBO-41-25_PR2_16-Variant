"""Command-line entry point for the first project stage."""

import argparse
import sys

from dependency_visualizer.config import load_config


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        prog="dependency-visualizer",
        description="Прототип визуализатора зависимостей (этап 1).",
    )
    parser.add_argument(
        "-c", "--config",
        default="config.toml",
        help="путь к TOML-конфигурации (по умолчанию: config.toml)",
    )
    return parser


def main() -> int:
    """Load configuration, validate it and print parameters."""
    args = create_parser().parse_args()
    try:
        config = load_config(args.config)
    except (OSError, ValueError) as error:
        print(f"Ошибка конфигурации: {error}", file=sys.stderr)
        return 2

    print("Параметры приложения:")
    print(f"package_name = {config.package_name}")
    print(f"repository = {config.repository}")
    print(f"test_mode = {str(config.test_mode).lower()}")
    print(f"package_version = {config.package_version}")
    print(f"output_file = {config.output_file}")
    print(f"ascii_tree = {str(config.ascii_tree).lower()}")
    print("\nЭтап 1 завершён: конфигурация успешно загружена.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
