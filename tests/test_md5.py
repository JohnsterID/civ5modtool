"""update-md5: only the md5 values change."""
import tempfile
import unittest
from pathlib import Path

from modtools.core.md5 import update_md5
from modtools.core.modinfo import write_modinfo
from tests.helpers import make_mod


class TestUpdateMd5(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        write_modinfo(make_mod(self.tmp), self.tmp / "m.modinfo", self.tmp, "modbuddy")
        self.modinfo = self.tmp / "m.modinfo"
        self.original = self.modinfo.read_bytes()

    def test_current_file_is_untouched(self):
        r = update_md5(self.modinfo)
        self.assertTrue(r.clean)
        self.assertEqual(r.unchanged, 5)
        self.assertEqual(self.modinfo.read_bytes(), self.original)

    def test_stale_md5_is_fixed_and_nothing_else_changes(self):
        (self.tmp / "Lua" / "Main.lua").write_bytes(b"print('changed')\n")
        self.assertEqual(update_md5(self.modinfo, check_only=True).changed, ["Lua/Main.lua"])
        self.assertEqual(self.modinfo.read_bytes(), self.original)  # --check writes nothing
        r = update_md5(self.modinfo)
        self.assertEqual(r.changed, ["Lua/Main.lua"])
        new = self.modinfo.read_bytes()
        self.assertTrue(new.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(len(new), len(self.original))  # same layout, CRLF, no trailing newline
        changed = [i for i, (a, b) in enumerate(zip(new, self.original)) if a != b]
        self.assertLessEqual(len(changed), 32)
        self.assertTrue(update_md5(self.modinfo).clean)

    def test_adds_missing_md5_and_reports_missing_files(self):
        text = self.modinfo.read_text(encoding="utf-8-sig")
        start = text.index('<File md5="')
        end = text.index('" import', start)
        self.modinfo.write_text(text[:start] + "<File" + text[end + 1:], encoding="utf-8-sig")
        (self.tmp / "UI" / "Addin.xml").unlink()
        r = update_md5(self.modinfo)
        self.assertEqual(r.changed, ["Lua/Main.lua"])
        self.assertEqual(r.missing, ["UI/Addin.xml"])
        self.assertIn('<File md5="', self.modinfo.read_text(encoding="utf-8-sig")[start:start + 20])

    def test_entities_in_paths(self):
        (self.tmp / "Maps" / "Small & Wet.lua").write_bytes(b"-- changed\n")
        self.assertEqual(update_md5(self.modinfo).changed, ["Maps/Small & Wet.lua"])


if __name__ == "__main__":
    unittest.main()
