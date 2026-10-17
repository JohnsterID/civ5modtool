"""The .civ5proj reader and writer, and conversions between the formats."""
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from modtools.core.civ5proj import NS, civ5proj_text, default_civ5proj_path, read_civ5proj
from modtools.core.compare import compare_projects
from modtools.core.modinfo import modinfo_text, read_modinfo
from modtools.core.models import ModProject, project_guid_for
from tests.helpers import make_mod

DATA = Path(__file__).parent / "data"
Q = lambda tag: f"{{{NS}}}{tag}"  # noqa: E731


class TestCiv5Proj(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.project = make_mod(self.tmp)

    def test_modbuddy_layout(self):
        root = ET.fromstring(civ5proj_text(self.project))
        props = root.find(Q("PropertyGroup"))
        for tag in ("ModReferences", "ModDependencies", "ModBlockers", "ModActions", "ModContent"):
            self.assertIsNotNone(props.find(Q(tag)), f"{tag} must be inside the main PropertyGroup")
            self.assertIsNone(root.find(Q(tag)), f"{tag} must not be at the project root")
        flags = [c.find(Q("ImportIntoVFS")).text for c in root.iter(Q("Content")) if c.get("Include")]
        self.assertEqual(flags, ["True", "False", "False", "True", "True"])
        self.assertEqual([f.get("Include") for f in root.iter(Q("Folder"))], ["Lua", "SQL", "Text", "Text\\en_US", "UI", "Maps"])
        self.assertEqual(root.find(Q("Import")).get("Project"), "$(MSBuildExtensionsPath)\\Firaxis\\ModBuddy\\Civ5Mod.targets")
        self.assertEqual(props.find(Q("ProjectGuid")).text, project_guid_for(self.project.mod_guid))

    def test_civ5proj_roundtrip(self):
        path = self.tmp / "Test Mod.civ5proj"
        self.project.write_civ5proj(path, create_solution=False)
        again = read_civ5proj(path)
        self.assertEqual(compare_projects(self.project, again), [])
        self.assertEqual(civ5proj_text(again), civ5proj_text(self.project))

    def test_write_uses_the_given_path(self):
        """The project is written exactly at the given path."""
        path = self.tmp / "sub" / "whatever.civ5proj"
        path.parent.mkdir()
        self.project.write_civ5proj(path)
        self.assertTrue(path.is_file())
        self.assertTrue(path.with_suffix(".civ5sln").is_file())
        self.assertEqual(default_civ5proj_path(self.project, self.tmp), self.tmp / "Test Mod.civ5proj")

    def test_cross_conversion(self):
        """.modinfo -> .civ5proj -> .modinfo gives the same bytes."""
        text, _ = modinfo_text(self.project, self.tmp)
        mi = self.tmp / "m.modinfo"
        mi.write_text(text, encoding="utf-8")
        proj = self.tmp / "m.civ5proj"
        read_modinfo(mi).write_civ5proj(proj, create_solution=False)
        self.assertEqual(modinfo_text(read_civ5proj(proj), self.tmp)[0], text)

    def test_reads_sections_at_the_project_root(self):
        """Mod sections at the project root and lower-case booleans are read too."""
        ET.register_namespace("", NS)
        root = ET.fromstring(civ5proj_text(self.project))
        props = root.find(Q("PropertyGroup"))
        for tag in ("ModReferences", "ModDependencies", "ModBlockers", "ModActions", "ModContent"):
            section = props.find(Q(tag))
            props.remove(section)
            root.append(section)
        for flag in root.iter(Q("ImportIntoVFS")):
            flag.text = flag.text.lower()
        path = self.tmp / "legacy.civ5proj"
        ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
        p = read_civ5proj(path)
        self.assertEqual(compare_projects(self.project, p), [])

    def test_namespaceless_content(self):
        """Squads' <Content xmlns=""> entry points (the 2026-03 upstream fix)."""
        text = civ5proj_text(self.project).replace("      <Content>", '      <Content xmlns="">')
        path = self.tmp / "squads.civ5proj"
        path.write_text(text, encoding="utf-8")
        self.assertEqual(len(read_civ5proj(path).entry_points), 2)

    def test_cp139_project(self):
        p = read_civ5proj(DATA / "Community Patch.civ5proj")
        self.assertEqual(p.name, "(1) Community Patch")
        self.assertEqual(p.project_guid.lower(), "{0d66d522-b624-4bc5-acfe-15a0c5b729f4}")
        self.assertTrue(p.files and p.actions and p.dependencies)
        mi = read_modinfo(DATA / "(1) Community Patch (v 139).modinfo")
        diffs = [d for d in compare_projects(p, mi) if not d.startswith("files: md5")]
        self.assertEqual(diffs, [])

    def test_base_name(self):
        for name, base in [("(1) Community Patch", "Community Patch"), ("(4a) Squads for VP", "Squads for VP"),
                           ("Plain", "Plain"), ("(odd", "(odd")]:
            self.assertEqual(ModProject(name=name).base_name, base)


if __name__ == "__main__":
    unittest.main()
