"""Tests for TOML configuration validation."""

import tempfile
import unittest
from pathlib import Path

from dependency_visualizer.config import load_config


VALID_CONFIG = """package_name = "Newtonsoft.Json"
repository = "https://api.nuget.org/v3/index.json"
test_mode = false
package_version = "13.0.3"
output_file = "dependencies.svg"
ascii_tree = true
"""


class ConfigTests(unittest.TestCase):
    def write_config(self, content: str) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "config.toml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_valid_config(self):
        config = load_config(self.write_config(VALID_CONFIG))
        self.assertEqual(config.package_name, "Newtonsoft.Json")
        self.assertEqual(config.package_version, "13.0.3")
        self.assertTrue(config.ascii_tree)

    def test_invalid_package_name(self):
        content = VALID_CONFIG.replace(
            'package_name = "Newtonsoft.Json"',
            'package_name = "bad name"',
        )
        with self.assertRaisesRegex(ValueError, "package_name"):
            load_config(self.write_config(content))

    def test_invalid_repository_url(self):
        content = VALID_CONFIG.replace(
            "https://api.nuget.org/v3/index.json", "not-a-url"
        )
        with self.assertRaisesRegex(ValueError, "repository"):
            load_config(self.write_config(content))

    def test_invalid_test_mode_type(self):
        content = VALID_CONFIG.replace("test_mode = false", 'test_mode = "no"')
        with self.assertRaisesRegex(ValueError, "test_mode"):
            load_config(self.write_config(content))

    def test_test_repository_must_exist(self):
        content = VALID_CONFIG.replace(
            "https://api.nuget.org/v3/index.json", "missing-repository.json"
        ).replace("test_mode = false", "test_mode = true")
        with self.assertRaisesRegex(ValueError, "тестовом режиме"):
            load_config(self.write_config(content))

    def test_invalid_version(self):
        content = VALID_CONFIG.replace(
            'package_version = "13.0.3"', 'package_version = "??"'
        )
        with self.assertRaisesRegex(ValueError, "package_version"):
            load_config(self.write_config(content))

    def test_invalid_output_file(self):
        content = VALID_CONFIG.replace(
            'output_file = "dependencies.svg"',
            'output_file = "folder/dependencies.png"',
        )
        with self.assertRaisesRegex(ValueError, "output_file"):
            load_config(self.write_config(content))

    def test_invalid_ascii_tree_type(self):
        content = VALID_CONFIG.replace(
            "ascii_tree = true", 'ascii_tree = "yes"'
        )
        with self.assertRaisesRegex(ValueError, "ascii_tree"):
            load_config(self.write_config(content))

    def test_missing_config(self):
        with self.assertRaises(FileNotFoundError):
            load_config("file-that-does-not-exist.toml")


if __name__ == "__main__":
    unittest.main()
