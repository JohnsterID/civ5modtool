"""Tests for solution file handling."""
import unittest
from pathlib import Path
import tempfile
import shutil
from modtools.core.solution import ModSolution, ProjectReference

class TestModSolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Get paths to test data
        cls.test_data = Path(__file__).parent / "data"
        cls.sln_path = cls.test_data / "Community Patch.civ5sln"
        cls.proj_path = cls.test_data / "Community Patch.civ5proj"
        
        # Create temp directory for output files
        cls.temp_dir = Path(tempfile.mkdtemp())

    @classmethod
    def tearDownClass(cls):
        # Clean up temp directory
        shutil.rmtree(cls.temp_dir)

    def test_load_solution(self):
        """Test loading a .civ5sln file."""
        solution = ModSolution.from_sln(self.sln_path)
        
        # Check basic properties
        self.assertEqual(solution.name, "Community Patch")
        
        # Check project references
        self.assertEqual(len(solution.projects), 1)
        proj = solution.projects[0]
        self.assertEqual(proj.name, "Community Patch")
        self.assertEqual(proj.path, "Community Patch.civ5proj")
        self.assertEqual(proj.guid.lower(), "{0d66d522-b624-4bc5-acfe-15a0c5b729f4}")

    def test_create_solution(self):
        """Test creating a new solution for a project."""
        project_path = Path("test_project.civ5proj")
        project_name = "Test Project"
        
        solution = ModSolution.create_for_project(project_path, project_name)
        
        # Check properties
        self.assertEqual(solution.name, project_name)
        self.assertEqual(solution.configuration, "Default")
        self.assertTrue(solution.guid)
        
        # Check project reference
        self.assertEqual(len(solution.projects), 1)
        self.assertEqual(solution.projects[0].path, str(project_path))
        self.assertEqual(solution.projects[0].name, project_name)

    def test_solution_roundtrip(self):
        """Test loading and saving a .civ5sln file preserves data."""
        # Load original
        original = ModSolution.from_sln(self.sln_path)
        
        # Save and reload
        temp_path = self.temp_dir / "test_roundtrip.civ5sln"
        original.write(temp_path)
        reloaded = ModSolution.from_sln(temp_path)
        
        # Compare properties
        self.assertEqual(original.name, reloaded.name)
        
        # Compare projects
        self.assertEqual(len(original.projects), len(reloaded.projects))
        for orig_proj, new_proj in zip(original.projects, reloaded.projects):
            self.assertEqual(orig_proj.path, new_proj.path)
            self.assertEqual(orig_proj.name, new_proj.name)
            self.assertEqual(orig_proj.guid.lower(), new_proj.guid.lower())

    def test_path_normalization(self):
        """Test path normalization in solution files."""
        solution = ModSolution("Test Solution")
        
        # Add projects with different path styles
        solution.projects.extend([
            ProjectReference(path="test/unix/style.civ5proj", name="Unix", guid="{123}"),
            ProjectReference(path="test\\windows\\style.civ5proj", name="Windows", guid="{456}"),
            ProjectReference(path="mixed/path\\style.civ5proj", name="Mixed", guid="{789}")
        ])
        
        # Save and reload
        temp_path = self.temp_dir / "path_test.civ5sln"
        solution.write(temp_path)
        reloaded = ModSolution.from_sln(temp_path)
        
        # Check all paths use Windows style
        for proj in reloaded.projects:
            self.assertNotIn("/", proj.path, f"Unix-style path found: {proj.path}")
            if "\\" in proj.path:  # Only check Windows paths
                self.assertTrue(proj.path.replace("\\", "/").count("/") == proj.path.count("\\"),
                              f"Mixed path separators found: {proj.path}")

    def test_solution_update(self):
        """Test updating an existing solution with a new project."""
        # Create initial solution
        solution = ModSolution("Test Solution")
        solution.projects.append(ProjectReference(
            path="existing.civ5proj",
            name="Existing Project",
            guid="{123}"
        ))
        
        # Save solution
        temp_path = self.temp_dir / "update_test.civ5sln"
        solution.write(temp_path)
        
        # Load and update
        updated = ModSolution.from_sln(temp_path)
        updated.projects.append(ProjectReference(
            path="new.civ5proj",
            name="New Project",
            guid="{456}"
        ))
        
        # Save and reload
        updated.write(temp_path)
        final = ModSolution.from_sln(temp_path)
        
        # Check both projects are present
        self.assertEqual(len(final.projects), 2)
        self.assertTrue(any(p.name == "Existing Project" for p in final.projects))
        self.assertTrue(any(p.name == "New Project" for p in final.projects))

if __name__ == '__main__':
    unittest.main()