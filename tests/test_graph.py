"""Tests for recursive DFS, cycles and the stage-3 test repository."""
import tempfile
import unittest
from pathlib import Path

from dependency_visualizer.graph import build_graph_dfs, format_graph
from dependency_visualizer.nuget import Dependency
from dependency_visualizer.test_repository import (
    TestRepositoryError,
    build_test_graph,
    load_test_graph,
)


class GraphTests(unittest.TestCase):
    def test_recursive_dfs_and_cycle_detection(self):
        graph = {
            "A": [Dependency("B", "1.0"), Dependency("C", "1.0")],
            "B": [Dependency("D", "1.0")],
            "C": [Dependency("D", "1.0")],
            "D": [Dependency("A", "1.0")],
        }

        def get_dependencies(name, _version):
            return [(item, "1.0") for item in graph[name]]

        result = build_graph_dfs("A", "1.0", get_dependencies)
        self.assertEqual(result.edges["A"], ["B", "C"])
        self.assertEqual(result.edges["D"], ["A"])
        self.assertIn(("D", "A"), result.cycles)
        self.assertIn("цикл", format_graph(result))

    def test_shared_dependency_is_expanded_once(self):
        calls = []
        graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}

        def get_dependencies(name, _version):
            calls.append(name)
            return [(Dependency(child, "*"), "1.0") for child in graph[name]]

        result = build_graph_dfs("A", "1.0", get_dependencies)
        self.assertEqual(calls.count("D"), 1)
        self.assertEqual(result.edges["C"], ["D"])

    def test_load_uppercase_test_repository(self):
        fixture = Path(__file__).parent / "fixtures" / "stage3_graph.json"
        result = build_test_graph(fixture, "A")
        self.assertEqual(result.edges["A"], ["B", "C"])
        self.assertEqual(result.edges["E"], [])
        self.assertIn(("D", "A"), result.cycles)

    def test_reject_lowercase_test_node(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.json"
            path.write_text('{"A": ["b"]}', encoding="utf-8")
            with self.assertRaises(TestRepositoryError):
                load_test_graph(path)

    def test_missing_root(self):
        fixture = Path(__file__).parent / "fixtures" / "stage3_graph.json"
        with self.assertRaises(TestRepositoryError):
            build_test_graph(fixture, "Z")


if __name__ == "__main__":
    unittest.main()
