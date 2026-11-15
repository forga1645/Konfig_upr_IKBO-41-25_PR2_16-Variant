"""Retrieve direct NuGet dependencies using the NuGet V3 HTTP protocol.

No package manager or third-party package is used: urllib performs HTTP,
ElementTree parses the .nuspec XML, and json handles the optional test fixture.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class Dependency:
    package_id: str
    version_range: str
    target_framework: str = "all"


class NuGetError(Exception):
    """A readable error while querying a NuGet repository."""


def _local_name(tag: str) -> str:
    """Return an XML tag without its optional namespace."""
    return tag.rsplit("}", 1)[-1]


def parse_nuspec(xml_content: str | bytes) -> list[Dependency]:
    """Extract direct dependencies from a NuGet .nuspec document.

    Dependencies in every target-framework group are returned. The framework
    is retained so that alternatives for different frameworks are not hidden.
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as error:
        raise NuGetError(f"Некорректный XML .nuspec: {error}") from error

    dependencies_node = next(
        (node for node in root.iter() if _local_name(node.tag) == "dependencies"),
        None,
    )
    if dependencies_node is None:
        return []

    result: list[Dependency] = []
    seen: set[tuple[str, str, str]] = set()

    def add_dependency(node: ET.Element, framework: str) -> None:
        package_id = node.attrib.get("id", "").strip()
        version_range = node.attrib.get("version", "").strip() or "(не указана)"
        if not package_id:
            return
        key = (package_id.casefold(), version_range, framework)
        if key not in seen:
            seen.add(key)
            result.append(Dependency(package_id, version_range, framework))

    children = list(dependencies_node)
    groups = [node for node in children if _local_name(node.tag) == "group"]
    if groups:
        for group in groups:
            framework = group.attrib.get("targetFramework", "all") or "all"
            for node in group:
                if _local_name(node.tag) == "dependency":
                    add_dependency(node, framework)
    else:
        for node in children:
            if _local_name(node.tag) == "dependency":
                add_dependency(node, "all")

    return result


def _http_get(url: str, timeout: int = 20) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "dependency-visualizer/0.2", "Accept": "application/json, application/xml, */*"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise NuGetError(f"Пакет или версия не найдены (HTTP 404): {url}") from error
        raise NuGetError(f"Ошибка HTTP {error.code} при обращении к NuGet: {url}") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise NuGetError(f"Не удалось обратиться к репозиторию NuGet: {error}") from error


def _find_package_base_address(service_index: dict, repository_url: str) -> str:
    resources = service_index.get("resources", [])
    for resource in resources:
        resource_type = resource.get("@type", "")
        types = resource_type if isinstance(resource_type, list) else [resource_type]
        if any(str(value).startswith("PackageBaseAddress/") for value in types):
            base = resource.get("@id")
            if isinstance(base, str) and base:
                return base.rstrip("/") + "/"
    # Some private feeds expose the flat-container endpoint directly.
    if "flatcontainer" in repository_url.lower():
        return repository_url.rstrip("/") + "/"
    raise NuGetError(
        "В service index репозитория не найден ресурс PackageBaseAddress. "
        "Укажите URL NuGet V3 service index."
    )


