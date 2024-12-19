"""Tests for path handling utilities."""
import unittest
import os
from pathlib import Path
import tempfile
import shutil
from ..core.paths import (
    normalize_game_path,
    normalize_system_path,
    paths_equal,
    list_mod_files
)

class TestPaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create temp directory for test files
        cls.temp_dir = Path(tempfile.mkdtemp())
        
        # Create some test files and directories
        (cls.temp_dir / "Assets/UI").mkdir(parents=True)
        (cls.temp_dir / "Assets/UI/test.dds").write_text("test")
        (cls.temp_dir / "Database Changes/SQL").mkdir(parents=True)
        (cls.temp_dir / "Database Changes/SQL/test.sql").write_text("test")

    @classmethod
    def tearDownClass(cls):
        # Clean up temp directory
        shutil.rmtree(cls.temp_dir)

    def test_normalize_game_path(self):
        """Test path normalization to Windows style."""
        test_cases = [
            # Basic paths
            ("Assets/UI/test.dds", "Assets\\UI\\test.dds"),
            ("Assets\\UI\\test.dds", "Assets\\UI\\test.dds"),
            ("Assets/UI\\test.dds", "Assets\\UI\\test.dds"),
            
            # Paths with spaces
            ("Assets/Great Works/test.dds", "Assets\\Great Works\\test.dds"),
            ("Assets\\Great Works\\test.dds", "Assets\\Great Works\\test.dds"),
            
            # Paths with dots
            ("Assets/UI/test.1.dds", "Assets\\UI\\test.1.dds"),
            ("./Assets/UI/test.dds", "Assets\\UI\\test.dds"),
            ("../Assets/UI/test.dds", "..\\Assets\\UI\\test.dds"),
            
            # Root paths
            ("/Assets/UI/test.dds", "\\Assets\\UI\\test.dds"),
            ("\\Assets\\UI\\test.dds", "\\Assets\\UI\\test.dds"),
            
            # Empty or single component paths
            ("", "."),
            ("test.dds", "test.dds"),
            ("./test.dds", "test.dds"),
        ]
        
        for input_path, expected in test_cases:
            with self.subTest(input_path=input_path):
                result = normalize_game_path(input_path)
                self.assertEqual(result, expected)

    def test_normalize_system_path(self):
        """Test conversion of game paths to system paths."""
        base = self.temp_dir
        test_cases = [
            # Basic paths
            ("Assets\\UI\\test.dds", str(base / "Assets/UI/test.dds")),
            ("Assets/UI/test.dds", str(base / "Assets/UI/test.dds")),
            
            # Paths with spaces
            ("Assets\\Great Works\\test.dds", str(base / "Assets/Great Works/test.dds")),
            
            # Simple paths
            ("test.dds", str(base / "test.dds")),
        ]
        
        for game_path, expected in test_cases:
            with self.subTest(game_path=game_path):
                result = normalize_system_path(base, game_path)
                self.assertEqual(result, os.path.normpath(expected))

    def test_paths_equal(self):
        """Test path equality comparison."""
        equal_pairs = [
            # Same paths, different separators
            ("Assets/UI/test.dds", "Assets\\UI\\test.dds"),
            ("Assets\\UI\\test.dds", "Assets\\UI\\test.dds"),
            ("Assets/UI/test.dds", "Assets/UI/test.dds"),

            # Normalized paths
            ("./Assets/UI/test.dds", "Assets\\UI\\test.dds"),
            ("Assets/./UI/test.dds", "Assets\\UI\\test.dds"),
            ("Assets/UI/./test.dds", "Assets/UI/test.dds"),

            # Paths with spaces
            ("Assets/Great Works/test.dds", "Assets\\Great Works\\test.dds"),

            # Case differences (Windows-style)
            ("Assets/UI/test.dds", "assets/ui/test.dds"),

            # Parent directory references that resolve to the same path
            ("Assets/UI/./test.dds", "Assets/UI/test.dds"),
        ]

        different_pairs = [
            # Different filenames
            ("Assets/UI/test1.dds", "Assets/UI/test2.dds"),
            
            # Different directories
            ("Assets/UI1/test.dds", "Assets/UI2/test.dds"),
            
            # Different path depth
            ("Assets/test.dds", "Assets/UI/test.dds"),
            ("Assets/UI/test.dds", "Assets/test.dds"),
            
            # Different paths with parent directory references
            ("Assets/test.dds", "Assets/UI/../Other/test.dds"),  # Different target directory
            ("Assets/UI/test.dds", "Assets/Other/../UI/test.dds"),  # Same target, different path
            ("Assets/UI/../UI/test.dds", "Assets/UI/test.dds"),  # Same target, different path
            ("Assets/UI/SubDir/../test.dds", "Assets/UI/test.dds"),  # Same target, different path
        ]
        
        # Test equal paths
        for path1, path2 in equal_pairs:
            with self.subTest(path1=path1, path2=path2):
                self.assertTrue(paths_equal(path1, path2))
                self.assertTrue(paths_equal(path2, path1))  # symmetry
        
        # Test different paths
        for path1, path2 in different_pairs:
            with self.subTest(path1=path1, path2=path2):
                self.assertFalse(paths_equal(path1, path2))
                self.assertFalse(paths_equal(path2, path1))  # symmetry

    def test_list_mod_files(self):
        """Test listing files in a mod directory."""
        # Get list of files
        files = list_mod_files(self.temp_dir)
        
        # Convert expected paths to Windows style
        expected = [
            "Assets\\UI\\test.dds",
            "Database Changes\\SQL\\test.sql"
        ]
        
        # Compare lists
        self.assertEqual(sorted(files), sorted(expected))
        
        # Test relative paths
        sub_dir = self.temp_dir / "Assets"
        files = list_mod_files(sub_dir, relative_to=self.temp_dir)
        self.assertEqual(files, ["Assets\\UI\\test.dds"])