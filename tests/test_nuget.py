"""Tests for NuGet metadata parsing and retrieval."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dependency_visualizer.nuget import (
    Dependency,
    NuGetError,
    fetch_dependencies,
    load_test_dependencies,
    parse_nuspec,
    resolve_dependency_version,
)


NUSPEC = '''<?xml version="1.0"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>Example.Library</id>
    <version>1.2.0</version>
    <dependencies>
      <group targetFramework="net8.0">
        <dependency id="System.Text.Json" version="[8.0.0, 9.0.0)" />
        <dependency id="Microsoft.Extensions.Logging.Abstractions" version="8.0.0" />
      </group>
      <group targetFramework="net6.0">
        <dependency id="System.Text.Json" version="[7.0.0, 8.0.0)" />
      </group>
    </dependencies>
  </metadata>
</package>'''


class NuGetTests(unittest.TestCase):
    def test_parse_nuspec_with_framework_groups(self):
        dependencies = parse_nuspec(NUSPEC)
        self.assertEqual(len(dependencies), 3)
        self.assertEqual(dependencies[0], Dependency(
            "System.Text.Json", "[8.0.0, 9.0.0)", "net8.0"
        ))
        self.assertEqual(dependencies[2].target_framework, "net6.0")

    def test_parse_nuspec_without_dependencies(self):
        self.assertEqual(parse_nuspec("<package><metadata><id>A</id></metadata></package>"), [])

    def test_invalid_nuspec(self):
        with self.assertRaisesRegex(NuGetError, "XML"):
            parse_nuspec("<package>")

    @patch("dependency_visualizer.nuget._http_get")
    def test_fetch_dependencies_from_v3_service_index(self, http_get):
        service_index = {
            "resources": [{
                "@id": "https://api.nuget.org/v3-flatcontainer/",
                "@type": "PackageBaseAddress/3.0.0",
            }]
        }
        http_get.side_effect = [json.dumps(service_index).encode(), NUSPEC.encode()]
        dependencies = fetch_dependencies(
            "Example.Library", "1.2.0", "https://api.nuget.org/v3/index.json"
        )
        self.assertEqual(len(dependencies), 3)
        self.assertEqual(http_get.call_count, 2)
        self.assertIn(
            "example.library/1.2.0/example.library.nuspec",
            http_get.call_args_list[1].args[0],
        )

    def test_load_test_repository_for_exact_version(self):
        fixture = {
            "packages": {
                "Example.Library": {
                    "1.2.0": {"dependencies": [{
                        "id": "System.Text.Json",
                        "version": "8.0.0",
                        "target_framework": "net8.0",
                    }]}
                }
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "repo.json"
            path.write_text(json.dumps(fixture), encoding="utf-8")
            dependencies = load_test_dependencies(path, "example.library", "1.2.0")
        self.assertEqual(dependencies, [Dependency("System.Text.Json", "8.0.0", "net8.0")])

    @patch("dependency_visualizer.nuget._http_get")
    def test_resolve_dependency_version_uses_highest_matching_range(self, http_get):
        service_index = {"resources": [{
            "@id": "https://api.nuget.org/v3-flatcontainer/",
            "@type": "PackageBaseAddress/3.0.0",
        }]}
        versions = {"versions": ["7.0.0", "8.0.0", "8.1.0", "9.0.0"]}
        http_get.side_effect = [
            json.dumps(service_index).encode(),
            json.dumps(versions).encode(),
        ]
        selected = resolve_dependency_version(
            "System.Text.Json", "[8.0.0, 9.0.0)",
            "https://api.nuget.org/v3/index.json",
        )
        self.assertEqual(selected, "8.1.0")

    def test_test_repository_rejects_missing_version(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "repo.json"
            path.write_text('{"packages": {"A": {"1.0": {"dependencies": []}}}}', encoding="utf-8")
            with self.assertRaisesRegex(NuGetError, "не найден"):
                load_test_dependencies(path, "A", "2.0")


if __name__ == "__main__":
    unittest.main()