def fetch_dependencies(package_name: str, package_version: str, repository_url: str) -> list[Dependency]:
    """Fetch one exact package version from a NuGet V3 service index."""
    index_bytes = _http_get(repository_url)
    try:
        service_index = json.loads(index_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise NuGetError(f"Репозиторий вернул некорректный JSON service index: {error}") from error
    if not isinstance(service_index, dict):
        raise NuGetError("Некорректный формат NuGet service index: ожидался JSON-объект.")

    base_address = _find_package_base_address(service_index, repository_url)
    package_id = urllib.parse.quote(package_name.lower(), safe="")
    version = urllib.parse.quote(package_version.lower(), safe="")
    nuspec_url = urllib.parse.urljoin(
        base_address,
        f"{package_id}/{version}/{package_id}.nuspec",
    )
    nuspec_bytes = _http_get(nuspec_url)
    return parse_nuspec(nuspec_bytes)


def load_test_dependencies(repository_file: str | Path, package_name: str, package_version: str) -> list[Dependency]:
    """Load dependencies from a small JSON fixture (offline test mode).

    Fixture schema: {"packages": {"Package.Id": {"1.0.0":
    {"dependencies": [{"id": "Other.Id", "version": "[2.0.0]",
    "target_framework": "net8.0"}]}}}}
    """
    path = Path(repository_file).expanduser()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise NuGetError(f"Не удалось прочитать тестовый репозиторий: {error}") from error
    except json.JSONDecodeError as error:
        raise NuGetError(f"Некорректный JSON тестового репозитория: {error}") from error

    try:
        package_versions = next(
            value for key, value in data["packages"].items()
            if key.casefold() == package_name.casefold()
        )
        package_data = package_versions[package_version]
        raw_dependencies = package_data.get("dependencies", [])
    except (KeyError, StopIteration, TypeError, AttributeError) as error:
        raise NuGetError(
            f"В тестовом репозитории не найден пакет '{package_name}' версии '{package_version}'."
        ) from error

    dependencies: list[Dependency] = []
    for item in raw_dependencies:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise NuGetError("Каждая тестовая зависимость должна содержать строковое поле 'id'.")
        dependencies.append(Dependency(
            package_id=item["id"],
            version_range=str(item.get("version", "(не указана)")),
            target_framework=str(item.get("target_framework", "all")),
        ))
    return dependencies


def _version_key(version: str):
    """A small NuGet/SemVer ordering helper implemented with stdlib only."""
    import re

    clean = version.split("+", 1)[0]
    main, separator, prerelease = clean.partition("-")
    numbers = tuple(int(part) for part in main.split("."))
    pre_parts = []
    if separator:
        for part in prerelease.split("."):
            pre_parts.append((0, int(part)) if part.isdigit() else (1, part.casefold()))
    return numbers, (1, ()) if not separator else (0, tuple(pre_parts))


def _satisfies_version(version: str, version_range: str) -> bool:
    """Check common NuGet exact, minimum and interval version expressions."""
    value = version_range.strip()
    if not value or value == "(не указана)" or value == "*":
        return True
    try:
        candidate = _version_key(version)
        if value[0:1] in "[(" and value[-1:] in ")]":
            body = value[1:-1]
            if "," not in body:
                return candidate == _version_key(body.strip()) if body.strip() else True
            lower, upper = (part.strip() for part in body.split(",", 1))
            if lower:
                lower_key = _version_key(lower)
                if candidate < lower_key or (candidate == lower_key and value[0] == "("):
                    return False
            if upper:
                upper_key = _version_key(upper)
                if candidate > upper_key or (candidate == upper_key and value[-1] == ")"):
                    return False
            return True
        # A bare NuGet version is a minimum inclusive version.
        return candidate >= _version_key(value)
    except (ValueError, TypeError):
        # Unknown/floating syntax: avoid silently claiming a precise match.
        return version.casefold() == value.casefold()


def resolve_dependency_version(package_name: str, version_range: str, repository_url: str) -> str:
    """Resolve a dependency range to the highest matching version in NuGet."""
    index_bytes = _http_get(repository_url)
    try:
        service_index = json.loads(index_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise NuGetError(f"Некорректный JSON service index: {error}") from error
    base_address = _find_package_base_address(service_index, repository_url)
    package_id = urllib.parse.quote(package_name.lower(), safe="")
    versions_url = urllib.parse.urljoin(base_address, f"{package_id}/index.json")
    try:
        payload = json.loads(_http_get(versions_url).decode("utf-8-sig"))
        versions = payload.get("versions", [])
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as error:
        raise NuGetError(f"Не удалось прочитать список версий {package_name}: {error}") from error
    matching = [item for item in versions if isinstance(item, str) and _satisfies_version(item, version_range)]
    if not matching:
        raise NuGetError(
            f"Для зависимости '{package_name}' не найдена версия, подходящая под '{version_range}'."
        )
    try:
        return max(matching, key=_version_key)
    except (ValueError, TypeError):
        return matching[-1]
