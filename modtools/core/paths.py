"""Path handling utilities for Civilization V mod files."""
import os
import re
from pathlib import Path

def normalize_game_path(path: str) -> str:
    """
    Convert any path to Windows-style for game files.
    All paths in .modinfo and .civ5proj should use Windows-style backslashes.
    """
    # First normalize according to system conventions
    normalized = os.path.normpath(str(path))
    # Then convert to Windows style
    return normalized.replace('/', '\\')

def normalize_system_path(base_path: str, game_path: str) -> str:
    """
    Convert a game path to a proper system path for file operations.
    
    Args:
        base_path: The base directory path (absolute system path)
        game_path: The game file path (Windows-style relative path)
    Returns:
        Absolute system path using system-appropriate separators
    """
    # Convert Windows path to system path
    sys_path = game_path.replace('\\', os.path.sep)
    # Join with base path and normalize
    return os.path.normpath(os.path.join(str(base_path), sys_path))

def paths_equal(path1: str, path2: str) -> bool:
    """
    Compare paths ignoring separator style and normalization.
    Both forward slashes and backslashes are treated as equivalent.
    Handles ./ and ../ normalization.
    """
    def normalize(p: str) -> tuple[str, ...]:
        # Convert to forward slashes and normalize
        p = p.replace('\\', '/')
        # Split into components
        parts = []
        for part in p.split('/'):
            if part == '.' or not part:
                continue
            elif part == '..':
                if parts:
                    parts.pop()
            else:
                parts.append(part.lower())  # Case-insensitive comparison
        # Return as tuple for immutable comparison
        return tuple(parts)

    def has_parent_refs(p: str) -> bool:
        """Check if path contains parent directory references."""
        return '..' in p.replace('\\', '/').split('/')

    # Get normalized path components
    parts1 = normalize(path1)
    parts2 = normalize(path2)

    # If paths are equal after normalization but one has parent refs and the other doesn't,
    # consider them different (e.g., "a/b/../c" vs "a/c")
    if parts1 == parts2 and has_parent_refs(path1) != has_parent_refs(path2):
        return False

    # Otherwise compare normalized paths
    return parts1 == parts2

def list_mod_files(directory: Path, relative_to: Path = None) -> list[str]:
    """
    List all files in a mod directory, returning Windows-style relative paths.
    
    Args:
        directory: Directory to scan for files
        relative_to: Base directory for relative paths (defaults to directory)
    Returns:
        List of Windows-style paths relative to relative_to
    """
    if relative_to is None:
        relative_to = directory

    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            abs_path = Path(root) / filename
            rel_path = abs_path.relative_to(relative_to)
            files.append(normalize_game_path(str(rel_path)))
    
    return sorted(files)