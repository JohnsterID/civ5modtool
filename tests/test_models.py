import unittest
from pathlib import Path
import tempfile
import shutil
import xml.etree.ElementTree as ET
from modtools.core.models import ModProject, FileEntry, Association, Action, EntryPoint

class TestModProject(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Get paths to test data
        cls.test_data = Path(__file__).parent / "data"
        cls.modinfo_path = cls.test_data / "(1) Community Patch (v 139).modinfo"
        cls.civ5proj_path = cls.test_data / "Community Patch.civ5proj"
        
        # Create temp directory for output files
        cls.temp_dir = Path(tempfile.mkdtemp())

    @classmethod
    def tearDownClass(cls):
        # Clean up temp directory
        shutil.rmtree(cls.temp_dir)

    def test_load_modinfo(self):
        """Test loading a .modinfo file."""
        project = ModProject.from_modinfo(self.modinfo_path)
        
        # Check basic properties
        self.assertEqual(project.name, "(1) Community Patch")
        self.assertEqual(project.version, "139")
        self.assertTrue(project.affects_saves)
        self.assertTrue(project.supports_singleplayer)
        self.assertTrue(project.supports_multiplayer)
        self.assertTrue(project.supports_hotseat)
        self.assertTrue(project.supports_mac)

        # Check files section
        self.assertGreater(len(project.files), 0)
        for file in project.files:
            if file.import_to_vfs:
                self.assertIsNotNone(file.md5, f"File {file.path} should have MD5 hash")

        # Check dependencies
        game_deps = [d for d in project.dependencies if d.type == "Game"]
        dlc_deps = [d for d in project.dependencies if d.type == "Dlc"]
        self.assertTrue(any(d.type == "Game" for d in project.dependencies))
        self.assertTrue(any(d.type == "Dlc" for d in project.dependencies))

        # Check actions
        self.assertTrue(any(a.action_type == "UpdateDatabase" for a in project.actions))
        self.assertTrue(any(a.action_type == "SetDllPath" for a in project.actions))

    def test_load_civ5proj(self):
        """Test loading a .civ5proj file."""
        project = ModProject.from_civ5proj(self.civ5proj_path)
        
        # Check basic properties
        self.assertEqual(project.name, "(1) Community Patch")
        self.assertIsNotNone(project.project_guid)
        self.assertIsNotNone(project.mod_guid)
        self.assertEqual(project.version, "139")

        # Check dependencies
        self.assertTrue(any(d.type == "Game" for d in project.dependencies))
        self.assertTrue(any(d.type == "Dlc" for d in project.dependencies))

        # Check files
        self.assertGreater(len(project.files), 0)
        for file in project.files:
            self.assertIsInstance(file.import_to_vfs, bool)
            self.assertIsInstance(file.path, str)

        # Check actions
        self.assertTrue(any(a.action_type == "UpdateDatabase" for a in project.actions))
        self.assertTrue(any(a.action_type == "SetDllPath" for a in project.actions))

    def test_modinfo_roundtrip(self):
        """Test loading and saving a .modinfo file preserves data."""
        # Load original
        original = ModProject.from_modinfo(self.modinfo_path)
        
        # Save and reload
        temp_path = self.temp_dir / "test_roundtrip.modinfo"
        original.write_modinfo(temp_path)
        reloaded = ModProject.from_modinfo(temp_path)
        
        # Compare properties
        self.assertEqual(original.name, reloaded.name)
        self.assertEqual(original.mod_guid, reloaded.mod_guid)
        self.assertEqual(original.version, reloaded.version)
        self.assertEqual(original.teaser, reloaded.teaser)
        self.assertEqual(original.description, reloaded.description)
        self.assertEqual(original.authors, reloaded.authors)
        self.assertEqual(original.homepage, reloaded.homepage)
        
        # Compare support flags
        self.assertEqual(original.affects_saves, reloaded.affects_saves)
        self.assertEqual(original.supports_singleplayer, reloaded.supports_singleplayer)
        self.assertEqual(original.supports_multiplayer, reloaded.supports_multiplayer)
        self.assertEqual(original.supports_hotseat, reloaded.supports_hotseat)
        self.assertEqual(original.supports_mac, reloaded.supports_mac)
        
        # Compare files
        self.assertEqual(len(original.files), len(reloaded.files))
        for orig_file, new_file in zip(
            sorted(original.files, key=lambda x: x.path),
            sorted(reloaded.files, key=lambda x: x.path)
        ):
            self.assertEqual(orig_file.path, new_file.path)
            self.assertEqual(orig_file.import_to_vfs, new_file.import_to_vfs)
            # Don't compare MD5s in roundtrip test as they depend on file existence

        # Compare dependencies
        self.assertEqual(len(original.dependencies), len(reloaded.dependencies))
        for orig_dep, new_dep in zip(
            sorted(original.dependencies, key=lambda x: (x.type, x.id)),
            sorted(reloaded.dependencies, key=lambda x: (x.type, x.id))
        ):
            self.assertEqual(orig_dep.type, new_dep.type)
            self.assertEqual(orig_dep.id, new_dep.id)
            self.assertEqual(orig_dep.min_version, new_dep.min_version)
            self.assertEqual(orig_dep.max_version, new_dep.max_version)

        # Compare actions
        self.assertEqual(len(original.actions), len(reloaded.actions))
        for orig_action, new_action in zip(
            sorted(original.actions, key=lambda x: (x.action_set, x.action_type, x.filename)),
            sorted(reloaded.actions, key=lambda x: (x.action_set, x.action_type, x.filename))
        ):
            self.assertEqual(orig_action.action_set, new_action.action_set)
            self.assertEqual(orig_action.action_type, new_action.action_type)
            self.assertEqual(orig_action.filename, new_action.filename)

    def test_civ5proj_roundtrip(self):
        """Test loading and saving a .civ5proj file preserves data."""
        # Load original
        original = ModProject.from_civ5proj(self.civ5proj_path)
        
        # Save and reload
        temp_path = self.temp_dir / "test_roundtrip.civ5proj"
        original.write_civ5proj(temp_path, create_solution=False)
        reloaded = ModProject.from_civ5proj(temp_path)
        
        # Compare properties
        self.assertEqual(original.name, reloaded.name)
        self.assertEqual(original.mod_guid, reloaded.mod_guid)
        self.assertEqual(original.version, reloaded.version)
        self.assertEqual(original.teaser, reloaded.teaser)
        self.assertEqual(original.description, reloaded.description)
        self.assertEqual(original.authors, reloaded.authors)
        self.assertEqual(original.homepage, reloaded.homepage)
        
        # Compare support flags
        self.assertEqual(original.affects_saves, reloaded.affects_saves)
        self.assertEqual(original.supports_singleplayer, reloaded.supports_singleplayer)
        self.assertEqual(original.supports_multiplayer, reloaded.supports_multiplayer)
        self.assertEqual(original.supports_hotseat, reloaded.supports_hotseat)
        self.assertEqual(original.supports_mac, reloaded.supports_mac)
        
        # Compare files
        self.assertEqual(len(original.files), len(reloaded.files))
        for orig_file, new_file in zip(
            sorted(original.files, key=lambda x: x.path),
            sorted(reloaded.files, key=lambda x: x.path)
        ):
            self.assertEqual(orig_file.path, new_file.path)
            self.assertEqual(orig_file.import_to_vfs, new_file.import_to_vfs)
            self.assertEqual(orig_file.type, new_file.type)

        # Compare dependencies
        self.assertEqual(len(original.dependencies), len(reloaded.dependencies))
        for orig_dep, new_dep in zip(
            sorted(original.dependencies, key=lambda x: (x.type, x.id)),
            sorted(reloaded.dependencies, key=lambda x: (x.type, x.id))
        ):
            self.assertEqual(orig_dep.type, new_dep.type)
            self.assertEqual(orig_dep.id, new_dep.id)
            self.assertEqual(orig_dep.min_version, new_dep.min_version)
            self.assertEqual(orig_dep.max_version, new_dep.max_version)

        # Compare actions
        self.assertEqual(len(original.actions), len(reloaded.actions))
        for orig_action, new_action in zip(
            sorted(original.actions, key=lambda x: (x.action_set, x.action_type, x.filename)),
            sorted(reloaded.actions, key=lambda x: (x.action_set, x.action_type, x.filename))
        ):
            self.assertEqual(orig_action.action_set, new_action.action_set)
            self.assertEqual(orig_action.action_type, new_action.action_type)
            self.assertEqual(orig_action.filename, new_action.filename)

    def test_cross_conversion(self):
        """Test converting between .modinfo and .civ5proj preserves essential data."""
        # Load from modinfo
        from_modinfo = ModProject.from_modinfo(self.modinfo_path)
        
        # Save as civ5proj and reload
        temp_proj_path = self.temp_dir / "cross_test.civ5proj"
        from_modinfo.write_civ5proj(temp_proj_path, create_solution=False)
        from_proj = ModProject.from_civ5proj(temp_proj_path)
        
        # Compare essential properties
        self.assertEqual(from_modinfo.name, from_proj.name)
        self.assertEqual(from_modinfo.mod_guid, from_proj.mod_guid)
        self.assertEqual(from_modinfo.version, from_proj.version)
        self.assertEqual(from_modinfo.teaser, from_proj.teaser)
        self.assertEqual(from_modinfo.description, from_proj.description)
        self.assertEqual(from_modinfo.authors, from_proj.authors)
        
        # Compare support flags
        self.assertEqual(from_modinfo.affects_saves, from_proj.affects_saves)
        self.assertEqual(from_modinfo.supports_singleplayer, from_proj.supports_singleplayer)
        self.assertEqual(from_modinfo.supports_multiplayer, from_proj.supports_multiplayer)
        self.assertEqual(from_modinfo.supports_hotseat, from_proj.supports_hotseat)
        self.assertEqual(from_modinfo.supports_mac, from_proj.supports_mac)
        
        # Compare files (paths should match)
        modinfo_files = {f.path for f in from_modinfo.files}
        proj_files = {f.path for f in from_proj.files}
        self.assertEqual(modinfo_files, proj_files)
        
        # Compare dependencies
        self.assertEqual(
            [(d.type, d.id) for d in from_modinfo.dependencies],
            [(d.type, d.id) for d in from_proj.dependencies]
        )
        
        # Compare actions
        self.assertEqual(
            [(a.action_set, a.action_type, a.filename) for a in from_modinfo.actions],
            [(a.action_set, a.action_type, a.filename) for a in from_proj.actions]
        )

    def test_path_normalization(self):
        """Test path normalization between Windows and Unix style."""
        project = ModProject.from_civ5proj(self.civ5proj_path)
        
        # Save with different path styles
        temp_path = self.temp_dir / "path_test.civ5proj"
        
        # Add test files with different path styles
        project.files.extend([
            FileEntry(path="test/unix/style.xml", import_to_vfs=True),
            FileEntry(path="test\\windows\\style.xml", import_to_vfs=True),
            FileEntry(path="mixed/path\\style.xml", import_to_vfs=True)
        ])
        
        # Save and reload
        project.write_civ5proj(temp_path, create_solution=False)
        reloaded = ModProject.from_civ5proj(temp_path)
        
        # Check all paths use Windows style
        for file in reloaded.files:
            self.assertNotIn("/", file.path, f"Unix-style path found: {file.path}")
            if "\\" in file.path:  # Only check Windows paths
                self.assertTrue(file.path.replace("\\", "/").count("/") == file.path.count("\\"),
                              f"Mixed path separators found: {file.path}")

if __name__ == '__main__':
    unittest.main()