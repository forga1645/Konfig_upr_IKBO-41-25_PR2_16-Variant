"""Точка входа в приложение."""

import argparse
import sys
from pathlib import Path

from .config import ConfigError, load_config, print_config


def main() -> int:
    """Запустить приложение."""
    parser = argparse.ArgumentParser(description="Визуализатор зависимостей")
    parser.add_argument(
        "--config", 
        type=Path, 
        required=True, 
        help="Путь к TOML файлу"
    )
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
        print_config(cfg)
        print(f"\n[OK] Пакет '{cfg.package_name}' готов к анализу.")
        return 0
    except ConfigError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
