import random
import unittest

from core.engine.family_generator import assign_years, build_random_binary_topology


def _collect_nodes(node):
    nodes = [node]
    for child in node.children:
        nodes.extend(_collect_nodes(child))
    return nodes


def _collect_leaves(node):
    if not node.children:
        return [node]
    leaves = []
    for child in node.children:
        leaves.extend(_collect_leaves(child))
    return leaves


class TestFamilyGenerator(unittest.TestCase):
    def test_tree_shape_and_years(self):
        rng = random.Random(42)
        root = build_random_binary_topology(6, rng)
        assign_years(root, extant_year=2000, min_branch_years=100, rng=rng)

        leaves = _collect_leaves(root)
        self.assertEqual(len(leaves), 6)
        for leaf in leaves:
            self.assertEqual(leaf.year, 2000)

        nodes = _collect_nodes(root)
        for node in nodes:
            for child in node.children:
                self.assertIsNotNone(node.year)
                self.assertIsNotNone(child.year)
                self.assertLessEqual(node.year, child.year)
                self.assertGreaterEqual(child.year - node.year, 100)


if __name__ == "__main__":
    unittest.main()
