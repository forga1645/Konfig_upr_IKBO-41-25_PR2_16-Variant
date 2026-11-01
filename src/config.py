"""Чтение конфигурации из TOML-файла."""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore


class ConfigError(Exception):
    """Ошибка чтения конфигурации."""


@dataclass
class Config:
    """Параметры запуска."""
    package_name: str
    repo_url: str
    work_mode: str
    package_version: str
    image_filename: str
    ascii_tree: bool
    max_depth: int


def load_config(config_path: Path) -> Config:
    """Загрузить и проверить конфигурацию."""
    if not config_path.exists():
        raise ConfigError(f"Файл конфигурации не найден: {config_path}")

    try:
        with config_path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Ошибка парсинга TOML: {exc}") from exc

    try:
        return Config(
            package_name=str(data["package_name"]),
            repo_url=str(data["repo_url"]),
            work_mode=str(data["work_mode"]),
            package_version=str(data["package_version"]),
            image_filename=str(data["image_filename"]),
            ascii_tree=bool(data["ascii_tree"]),
            max_depth=int(data["max_depth"]),
        )
    except KeyError as exc:
        raise ConfigError(f"Отсутствует обязательный параметр: {exc}") from exc
    except ValueError as exc:
        raise ConfigError(f"Неверный тип данных: {exc}") from exc


def print_config(cfg: Config) -> None:
    """Вывести конфигурацию в формате ключ-значение."""
    print("--- Конфигурация ---")
    print(f"package_name   = {cfg.package_name}")
    print(f"repo_url       = {cfg.repo_url}")
    print(f"work_mode      = {cfg.work_mode}")
    print(f"package_version= {cfg.package_version}")
    print(f"image_filename = {cfg.image_filename}")
    print(f"ascii_tree     = {cfg.ascii_tree}")
    print(f"max_depth      = {cfg.max_depth}")
    print("--------------------")
