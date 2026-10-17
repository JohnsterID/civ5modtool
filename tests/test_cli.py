"""The modtools command line, compare and the GUI."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from modtools.cli.main import main
from modtools.core.compare import compare_projects
from modtools.core.models import FileEntry
from tests.helpers import make_mod


def run(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = main([str(a) for a in args])
    return code, out.getvalue()


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.project = make_mod(self.tmp)
        self.proj = self.tmp / "Test Mod.civ5proj"
        self.project.write_civ5proj(self.proj)

    def test_proj2modinfo_default_name_and_folder_argument(self):
        code, out = run("proj2modinfo", self.tmp)
        self.assertEqual(code, 0, out)
        self.assertTrue((self.tmp / "(7) Test Mod (v 3).modinfo").is_file())

    def test_strict_missing(self):
        (self.tmp / "UI" / "Addin.xml").unlink()
        self.assertEqual(run("proj2modinfo", self.proj)[0], 0)
        self.assertEqual(run("proj2modinfo", self.proj, "--strict")[0], 1)

    def test_modinfo2proj_and_compare(self):
        run("proj2modinfo", self.proj)
        mi = self.tmp / "(7) Test Mod (v 3).modinfo"
        out = self.tmp / "rebuilt" / "R.civ5proj"
        out.parent.mkdir()
        code, text = run("modinfo2proj", mi, "-o", out)
        self.assertEqual(code, 0, text)
        self.assertTrue(out.with_suffix(".civ5sln").is_file())
        self.assertEqual(run("compare", self.proj, out)[0], 0)
        self.assertEqual(run("compare", mi, self.proj)[0], 0)

    def test_update_md5_check_and_fix(self):
        run("proj2modinfo", self.proj)
        mi = self.tmp / "(7) Test Mod (v 3).modinfo"
        self.assertEqual(run("update-md5", "--check", mi)[0], 0)
        (self.tmp / "Lua" / "Main.lua").write_bytes(b"new")
        self.assertEqual(run("update-md5", "--check", mi)[0], 1)
        self.assertEqual(run("update-md5", mi)[0], 0)
        self.assertEqual(run("update-md5", "--check", mi)[0], 0)

    def test_validate_exit_codes(self):
        self.assertEqual(run("validate", self.proj)[0], 0)
        (self.tmp / "Lua" / "Main.lua").unlink()
        self.assertEqual(run("validate", self.proj)[0], 1)

    def test_errors_are_exit_2(self):
        self.assertEqual(run("proj2modinfo", self.tmp / "nope.civ5proj")[0], 2)
        self.assertEqual(run()[0], 2)

    def test_compare_reports_differences(self):
        other = make_mod(Path(tempfile.mkdtemp()))
        other.version = "4"
        other.files.append(FileEntry("Extra.lua", True))
        diffs = compare_projects(self.project, other)
        self.assertIn("version: '3' != '4'", diffs)
        self.assertIn("files: only in second: Extra.lua", diffs)


class TestGui(unittest.TestCase):
    def test_load_and_collect_loses_nothing(self):
        try:
            from modtools.gui.main import App
            app = App()
        except Exception as e:  # noqa: BLE001 - no display (CI)
            self.skipTest(f"no Tk display: {e}")
        try:
            app.withdraw()
            tmp = Path(tempfile.mkdtemp())
            project = make_mod(tmp)
            proj = tmp / "Test Mod.civ5proj"
            project.write_civ5proj(proj)
            app.open(proj)
            self.assertEqual(compare_projects(project, app.collect()), [])
            out = tmp / "saved.modinfo"
            app.write(out)
            self.assertIn("all files hashed", app.status.get())
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
