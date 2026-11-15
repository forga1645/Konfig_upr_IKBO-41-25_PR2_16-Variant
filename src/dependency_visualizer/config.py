"""Loading and validation of the TOML configuration."""

from dataclasses import dataclass
from pathlib import Path
import re
import tomllib
from urllib.parse import urlparse


@dataclass(frozen=True)
class AppConfig:
    package_name: str
    repository: str
    test_mode: bool
    package_version: str
    output_file: str
    ascii_tree: bool


def _require_string(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Параметр '{key}' должен быть непустой строкой.")
    return value.strip()


def load_config(config_path: str | Path) -> AppConfig:
    """Read config.toml and validate every parameter."""
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Файл конфигурации не найден: {path}")

    try:
        with path.open("rb") as config_file:
            data = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"Ошибка синтаксиса TOML: {error}") from error

    required = {
        "package_name", "repository", "test_mode",
        "package_version", "output_file", "ascii_tree",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError("Отсутствуют параметры: " + ", ".join(missing))

    package_name = _require_string(data, "package_name")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", package_name):
        raise ValueError(
            "Параметр 'package_name' содержит недопустимые символы."
        )

    repository = _require_string(data, "repository")
    test_mode = data["test_mode"]
    if not isinstance(test_mode, bool):
        raise ValueError("Параметр 'test_mode' должен быть true или false.")

    if test_mode:
        repo_path = Path(repository).expanduser()
        if not repo_path.exists():
            raise ValueError(
                "В тестовом режиме 'repository' должен быть "
                "путём к существующему тестовому репозиторию."
            )
        if not repo_path.is_file():
            raise ValueError("Файл тестового репозитория должен быть файлом.")
    else:
        parsed_url = urlparse(repository)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError(
                "В обычном режиме 'repository' должен быть URL с http или https."
            )

    package_version = _require_string(data, "package_version")
    if not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z.+_-]*", package_version):
        raise ValueError("Параметр 'package_version' имеет неверный формат.")

    output_file = _require_string(data, "output_file")
    output_path = Path(output_file)
    if output_path.name != output_file or output_path.suffix.lower() != ".svg":
        raise ValueError(
            "Параметр 'output_file' должен быть именем файла с расширением .svg "
            "без пути к папке."
        )

    ascii_tree = data["ascii_tree"]
    if not isinstance(ascii_tree, bool):
        raise ValueError("Параметр 'ascii_tree' должен быть true или false.")

    return AppConfig(
        package_name=package_name,
        repository=repository,
        test_mode=test_mode,
        package_version=package_version,
        output_file=output_file,
        ascii_tree=ascii_tree,
    )
