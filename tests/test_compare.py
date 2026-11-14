"""compare_projects: duplicates and action order."""
import copy
import shutil
import tempfile
import unittest
from pathlib import Path

from modtools.core.compare import compare_projects
from modtools.core.models import Action, EntryPoint
from modtools.core.modinfo import read_modinfo
from tests.helpers import make_mod


class TestCompare(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.a = make_mod(self.tmp)
        self.b = copy.deepcopy(self.a)

    def test_same(self):
        self.assertEqual(compare_projects(self.a, self.b), [])

    def test_duplicate_action_is_a_difference(self):
        self.b.actions.append(copy.copy(self.b.actions[0]))
        self.assertEqual(compare_projects(self.a, self.b),
                         ["actions: only in second: ('OnModActivated', 'UpdateDatabase', 'sql/changes.sql')"])
        self.b.actions.append(copy.copy(self.b.actions[0]))
        self.assertEqual(compare_projects(self.a, self.b),
                         ["actions: only in second: ('OnModActivated', 'UpdateDatabase', 'sql/changes.sql') (x2)"])

    def test_duplicate_entry_point_is_a_difference(self):
        self.a.entry_points.append(copy.copy(self.a.entry_points[0]))
        self.assertEqual(compare_projects(self.a, self.b),
                         ["entry points: only in first: ('InGameUIAddin', 'ui/addin.xml', 'Addin', 'The addin')"])

    def test_order_within_a_set_matters(self):
        self.b.actions.reverse()
        self.assertEqual(compare_projects(self.a, self.b),
                         ["actions: OnModActivated: same actions in a different order (they run in that order)"])

    def test_order_across_sets_does_not(self):
        # a .civ5proj may interleave sets; its .modinfo groups them, and that is the same mod
        self.a.actions.insert(1, Action("OnCreateModUserData", "UpdateUserData", "SQL/Changes.sql"))
        self.a.write_modinfo(self.tmp / "m.modinfo")
        written = read_modinfo(self.tmp / "m.modinfo")
        self.assertEqual([x.action_set for x in written.actions],
                         ["OnModActivated", "OnModActivated", "OnCreateModUserData"])
        self.assertEqual(compare_projects(self.a, written), [])

    def test_entry_point_order_does_not_matter(self):
        self.b.entry_points.reverse()
        self.b.entry_points.append(EntryPoint("Custom", "UI/Addin.xml"))
        self.assertEqual(compare_projects(self.a, self.b),
                         ["entry points: only in second: ('Custom', 'ui/addin.xml', '', '')"])


if __name__ == "__main__":
    unittest.main()
