"""Data model shared by the .modinfo, .civ5proj and .civ5sln readers and writers.

One ModProject holds everything either format carries. Paths are kept exactly
as the source file wrote them (ModBuddy mixes "/" and "\\" in action and entry
point file names); the writers convert where the target format requires it.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import uuid


@dataclass
class Association:
    """A dependency, reference or blocker: Game, Dlc or Mod."""
    type: str = "Mod"
    name: str = ""
    id: str = ""
    min_version: str = "0"
    max_version: str = "999"


@dataclass
class FileEntry:
    """A file of the mod. `path` is relative to the mod folder."""
    path: str
    import_to_vfs: bool = False
    subtype: str = "Lua"  # .civ5proj <SubType>; ModBuddy writes "Lua" for every file type
    md5: str = ""         # as read from a .modinfo; the writers always hash the file on disk

    @property
    def type(self) -> str:  # alias of subtype
        return self.subtype


@dataclass
class Action:
    """One action, e.g. OnModActivated / UpdateDatabase / Database Changes/Foo.sql."""
    action_set: str
    action_type: str
    filename: str


@dataclass
class EntryPoint:
    """One entry point, e.g. InGameUIAddin with its file."""
    type: str
    file: str
    name: str = ""
    description: str = ""


def new_mod_guid() -> str:
    """A new mod id in ModBuddy's style: lower case, no braces."""
    return str(uuid.uuid4())


def project_guid_for(mod_guid: str) -> str:
    """A stable ModBuddy ProjectGuid for a mod id, so converting the same .modinfo
    twice gives the same .civ5proj and .civ5sln."""
    return "{%s}" % uuid.uuid5(uuid.NAMESPACE_URL, "civ5modtool:" + mod_guid.strip("{}").lower())


@dataclass
class ModProject:
    """A complete mod. Defaults are what ModBuddy (and upstream VP's
    scripts/generate_modinfo.py) assume when a .civ5proj omits an element."""
    name: str
    mod_guid: str = field(default_factory=new_mod_guid)
    version: str = "1"
    project_guid: str = ""
    stability: str = "Stable"
    teaser: str = ""
    description: str = ""
    authors: str = ""
    special_thanks: str = ""
    homepage: str = ""
    categories: str = ""
    assembly_name: str = ""
    root_namespace: str = ""

    hide_setup_game: bool = False
    affects_saves: bool = True
    min_save_version: str = "0"
    supports_singleplayer: bool = True
    supports_multiplayer: bool = True
    supports_hotseat: bool = False
    supports_mac: bool = True
    reload_audio: bool = False
    reload_landmark: bool = False
    reload_strategic_view: bool = False
    reload_unit: bool = False

    dependencies: List[Association] = field(default_factory=list)
    references: List[Association] = field(default_factory=list)
    blockers: List[Association] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    entry_points: List[EntryPoint] = field(default_factory=list)
    files: List[FileEntry] = field(default_factory=list)
    folders: List[str] = field(default_factory=list)  # .civ5proj <Folder Include>; derived from files if empty

    @property
    def min_compatible_save_version(self) -> str:
        return self.min_save_version or "0"

    @property
    def base_name(self) -> str:
        """The name without a leading "(1) " / "(4a) " load-order prefix, as ModBuddy
        names the .civ5proj/.civ5sln ("(1) Community Patch" -> "Community Patch")."""
        name = self.name.strip()
        if name.startswith("(") and ") " in name:
            name = name.split(") ", 1)[1]
        return name or "Mod"

    def modinfo_filename(self) -> str:
        """ModBuddy's .modinfo name: "<Name> (v <version>).modinfo"."""
        return f"{self.name} (v {self.version}).modinfo"

    def ensure_project_guid(self) -> str:
        if not self.project_guid:
            self.project_guid = project_guid_for(self.mod_guid)
        return self.project_guid

    # convenience API ----------------------------------------------------------

    @classmethod
    def from_modinfo(cls, path: Path) -> "ModProject":
        from .modinfo import read_modinfo
        return read_modinfo(Path(path))

    @classmethod
    def from_civ5proj(cls, path: Path) -> "ModProject":
        from .civ5proj import read_civ5proj
        return read_civ5proj(Path(path))

    def write_modinfo(self, output_path: Path, base_path: Optional[Path] = None, style: str = "vp"):
        """Write a .modinfo; files are hashed under `base_path` (default: the
        output's folder). style "vp" (LF, like VP's generate_modinfo.py) or
        "modbuddy" (CRLF, like ModBuddy). Returns the files that could not be hashed."""
        from .modinfo import write_modinfo
        output_path = Path(output_path)
        return write_modinfo(self, output_path, Path(base_path) if base_path else output_path.parent, style)

    def write_civ5proj(self, output_path: Path, create_solution: bool = True, newline: str = "\r\n") -> Path:
        """Write a .civ5proj exactly at `output_path`, and create or update the
        .civ5sln of the same name next to it."""
        from .civ5proj import write_civ5proj
        from .solution import add_project_to_solution
        output_path = Path(output_path)
        write_civ5proj(self, output_path, newline)
        if create_solution:
            add_project_to_solution(output_path.with_suffix(".civ5sln"), output_path, self)
        return output_path
