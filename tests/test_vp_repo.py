"""Against a Vox Populi checkout (Community-Patch-DLL), the reference for the formats.

Set VP_REPO to the checkout to run these, e.g.
    VP_REPO=../Community-Patch-DLL python -m pytest tests/test_vp_repo.py
Nothing is written into the checkout.
"""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

from modtools.core.civ5proj import read_civ5proj, write_civ5proj
from modtools.core.compare import compare_projects
from modtools.core.md5 import update_md5
from modtools.core.modinfo import modinfo_text, read_modinfo
from modtools.core.validate import validate_path

REPO = Path(os.environ["VP_REPO"]) if os.environ.get("VP_REPO") else None


@unittest.skipUnless(REPO and (REPO / "scripts" / "generate_modinfo.py").is_file(), "VP_REPO not set")
class TestVoxPopuli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("generate_modinfo", REPO / "scripts" / "generate_modinfo.py")
        cls.upstream = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.upstream)
        cls.projects = sorted(REPO.glob("(*/*.civ5proj"))
        assert cls.projects, "no (N) mod folders in VP_REPO"

    @unittest.skipUnless(os.name == "nt", "generate_modinfo.py resolves the projects' '\\' paths with pathlib, "
                                          "which only works on Windows (elsewhere it leaves those files out)")
    def test_proj2modinfo_matches_generate_modinfo(self):
        for proj in self.projects:
            with self.subTest(proj.parent.name):
                expected, _ = self.upstream.generate_modinfo_xml(self.upstream.parse_civ5proj(proj), proj.parent)
                self.assertEqual(modinfo_text(read_civ5proj(proj), proj.parent)[0], expected)

    def test_committed_modinfo_survives_a_civ5proj_roundtrip(self):
        tmp = Path(tempfile.mkdtemp())
        for mi in sorted(REPO.glob("(*/*.modinfo")):
            with self.subTest(mi.parent.name):
                committed = mi.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
                proj = tmp / (mi.parent.name + ".civ5proj")
                write_civ5proj(read_modinfo(mi), proj)
                rebuilt = read_civ5proj(proj)
                self.assertEqual(modinfo_text(rebuilt, mi.parent)[0], committed)
                self.assertEqual(compare_projects(read_civ5proj(next(mi.parent.glob("*.civ5proj"))), rebuilt), [])

    def test_committed_md5s_are_current(self):
        for mi in sorted(REPO.glob("(*/*.modinfo")):
            with self.subTest(mi.parent.name):
                self.assertTrue(update_md5(mi, check_only=True).clean)

    def test_solutions_validate(self):
        for sln in sorted(REPO.glob("(*/*.civ5sln")):
            with self.subTest(sln.parent.name):
                self.assertEqual(validate_path(sln), [])


if __name__ == "__main__":
    unittest.main()
