"""The editor window (Tkinter) and the .modinfo format detection it uses."""
import shutil
import tempfile
import unittest
from pathlib import Path

from modtools.core.compare import compare_projects
from modtools.core.modinfo import modinfo_format, read_modinfo
from tests.helpers import make_mod

DATA = Path(__file__).parent / "data"
MODBUDDY = DATA / "(1) Community Patch (v 139).modinfo"


class TestModinfoFormat(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.project = make_mod(self.tmp)

    def test_modbuddy_build(self):
        self.assertEqual(modinfo_format(MODBUDDY), ("modbuddy", "\r\n"))

    def test_vp_style_lf_and_windows_checkout_crlf(self):
        out = self.tmp / "m.modinfo"
        self.project.write_modinfo(out)
        self.assertEqual(modinfo_format(out), ("vp", "\n"))
        # a Windows checkout (core.autocrlf) of the same LF file: still VP style, CRLF kept
        self.project.write_modinfo(out, newline="\r\n")
        data = out.read_bytes()
        self.assertTrue(data.endswith(b"</Mod>\r\n"))
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
        self.assertEqual(modinfo_format(out), ("vp", "\r\n"))


def _app():
    try:
        from modtools.gui import main as gui
        app = gui.App()
    except Exception as e:  # noqa: BLE001 - no display (CI)
        raise unittest.SkipTest(f"no Tk display: {e}")
    app.withdraw()
    return gui, app


class TestGuiEditing(unittest.TestCase):
    def setUp(self):
        self.gui, self.app = _app()
        self.addCleanup(self.app.destroy)
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.asked = []
        self.answers = []
        orig = self.gui.messagebox.askyesnocancel
        self.gui.messagebox.askyesnocancel = lambda *a, **k: (self.asked.append(a), self.answers.pop(0))[1]
        self.addCleanup(setattr, self.gui.messagebox, "askyesnocancel", orig)

    def test_modbuddy_modinfo_open_save_is_byte_identical(self):
        path = self.tmp / MODBUDDY.name
        shutil.copy2(MODBUDDY, path)  # its files are not there: the MD5s it lists are kept
        before = path.read_bytes()
        self.app.open(path)
        self.assertEqual(self.app.style_var.get(), "modbuddy")
        self.assertTrue(self.app.save())
        self.assertEqual(path.read_bytes(), before)

    def test_text_is_kept_as_typed(self):
        project = make_mod(self.tmp)
        project.teaser, project.authors = "Trailing space ", " Leading space"
        path = self.tmp / "m.modinfo"
        project.write_modinfo(path)
        self.app.open(path)
        shown = self.app.collect()
        self.assertEqual((shown.teaser, shown.authors), (project.teaser, project.authors))
        self.assertEqual(compare_projects(read_modinfo(path), shown), [])

    def test_unsaved_changes_are_offered_for_saving(self):
        path = self.tmp / "m.modinfo"
        make_mod(self.tmp).write_modinfo(path)
        self.app.open(path)
        self.assertFalse(self.app.dirty())
        self.app.new()  # nothing changed: no question
        self.assertEqual(self.asked, [])
        self.assertEqual(self.app.title(), self.gui.APP_TITLE)

        self.app.open(path)
        self.app.text_vars["version"].set("4")
        self.assertTrue(self.app.dirty())
        self.answers = [None]  # Cancel
        self.app.new()
        self.assertEqual(self.app.text_vars["version"].get(), "4")
        self.answers = [False]  # Don't save
        self.app.new()
        self.assertEqual(self.app.path, None)
        self.assertIn('version="3"', path.read_text("utf-8-sig"))

        self.app.open(path)
        self.app.text_vars["version"].set("5")
        self.answers = [True]  # Save
        self.app.new()
        self.assertIn('version="5"', path.read_text("utf-8-sig"))

    def test_close_asks_and_cancel_keeps_the_window(self):
        self.app.text_vars["name"].set("Changed")
        self.answers = [None]
        self.app.quit_app()
        self.assertTrue(self.app.winfo_exists())
        self.assertEqual(len(self.asked), 1)

    def test_table_keeps_the_selection(self):
        t = self.app.actions
        t.set_rows([{"action_set": "OnModActivated", "action_type": "UpdateDatabase", "filename": f"{i}.sql"}
                    for i in range(3)])
        t.tree.selection_set("0")
        t.move(1)
        self.assertEqual(t.tree.selection(), ("1",))
        t.refresh()
        self.assertEqual(t.tree.selection(), ("1",))
        t.remove()
        self.assertEqual([r["filename"] for r in t.rows], ["1.sql", "2.sql"])

    def test_default_import(self):
        (self.tmp / "Panel.xml").write_text('<?xml version="1.0"?>\n<Context ID="P"/>\n')
        (self.tmp / "Data.xml").write_text("<GameData/>\n")
        (self.tmp / "Bad.xml").write_text("<oops")
        (self.tmp / "A.sql").write_text("--\n")
        (self.tmp / "A.lua").write_text("--\n")
        (self.tmp / "A.dds").write_bytes(b"DDS ")
        got = {n: self.gui.default_import(self.tmp / n)
               for n in ("Panel.xml", "Data.xml", "Bad.xml", "A.sql", "A.lua", "A.dds")}
        self.assertEqual(got, {"Panel.xml": True, "Data.xml": False, "Bad.xml": False,
                               "A.sql": False, "A.lua": True, "A.dds": True})


if __name__ == "__main__":
    unittest.main()
