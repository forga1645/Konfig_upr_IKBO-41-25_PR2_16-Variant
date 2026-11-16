"""Tests for stage-4 reverse dependency lookup using recursive DFS."""
import unittest
from pathlib import Path

from dependency_visualizer.graph import (
    GraphError,
    find_reverse_dependencies_dfs,
    format_reverse_dependencies,
)
from dependency_visualizer.test_repository import build_test_graph


class ReverseDependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):  # noqa: N802 - required by unittest
        fixture = Path(__file__).parent / "fixtures" / "stage3_graph.json"
        cls.graph = build_test_graph(fixture, "A")

    def test_multiple_direct_reverse_dependencies(self):
        self.assertEqual(
            find_reverse_dependencies_dfs(self.graph, "D"), ["B", "C"]
        )

    def test_single_direct_reverse_dependency(self):
        self.assertEqual(find_reverse_dependencies_dfs(self.graph, "E"), ["C"])

    def test_package_lookup_is_case_insensitive(self):
        actual = find_reverse_dependencies_dfs(self.graph, "d")
        self.assertEqual(actual, ["B", "C"])

    def test_reverse_dependency_through_cycle(self):
        self.assertEqual(find_reverse_dependencies_dfs(self.graph, "A"), ["D"])

    def test_no_reverse_dependencies_in_acyclic_test_repository(self):
        fixture = (
            Path(__file__).parent
            / "fixtures"
            / "stage4_acyclic_graph.json"
        )
        acyclic = build_test_graph(fixture, "A")
        self.assertEqual(find_reverse_dependencies_dfs(acyclic, "A"), [])

    def test_target_not_in_graph(self):
        with self.assertRaisesRegex(GraphError, "отсутствует"):
            find_reverse_dependencies_dfs(self.graph, "Z")

    def test_format_empty_and_nonempty_results(self):
        self.assertIn("Всего: 0", format_reverse_dependencies("Q", []))
        output = format_reverse_dependencies("D", ["B", "C"])
        self.assertIn("- B", output)
        self.assertIn("- C", output)
        self.assertIn("Всего: 2", output)


if __name__ == "__main__":
    unittest.main()
