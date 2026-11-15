import tempfile
import unittest
from pathlib import Path

from dependency_visualizer.graph import GraphResult
from dependency_visualizer.visualization import generate_dot, format_ascii_tree, render_svg


class VisualizationTests(unittest.TestCase):
    def setUp(self):
        self.graph = GraphResult(
            root="A",
            edges={"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": ["A"]},
            cycles=[("D", "A")],
            resolved_versions={"A": "1.0", "B": "2.0", "C": "3.0", "D": "4.0"},
        )

    def test_dot_contains_nodes_edges_and_cycle_style(self):
        dot = generate_dot(self.graph)
        self.assertIn('digraph dependencies {', dot)
        self.assertIn('"A" -> "B";', dot)
        self.assertIn('"D" -> "A" [color="firebrick", penwidth="2"];', dot)
        self.assertIn("A\\\\n1.0", dot)

    def test_ascii_tree_marks_shared_nodes_and_cycles(self):
        tree = format_ascii_tree(self.graph)
        self.assertIn("A", tree)
        self.assertIn("D [already shown]", tree)
        self.assertIn("A [cycle]", tree)

    @unittest.skipUnless(__import__("shutil").which("dot"), "Graphviz dot is not installed")
    def test_render_svg_creates_nonempty_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "graph.svg"
            render_svg(generate_dot(self.graph), target)
            self.assertTrue(target.is_file())
            self.assertIn("<svg", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
