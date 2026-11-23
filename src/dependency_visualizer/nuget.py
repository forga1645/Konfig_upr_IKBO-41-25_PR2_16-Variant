"""Retrieve direct NuGet dependencies using the NuGet V3 HTTP protocol.

No package manager or third-party package is used: urllib performs HTTP,
ElementTree parses the .nuspec XML, and json handles the optional test fixture.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as element_tree


DEFAULT_TIMEOUT = 10
MAX_RETRIES = 2
RETRY_PAUSE = 1.0
HTTP_NOT_FOUND = 404
USER_AGENT = "dependency-visualizer/0.2"


@dataclass(frozen=True)
class Dependency:
    """Direct dependency metadata extracted from a NuGet package."""

    package_id: str
    version_range: str
    target_framework: str = "all"


class NuGetError(Exception):
    """A readable error while querying a NuGet repository."""


def _local_name(tag: str) -> str:
    """Return an XML tag without its optional namespace."""
    return tag.rsplit("}", 1)[-1]


def _find_dependencies_node(root: element_tree.Element):
    """Find the package's dependencies element, ignoring XML namespaces."""
    for node in root.iter():
        if _local_name(node.tag) == "dependencies":
            return node
    return None


def _append_dependency(
    node: element_tree.Element,
    framework: str,
    seen: set[tuple[str, str, str]],
    result: list[Dependency],
) -> None:
    """Append a dependency once, retaining its framework and version range."""
    package_id = node.attrib.get("id", "").strip()
    version_range = node.attrib.get("version", "").strip() or "(не указана)"
    if not package_id:
        return
    key = (package_id.casefold(), version_range, framework)
    if key not in seen:
        seen.add(key)
        result.append(Dependency(package_id, version_range, framework))


def _parse_dependency_groups(
    node: element_tree.Element,
    result: list[Dependency],
    seen: set[tuple[str, str, str]],
) -> None:
    """Extract dependencies from target-framework groups or flat metadata."""
    children = list(node)
    groups = [item for item in children if _local_name(item.tag) == "group"]
    if groups:
        for group in groups:
            framework = group.attrib.get("targetFramework", "all") or "all"
            for dependency in group:
                if _local_name(dependency.tag) == "dependency":
                    _append_dependency(dependency, framework, seen, result)
        return
    for dependency in children:
        if _local_name(dependency.tag) == "dependency":
            _append_dependency(dependency, "all", seen, result)


def parse_nuspec(xml_content: str | bytes) -> list[Dependency]:
    """Extract direct dependencies from a NuGet .nuspec document.

    Dependencies in every target-framework group are returned. The framework
    is retained so that alternatives for different frameworks are not hidden.
    """
    try:
        root = element_tree.fromstring(xml_content)
    except element_tree.ParseError as error:
        message = f"Некорректный XML .nuspec: {error}"
        raise NuGetError(message) from error
    dependencies_node = _find_dependencies_node(root)
    if dependencies_node is None:
        return []
    result: list[Dependency] = []
    seen: set[tuple[str, str, str]] = set()
    _parse_dependency_groups(dependencies_node, result, seen)
    return result


