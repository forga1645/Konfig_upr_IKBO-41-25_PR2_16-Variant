"""Loading and validation of the TOML configuration."""

from dataclasses import dataclass
from pathlib import Path
import re
import tomllib
from urllib.parse import urlparse


@dataclass(frozen=True)
class AppConfig:
    """Validated application settings."""

    package_name: str
    repository: str
    test_mode: bool
    package_version: str
    output_file: str
    ascii_tree: bool


def _require_string(data: dict, key: str) -> str:
    """Return a non-empty string configuration value."""
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Параметр '{key}' должен быть непустой строкой.")
    return value.strip()


def _read_toml(path: Path) -> dict:
    """Read TOML data and translate parser errors to ValueError."""
    try:
        with path.open("rb") as config_file:
            return tomllib.load(config_file)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"Ошибка синтаксиса TOML: {error}") from error


def _validate_required(data: dict) -> None:
    """Ensure that all required configuration keys are present."""
    required = {
        "package_name", "repository", "test_mode",
        "package_version", "output_file", "ascii_tree",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError("Отсутствуют параметры: " + ", ".join(missing))


def _validate_package_name(value: str) -> None:
    """Validate a NuGet package identifier."""
    pattern = r"[A-Za-z0-9][A-Za-z0-9._-]*"
    if not re.fullmatch(pattern, value):
        raise ValueError(
            "Параметр 'package_name' содержит недопустимые символы."
        )


def _validate_repository(repository: str, test_mode: bool) -> None:
    """Validate a local fixture path or a NuGet HTTP repository URL."""
    if test_mode:
        repo_path = Path(repository).expanduser()
        if not repo_path.exists():
            raise ValueError(
                "В тестовом режиме 'repository' должен быть "
                "путём к существующему тестовому репозиторию."
            )
        if not repo_path.is_file():
            raise ValueError("Файл тестового репозитория должен быть файлом.")
        return

    parsed_url = urlparse(repository)
    valid_scheme = parsed_url.scheme in {"http", "https"}
    if not valid_scheme or not parsed_url.netloc:
        raise ValueError(
            "В обычном режиме 'repository' должен быть URL "
            "с http или https."
        )


def _validate_version(value: str) -> None:
    """Validate the configured package version string."""
    pattern = r"[0-9A-Za-z][0-9A-Za-z.+_-]*"
    if not re.fullmatch(pattern, value):
        raise ValueError("Параметр 'package_version' имеет неверный формат.")


def _validate_output_file(value: str) -> None:
    """Require a simple SVG filename without directory components."""
    output_path = Path(value)
    valid_name = output_path.name == value
    if not valid_name or output_path.suffix.lower() != ".svg":
        raise ValueError(
            "Параметр 'output_file' должен быть именем файла "
            "с расширением .svg без пути к папке."
        )


def _require_boolean(data: dict, key: str) -> bool:
    """Return a boolean setting or raise a descriptive validation error."""
    value = data[key]
    if not isinstance(value, bool):
        raise ValueError(f"Параметр '{key}' должен быть true или false.")
    return value


def load_config(config_path: str | Path) -> AppConfig:
    """Read config.toml, validate all fields, and return AppConfig."""
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Файл конфигурации не найден: {path}")

    data = _read_toml(path)
    _validate_required(data)
    package_name = _require_string(data, "package_name")
    repository = _require_string(data, "repository")
    test_mode = _require_boolean(data, "test_mode")
    package_version = _require_string(data, "package_version")
    output_file = _require_string(data, "output_file")
    ascii_tree = _require_boolean(data, "ascii_tree")

    _validate_package_name(package_name)
    _validate_repository(repository, test_mode)
    _validate_version(package_version)
    _validate_output_file(output_file)
    return AppConfig(
        package_name=package_name,
        repository=repository,
        test_mode=test_mode,
        package_version=package_version,
        output_file=output_file,
        ascii_tree=ascii_tree,
    )
