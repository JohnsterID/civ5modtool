"""Against a Vox Populi checkout (Community-Patch-DLL), the reference for the formats.

Set VP_REPO to the checkout to run these, e.g.
    VP_REPO=../Community-Patch-DLL python -m pytest tests/test_vp_repo.py
Nothing is written into the checkout.
"""
import hashlib
import importlib.util
import os
import re
import tempfile
import unittest
from html import unescape
from pathlib import Path

from modtools.core.civ5proj import read_civ5proj, write_civ5proj
from modtools.core.compare import compare_projects
from modtools.core.md5 import update_md5
from modtools.core.modinfo import modinfo_text, read_modinfo
from modtools.core.validate import validate_path
from modtools.core.xmltext import mod_file_path

# VP refreshes the MD5s in its committed .modinfo files when it releases, so between
# releases some of them are out of date. The tests below check the tool, not that.
_MD5_VALUE = re.compile(r'md5="[0-9A-Fa-f]*"')
_FILE = re.compile(r'<File md5="([0-9A-Fa-f]*)"[^>]*>([^<]+)</File>')

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
                text = modinfo_text(rebuilt, mi.parent)[0]
                self.assertEqual(_MD5_VALUE.sub('md5=""', text), _MD5_VALUE.sub('md5=""', committed))

    def test_project_survives_a_modinfo_roundtrip(self):
        # From VP's current .civ5proj, not its committed .modinfo: that one can lag the
        # project until VP's next release (files added since are missing from it).
        tmp = Path(tempfile.mkdtemp())
        for proj in self.projects:
            with self.subTest(proj.parent.name):
                original = read_civ5proj(proj)
                text = modinfo_text(original, proj.parent)[0]
                mi = tmp / (proj.parent.name + ".modinfo")
                mi.write_text(text, encoding="utf-8")
                back = tmp / (proj.parent.name + ".civ5proj")
                write_civ5proj(read_modinfo(mi), back)
                rebuilt = read_civ5proj(back)
                self.assertEqual(compare_projects(original, rebuilt), [])
                self.assertEqual(modinfo_text(rebuilt, proj.parent)[0], text)

    def test_md5_check_flags_exactly_the_stale_files(self):
        for mi in sorted(REPO.glob("(*/*.modinfo")):
            with self.subTest(mi.parent.name):
                stale, missing = [], []
                for md5, path in _FILE.findall(mi.read_bytes().decode("utf-8-sig")):
                    path = unescape(path)
                    disk = mod_file_path(mi.parent, path.strip())
                    if not disk.is_file():
                        missing.append(path.strip())
                    elif hashlib.md5(disk.read_bytes()).hexdigest().upper() != md5.upper():
                        stale.append(path.strip())
                report = update_md5(mi, check_only=True)
                self.assertEqual((report.changed, report.missing), (stale, missing))

    def test_solutions_validate(self):
        for sln in sorted(REPO.glob("(*/*.civ5sln")):
            with self.subTest(sln.parent.name):
                self.assertEqual(validate_path(sln), [])


if __name__ == "__main__":
    unittest.main()
