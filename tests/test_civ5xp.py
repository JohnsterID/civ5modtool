"""Civ5XP (Linux): lower-case install and the --civ5xp check."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from modtools.core import civ5xp
from modtools.core.md5 import update_md5
from modtools.core.modinfo import write_modinfo
from modtools.core.validate import validate_path
from modtools.core.xmltext import disk_parts, mod_file_path
from tests.helpers import make_mod


class TestCiv5XP(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.mod = root / "(7) Test Mod"
        self.mod.mkdir()
        write_modinfo(make_mod(self.mod), self.mod / "(7) Test Mod (v 3).modinfo", self.mod)
        self.modinfo = self.mod / "(7) Test Mod (v 3).modinfo"
        self.mods_dir = root / "Aspyr" / "Sid Meier's Civilization 5" / "MODS"

    def test_mixed_case_names_fail_the_civ5xp_check(self):
        self.assertEqual(validate_path(self.modinfo), [])  # fine on Windows
        issues = validate_path(self.modinfo, civ5xp=True)
        errors = [i.message for i in issues if i.severity == "error"]
        self.assertTrue(any("'lua/main.lua'" in m and "'Lua/Main.lua'" in m for m in errors), errors)
        self.assertTrue(any("mod folder" in i.message for i in issues if i.severity == "warning"))

    def test_install_lower_cases_everything_and_validates(self):
        r = civ5xp.install(self.mod, self.mods_dir)
        self.assertEqual(r.collisions, {})
        self.assertEqual(r.target, self.mods_dir / "(7) test mod")
        self.assertEqual(r.copied, 6)  # 5 files + the .modinfo
        names = sorted(p.relative_to(r.target).as_posix() for p in r.target.rglob("*") if p.is_file())
        self.assertEqual(names, sorted(n.lower() for n in names))
        installed = r.target / "(7) test mod (v 3).modinfo"
        self.assertEqual(validate_path(installed, civ5xp=True), [])
        self.assertTrue(update_md5(installed, check_only=True).clean)  # the listed Windows case still resolves
        self.assertEqual(self.modinfo.read_bytes(), installed.read_bytes())  # .modinfo content unchanged

    def test_install_refuses_existing_target_and_collisions(self):
        civ5xp.install(self.mod, self.mods_dir)
        with self.assertRaises(FileExistsError):
            civ5xp.install(self.mod, self.mods_dir)
        self.assertEqual(civ5xp.install(self.mod, self.mods_dir, replace=True).copied, 6)
        walk = [(str(self.mod), [], ["Foo.lua", "foo.lua"])]  # cannot exist side by side on Windows
        with mock.patch.object(civ5xp.os, "walk", return_value=walk):
            r = civ5xp.install(self.mod, self.mods_dir / "other")
        self.assertEqual(r.collisions, {"foo.lua": ["Foo.lua", "foo.lua"]})
        self.assertFalse((self.mods_dir / "other").exists())

    def test_dry_run_copies_nothing(self):
        r = civ5xp.install(self.mod, self.mods_dir, dry_run=True)
        self.assertEqual(r.copied, 6)
        self.assertFalse(r.target.exists())

    def test_default_mods_dir(self):
        with mock.patch.dict(os.environ, {"XDG_DATA_HOME": "/data"}):
            self.assertEqual(civ5xp.default_mods_dir().as_posix(), "/data/Aspyr/Sid Meier's Civilization 5/MODS")
        with mock.patch.dict(os.environ, {"XDG_DATA_HOME": ""}):
            self.assertEqual(civ5xp.default_mods_dir(),
                             Path.home() / ".local" / "share" / "Aspyr" / "Sid Meier's Civilization 5" / "MODS")

    def test_case_insensitive_lookup(self):
        self.assertEqual(disk_parts(self.mod, "LUA\\MAIN.LUA"), ["Lua", "Main.lua"])
        self.assertIsNone(disk_parts(self.mod, "Lua/Missing.lua"))
        self.assertTrue(mod_file_path(self.mod, "lua/main.lua").is_file())


if __name__ == "__main__":
    unittest.main()
