"""validate: rules taken from the game's own parser (see modtools/core/validate.py)."""
import tempfile
import unittest
from pathlib import Path

from modtools.core.civ5proj import civ5proj_text
from modtools.core.models import Action, EntryPoint
from modtools.core.modinfo import write_modinfo
from modtools.core.validate import validate_path
from tests.helpers import make_mod

DATA = Path(__file__).parent / "data"


def messages(issues, severity=None):
    return [i.message for i in issues if severity in (None, i.severity)]


class TestValidate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.project = make_mod(self.tmp)
        self.modinfo = self.tmp / "m.modinfo"
        write_modinfo(self.project, self.modinfo, self.tmp)

    def test_clean_mod(self):
        self.assertEqual(validate_path(self.modinfo), [])
        proj = self.tmp / "m.civ5proj"
        self.project.write_civ5proj(proj)
        self.assertEqual(validate_path(proj), [])
        self.assertEqual(validate_path(proj.with_suffix(".civ5sln")), [])

    def test_stale_md5_warning_or_packaged_error(self):
        (self.tmp / "Lua" / "Main.lua").write_bytes(b"changed")
        self.assertTrue(any("stale md5" in m for m in messages(validate_path(self.modinfo), "warning")))
        self.assertTrue(any("stale md5" in m for m in messages(validate_path(self.modinfo, packaged=True), "error")))

    def test_missing_file_is_an_error(self):
        (self.tmp / "SQL" / "Changes.sql").unlink()
        errors = messages(validate_path(self.modinfo), "error")
        self.assertIn("file not found: SQL\\Changes.sql", errors)
        self.assertTrue(any("UpdateDatabase file not found" in m for m in errors))

    def test_unknown_action_and_entry_point_names(self):
        self.project.actions.append(Action("OnModLoaded", "ImportFiles", "Lua/Main.lua"))
        self.project.entry_points.append(EntryPoint("MyAddin", "UI\\Addin.xml"))
        write_modinfo(self.project, self.modinfo, self.tmp)
        warnings = " | ".join(messages(validate_path(self.modinfo), "warning"))
        for word in ("'ImportFiles'", "'OnModLoaded'", "'MyAddin'"):
            self.assertIn(word, warnings)

    def test_map_entry_point_path_must_match_exactly(self):
        text = self.modinfo.read_text(encoding="utf-8-sig").replace('file="Maps/Small &amp; Wet.lua"',
                                                                    'file="maps\\Small &amp; Wet.lua"')
        self.modinfo.write_text(text, encoding="utf-8-sig")
        self.assertTrue(any("matches them exactly" in m for m in messages(validate_path(self.modinfo), "error")))

    def test_version_and_ids(self):
        text = self.modinfo.read_text(encoding="utf-8-sig").replace('version="3"', 'version="3b"', 1)
        self.modinfo.write_text(text.replace("11111111-2222-3333-4444-555555555555", "not-a-guid"), encoding="utf-8-sig")
        issues = validate_path(self.modinfo)
        self.assertTrue(any("not a whole number" in m for m in messages(issues, "error")))
        self.assertTrue(any("not a GUID" in m for m in messages(issues, "warning")))

    def test_sections_outside_the_property_group_are_an_error(self):
        legacy = civ5proj_text(self.project)
        start, end = legacy.index("    <ModReferences>"), legacy.index("  </PropertyGroup>")
        legacy = legacy[:start] + legacy[end:].replace("</Project>", legacy[start:end] + "</Project>", 1)
        proj = self.tmp / "legacy.civ5proj"
        proj.write_text(legacy, encoding="utf-8")
        errors = messages(validate_path(proj), "error")
        self.assertTrue(any("outside the main <PropertyGroup>" in m for m in errors))

    def test_true_false_booleans_are_accepted(self):
        text = self.modinfo.read_text(encoding="utf-8-sig").replace("<SupportsMac>1<", "<SupportsMac>true<")
        self.modinfo.write_text(text, encoding="utf-8-sig")
        self.assertEqual(validate_path(self.modinfo), [])

    def test_unreadable_and_unknown(self):
        bad = self.tmp / "bad.modinfo"
        bad.write_text("<Mod", encoding="utf-8")
        self.assertTrue(messages(validate_path(bad), "error")[0].startswith("cannot read"))
        self.assertEqual(validate_path(self.tmp / "x.txt")[0].severity, "error")


if __name__ == "__main__":
    unittest.main()