def _http_get(url: str, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    """Fetch a URL and convert transport failures into NuGetError."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, application/xml, */*",
    }
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code == HTTP_NOT_FOUND:
                message = f"Пакет или версия не найдены (HTTP 404): {url}"
            else:
                message = f"Ошибка HTTP {error.code} при обращении к NuGet: {url}"
            raise NuGetError(message) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = error
            print(
                f"[DEBUG] попытка {attempt}/{MAX_RETRIES} для {url}: "
                f"{type(error).__name__}: {error}",
                file=sys.stderr,
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_PAUSE)
                continue
    message = (
        f"Не удалось обратиться к репозиторию NuGet ({url}) "
        f"после {MAX_RETRIES} попыток: {last_error}"
    )
    raise NuGetError(message) from last_error


def _find_package_base_address(
    service_index: dict,
    repository_url: str,
) -> str:
    """Find the NuGet flat-container endpoint in a V3 service index."""
    resources = service_index.get("resources", [])
    for resource in resources:
        resource_type = resource.get("@type", "")
        types = (
            resource_type
            if isinstance(resource_type, list)
            else [resource_type]
        )
        is_package_base = any(
            str(value).startswith("PackageBaseAddress/") for value in types
        )
        base = resource.get("@id")
        if is_package_base and isinstance(base, str) and base:
            return base.rstrip("/") + "/"
    if "flatcontainer" in repository_url.lower():
        return repository_url.rstrip("/") + "/"
    message = (
        "В service index репозитория не найден ресурс PackageBaseAddress. "
        "Укажите URL NuGet V3 service index."
    )
    raise NuGetError(message)


def _decode_service_index(index_bytes: bytes) -> dict:
    """Decode and validate a NuGet V3 service index response."""
    try:
        service_index = json.loads(index_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        message = f"Репозиторий вернул некорректный JSON service index: {error}"
        raise NuGetError(message) from error
    if not isinstance(service_index, dict):
        message = (
            "Некорректный формат NuGet service index: "
            "ожидался JSON-объект."
        )
        raise NuGetError(message)
    return service_index


def fetch_dependencies(
    package_name: str,
    package_version: str,
    repository_url: str,
) -> list[Dependency]:
    """Fetch one exact package version from a NuGet V3 service index."""
    index_bytes = _http_get(repository_url)
    service_index = _decode_service_index(index_bytes)
    base_address = _find_package_base_address(service_index, repository_url)
    package_id = urllib.parse.quote(package_name.lower(), safe="")
    version = urllib.parse.quote(package_version.lower(), safe="")
    package_path = f"{package_id}/{version}/{package_id}.nuspec"
    nuspec_url = urllib.parse.urljoin(base_address, package_path)
    return parse_nuspec(_http_get(nuspec_url))


def _find_test_package(data: dict, package_name: str, version: str) -> list:
    """Find one package version in a test fixture."""
    try:
        package_versions = next(
            value for key, value in data["packages"].items()
            if key.casefold() == package_name.casefold()
        )
        package_data = package_versions[version]
        return package_data.get("dependencies", [])
    except (KeyError, StopIteration, TypeError, AttributeError) as error:
        message = (
            f"В тестовом репозитории не найден пакет '{package_name}' "
            f"версии '{version}'."
        )
        raise NuGetError(message) from error


def _read_test_fixture(path: Path) -> dict:
    """Read a JSON test fixture and normalize file/JSON errors."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        message = f"Не удалось прочитать тестовый репозиторий: {error}"
        raise NuGetError(message) from error
    except json.JSONDecodeError as error:
        message = f"Некорректный JSON тестового репозитория: {error}"
        raise NuGetError(message) from error


def _convert_test_dependencies(items: list) -> list[Dependency]:
    """Convert fixture entries to Dependency objects."""
    dependencies = []
    for item in items:
        valid_item = isinstance(item, dict)
        valid_id = valid_item and isinstance(item.get("id"), str)
        if not valid_id:
            message = "Каждая тестовая зависимость должна содержать "
            raise NuGetError(message + "строковое поле 'id'.")
        dependencies.append(
            Dependency(
                package_id=item["id"],
                version_range=str(item.get("version", "(не указана)")),
                target_framework=str(item.get("target_framework", "all")),
            )
        )
    return dependencies


def load_test_dependencies(
    repository_file: str | Path,
    package_name: str,
    package_version: str,
) -> list[Dependency]:
    """Load dependencies from a small JSON fixture (offline test mode).

    Fixture schema: {"packages": {"Package.Id": {"1.0.0":
    {"dependencies": [{"id": "Other.Id", "version": "[2.0.0]",
    "target_framework": "net8.0"}]}}}}
    """
    path = Path(repository_file).expanduser()
    data = _read_test_fixture(path)
    items = _find_test_package(data, package_name, package_version)
    return _convert_test_dependencies(items)


def _version_key(version: str):
    """Return a comparable key for common NuGet/SemVer version strings."""
    clean = version.split("+", 1)[0]
    main, separator, prerelease = clean.partition("-")
    numbers = tuple(int(part) for part in main.split("."))
    numbers += (0,) * (4 - len(numbers)) # добавить недостающие нули
    pre_parts = []
    if separator:
        for part in prerelease.split("."):
            value = (0, int(part)) if part.isdigit() else (1, part.casefold())
            pre_parts.append(value)
    release_key = (1, ()) if not separator else (0, tuple(pre_parts))
    return numbers, release_key


def _is_interval(value: str) -> bool:
    """Return whether a version expression is a bracketed interval."""
    return value.startswith(("[", "(")) and value.endswith(("]", ")"))


def _matches_exact_interval(candidate, body: str) -> bool:
    """Check an exact NuGet interval such as [1.2.3]."""
    return candidate == _version_key(body.strip()) if body.strip() else True


def _matches_lower_bound(candidate, lower: str, inclusive: bool) -> bool:
    """Check a lower endpoint of a version interval."""
    if not lower:
        return True
    lower_key = _version_key(lower)
    return candidate > lower_key or (inclusive and candidate == lower_key)


def _matches_upper_bound(candidate, upper: str, inclusive: bool) -> bool:
    """Check an upper endpoint of a version interval."""
    if not upper:
        return True
    upper_key = _version_key(upper)
    return candidate < upper_key or (inclusive and candidate == upper_key)


def _matches_interval(candidate, value: str) -> bool:
    """Check exact and bounded NuGet interval expressions."""
    body = value[1:-1]
    if "," not in body:
        return _matches_exact_interval(candidate, body)
    lower, upper = (part.strip() for part in body.split(",", 1))
    lower_ok = _matches_lower_bound(candidate, lower, value[0] == "[")
    upper_ok = _matches_upper_bound(candidate, upper, value[-1] == "]")
    return lower_ok and upper_ok


def _satisfies_version(version: str, version_range: str) -> bool:
    """Check common NuGet exact, minimum and interval version expressions."""
    value = version_range.strip()
    if not value or value in {"(не указана)", "*"}:
        return True
    try:
        candidate = _version_key(version)
        if _is_interval(value):
            return _matches_interval(candidate, value)
        return candidate >= _version_key(value)
    except (ValueError, TypeError):
        return version.casefold() == value.casefold()


def _fetch_version_list(package_name: str, repository_url: str) -> list[str]:
    """Fetch and decode the available versions for one package."""
    index = _decode_service_index(_http_get(repository_url))
    base = _find_package_base_address(index, repository_url)
    package_id = urllib.parse.quote(package_name.lower(), safe="")
    versions_url = urllib.parse.urljoin(base, f"{package_id}/index.json")
    try:
        payload = json.loads(_http_get(versions_url).decode("utf-8-sig"))
        return payload.get("versions", [])
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as error:
        message = f"Не удалось прочитать список версий {package_name}: {error}"
        raise NuGetError(message) from error


def _matching_versions(versions: list, version_range: str) -> list[str]:
    """Filter version strings using the requested NuGet version range."""
    return [
        item for item in versions
        if isinstance(item, str) and _satisfies_version(item, version_range)
    ]


def resolve_dependency_version(
    package_name: str,
    version_range: str,
    repository_url: str,
) -> str:
    """Resolve a dependency range to the highest matching NuGet version."""
    versions = _fetch_version_list(package_name, repository_url)
    matching = _matching_versions(versions, version_range)
    if not matching:
        message = (
            f"Для зависимости '{package_name}' не найдена версия, "
            f"подходящая под '{version_range}'."
        )
        raise NuGetError(message)
    try:
        return max(matching, key=_version_key)
    except (ValueError, TypeError):
        return matching[-1]
