"""Civ5XP: Aspyr's Linux build of Civilization V.

Civ5XP opens every file through DOS2POSIXPathW -> DOS2MacPath (IDA, Civ5XP
with symbols): "\\" becomes "/", and in a path containing
"Aspyr/Sid Meier's Civilization 5/MODS" everything after that point - the mod
folder and every file in it - is lower-cased before the file is opened
(relative paths are lower-cased entirely). Linux file names are case
sensitive, so a mod only works on Civ5XP if every name under MODS is lower
case on disk. The .modinfo itself can keep any case: the game lower-cases
what it reads.

The MODS folder is $XDG_DATA_HOME/Aspyr/Sid Meier's Civilization 5/MODS,
with $XDG_DATA_HOME defaulting to ~/.local/share (both strings are in the
binary).
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import os
import shutil

from .xmltext import disk_parts

SKIP_DIRS = {".git", ".svn", "__pycache__"}


def default_mods_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "Aspyr" / "Sid Meier's Civilization 5" / "MODS"


def case_problems(mod_dir: Path, paths: List[str]) -> List[str]:
    """Listed paths whose names on disk are not lower case (Civ5XP would not find them)."""
    problems = []
    for path in paths:
        names = disk_parts(mod_dir, path)
        if names is not None:
            on_disk = "/".join(names)
            if on_disk != on_disk.lower():
                problems.append(on_disk)
    return problems


@dataclass
class InstallReport:
    target: Path
    copied: int = 0
    collisions: Dict[str, List[str]] = field(default_factory=dict)  # lower-cased name -> source names


def install(mod_dir: Path, mods_dir: Optional[Path] = None, name: Optional[str] = None,
            replace: bool = False, dry_run: bool = False) -> InstallReport:
    """Copy a mod folder into Civ5XP's MODS folder with every name lower-cased.
    The source is not changed. Refuses if two names collide once lower-cased,
    or if the target exists (unless `replace`)."""
    mod_dir = Path(mod_dir)
    target = Path(mods_dir or default_mods_dir()) / (name or mod_dir.name).lower()
    report = InstallReport(target=target)
    plan = {}
    for root, dirs, files in os.walk(mod_dir):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            rel = (Path(root) / f).relative_to(mod_dir).as_posix()
            plan.setdefault(rel.lower(), []).append(rel)
    report.collisions = {low: srcs for low, srcs in plan.items() if len(srcs) > 1}
    if report.collisions:
        return report
    if target.exists():
        if not replace:
            raise FileExistsError(f"{target} exists (use replace=True / --replace)")
        if not dry_run:
            shutil.rmtree(target)
    for low, (src,) in sorted(plan.items()):
        if not dry_run:
            dst = target / low
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(mod_dir / src, dst)
        report.copied += 1
    return report
