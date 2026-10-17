"""Checks for .modinfo, .civ5proj and .civ5sln files.

Errors are things that break the mod or its build; warnings are things that
work but are probably mistakes. What the game accepts was read from the EXE
(IDA, Linux Civ5XP with symbols; the Windows EXEs share the code):

* Modding::PackageManager::LoadModInfo records a mod only if <Mod version> is
  an integer >= 0. Mod/Dlc min/maxversion are read as integers, Game ones as
  text. A <File> without import="" counts as import="1".
* Booleans (FXmlNVPair::GetVal(bool&)): t/T... true, f/F... false, else a number.
* MD5s are compared only by Modding::Installer::CanInstallMod, i.e. when a
  packaged .civ5mod is installed (a mismatch aborts with error 16). Mods in the
  MODS folder load without any MD5 check, so for them a stale MD5 is a warning
  (pass packaged=True / --packaged to make it an error).
* CvModdingFrameworkAppSide::Initialize registers exactly four action types:
  UpdateDatabase, UpdateUserData, ExecuteScript, SetDllPath; the action sets the
  EXE uses are OnModActivated, OnGetDLLPath and OnCreateModUserData.
* Entry point types looked up: InGameUIAddin, DiplomacyUIAddin, CityViewUIAddin,
  Custom (game UI Lua), Map and MapScript (EXE SQL). Map and MapScript entry
  points are joined to the file list with ModEntryPoints.File = ModFiles.Path,
  an exact string match: the file attribute must equal the <File> text,
  same slashes and case.
* Civ5XP (Linux) lower-cases every path below MODS when it opens a file
  (DOS2MacPath), so there every name must be lower case on disk
  (validate_civ5xp, civ5xp=True / --civ5xp).
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import re
import xml.etree.ElementTree as ET

from .civ5proj import NS, _child, _children, main_property_group, read_civ5proj
from .civ5xp import case_problems
from .modinfo import read_modinfo
from .solution import ModSolution
from .xmltext import md5_of, mod_file_path

GUID = re.compile(r"^\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?$")
MOD_SECTIONS = ("ModReferences", "ModDependencies", "ModBlockers", "ModActions", "ModContent")
ACTION_TYPES = ("UpdateDatabase", "UpdateUserData", "ExecuteScript", "SetDllPath")
ACTION_SETS = ("OnModActivated", "OnGetDLLPath", "OnCreateModUserData")
ENTRY_POINT_TYPES = ("InGameUIAddin", "DiplomacyUIAddin", "CityViewUIAddin", "Custom", "Map", "MapScript")
EXACT_PATH_ENTRY_POINTS = ("Map", "MapScript")
BOOL_PROPS = ("HideSetupGame", "AffectsSavedGames", "SupportsSinglePlayer", "SupportsMultiplayer",
              "SupportsHotSeat", "SupportsMac", "ReloadAudioSystem", "ReloadLandmarkSystem",
              "ReloadStrategicViewSystem", "ReloadUnitSystem")


@dataclass
class Issue:
    severity: str  # "error" | "warning"
    message: str

    def __str__(self):
        return f"{self.severity}: {self.message}"


def _key(path: str) -> str:
    return path.replace("\\", "/").strip().lower()


def _is_bool(text) -> bool:
    text = (text or "").strip()
    return bool(text) and (text[0] in "tTfF" or text.lstrip("-").isdigit())


def _common(p, mod_dir: Path, issues: List[Issue], hash_files: bool, packaged: bool = False) -> None:
    """Checks shared by both formats, on the parsed project."""
    if not p.name:
        issues.append(Issue("error", "the mod has no Name"))
    if not GUID.match(p.mod_guid or ""):
        issues.append(Issue("error", f"mod id {p.mod_guid!r} is not a GUID"))
    if not (p.version or "").isdigit():
        issues.append(Issue("error", f"version {p.version!r} is not a whole number"))
    if not (p.min_save_version or "0").isdigit():
        issues.append(Issue("warning", f"MinCompatibleSaveVersion {p.min_save_version!r} is not a whole number"))
    for kind, assocs in (("dependency", p.dependencies), ("reference", p.references), ("blocker", p.blockers)):
        for a in assocs:
            if a.type not in ("Game", "Dlc", "Mod"):
                issues.append(Issue("warning", f"{kind} {a.name or a.id!r} has unknown type {a.type!r}"))
            elif a.type != "Game":
                if not GUID.match(a.id or ""):
                    issues.append(Issue("warning", f"{kind} {a.name or '?'!r}: id {a.id!r} is not a GUID"))
                for v in (a.min_version, a.max_version):
                    if not v.lstrip("-").isdigit():
                        issues.append(Issue("warning", f"{kind} {a.name or a.id!r}: version {v!r} is not a whole "
                                                       "number (the game reads Mod/Dlc versions as integers)"))

    listed: Dict[str, object] = {}
    for f in p.files:
        k = _key(f.path)
        if k in listed:
            issues.append(Issue("warning", f"file listed twice: {f.path}"))
        listed[k] = f
        disk = mod_file_path(mod_dir, f.path)
        if not disk.is_file():
            issues.append(Issue("error", f"file not found: {f.path}"))
        elif hash_files:
            level = "error" if packaged else "warning"
            if not f.md5:
                issues.append(Issue(level, f"no md5 for {f.path} (run update-md5; a packaged install fails without it)"))
            elif f.md5.upper() != md5_of(disk):
                issues.append(Issue(level, f"stale md5 for {f.path} (run update-md5; a packaged install fails on it)"))

    for a in p.actions:
        if a.action_type not in ACTION_TYPES:
            issues.append(Issue("warning", f"action type {a.action_type!r} is not one the game runs ({', '.join(ACTION_TYPES)})"))
        if a.action_set not in ACTION_SETS:
            issues.append(Issue("warning", f"action set {a.action_set!r} is not one the game uses ({', '.join(ACTION_SETS)})"))
        if not a.filename:
            issues.append(Issue("error", f"action {a.action_set}/{a.action_type} has no file"))
            continue
        if _key(a.filename) not in listed:
            issues.append(Issue("warning", f"action {a.action_set}/{a.action_type} file is not in the file list: {a.filename}"))
        if not mod_file_path(mod_dir, a.filename).is_file():
            issues.append(Issue("error", f"action {a.action_set}/{a.action_type} file not found: {a.filename}"))
        if a.action_type == "UpdateDatabase" and not a.filename.lower().endswith((".sql", ".xml")):
            issues.append(Issue("warning", f"UpdateDatabase file is neither .sql nor .xml: {a.filename}"))
    for ep in p.entry_points:
        if ep.type not in ENTRY_POINT_TYPES:
            issues.append(Issue("warning", f"entry point type {ep.type!r} is not one the game looks up "
                                           f"({', '.join(ENTRY_POINT_TYPES)})"))
        if _key(ep.file) not in listed:
            issues.append(Issue("warning", f"entry point {ep.type} file is not in the file list: {ep.file}"))
        if not mod_file_path(mod_dir, ep.file).is_file():
            issues.append(Issue("error", f"entry point {ep.type} file not found: {ep.file}"))


def validate_modinfo(path: Path, packaged: bool = False) -> List[Issue]:
    issues: List[Issue] = []
    try:
        root = ET.parse(str(path)).getroot()
        p = read_modinfo(path)
    except (ET.ParseError, ValueError) as e:
        return [Issue("error", f"cannot read: {e}")]
    props = root.find("Properties")
    if props is None:
        issues.append(Issue("error", "no <Properties>"))
    else:
        for tag in BOOL_PROPS:
            node = props.find(tag)
            if node is not None and not _is_bool(node.text):
                issues.append(Issue("warning", f"<{tag}> is {node.text!r}, not a boolean (0/1 or true/false)"))
    files = root.find("Files")
    exact = set()
    for f in (files if files is not None else []):
        if f.tag == "File":
            exact.add((f.text or "").strip())
            if f.get("import") is None:
                issues.append(Issue("warning", f"{(f.text or '').strip()}: no import attribute; the game treats it as import=\"1\""))
    eps = root.find("EntryPoints")
    for ep in (eps if eps is not None else []):
        if ep.get("type") in EXACT_PATH_ENTRY_POINTS and ep.get("file") not in exact and _key(ep.get("file") or "") in {_key(x) for x in exact}:
            issues.append(Issue("error", f"{ep.get('type')} entry point file {ep.get('file')!r} differs from its <File> entry in "
                                         "slashes or case; the game matches them exactly and will not find the map"))
    _common(p, path.parent, issues, hash_files=True, packaged=packaged)
    return issues


def validate_civ5proj(path: Path) -> List[Issue]:
    issues: List[Issue] = []
    try:
        root = ET.parse(str(path)).getroot()
        p = read_civ5proj(path)
    except (ET.ParseError, ValueError) as e:
        return [Issue("error", f"cannot read: {e}")]
    props = main_property_group(root)
    for tag in MOD_SECTIONS:
        if _child(props, tag) is None and _child(root, tag) is not None:
            issues.append(Issue("error", f"<{tag}> is outside the main <PropertyGroup>; ModBuddy and "
                                         "generate_modinfo.py ignore it there"))
    for item in root.iter(f"{{{NS}}}Content"):
        flag = _child(item, "ImportIntoVFS")
        if item.get("Include") and flag is not None and flag.text not in ("True", "False"):
            issues.append(Issue("warning", f"{item.get('Include')}: ImportIntoVFS is {flag.text!r}; ModBuddy writes "
                                           "True/False and generate_modinfo.py reads anything but True as False"))
    _common(p, path.parent, issues, hash_files=False)
    if not p.project_guid:
        issues.append(Issue("warning", "no ProjectGuid"))
    for ep in _children(_child(props, "ModContent"), "Content"):
        if not (_child(ep, "Type") is not None and _child(ep, "FileName") is not None):
            issues.append(Issue("warning", "an entry point in <ModContent> has no Type or FileName and is skipped"))
    return issues


def validate_civ5sln(path: Path) -> List[Issue]:
    try:
        sln = ModSolution.from_sln(path)
    except (OSError, ValueError) as e:
        return [Issue("error", f"cannot read: {e}")]
    issues = []
    for ref in sln.projects:
        proj = path.parent / ref.path.replace("\\", "/")
        if not proj.is_file():
            issues.append(Issue("error", f"project not found: {ref.path}"))
            continue
        try:
            guid = read_civ5proj(proj).project_guid
        except (ET.ParseError, ValueError) as e:
            issues.append(Issue("error", f"{ref.path}: cannot read: {e}"))
            continue
        if guid and guid.strip("{}").lower() != ref.guid.strip("{}").lower():
            issues.append(Issue("warning", f"{ref.path}: solution GUID {ref.guid} differs from ProjectGuid {guid}"))
    return issues


def validate_civ5xp(path: Path) -> List[Issue]:
    """Civ5XP (Linux) lower-cases every path below MODS before opening it
    (see civ5xp.py), so every listed name must be lower case on disk."""
    try:
        p = read_civ5proj(path) if path.suffix.lower() == ".civ5proj" else read_modinfo(path)
    except (ET.ParseError, ValueError):
        return []  # reported by the format check
    paths = [f.path for f in p.files] + [a.filename for a in p.actions if a.filename] + [e.file for e in p.entry_points]
    issues = [Issue("error", f"Civ5XP opens {name.lower()!r} but the file is {name!r} (Linux is case sensitive; "
                             "install with civ5xp-install)")
              for name in dict.fromkeys(case_problems(path.parent, paths))]
    if path.parent.name != path.parent.name.lower():
        issues.append(Issue("warning", f"Civ5XP looks for the mod folder as {path.parent.name.lower()!r} "
                                       "(civ5xp-install copies it under that name)"))
    return issues


def validate_path(path: Path, packaged: bool = False, civ5xp: bool = False) -> List[Issue]:
    suffix = path.suffix.lower()
    if suffix == ".modinfo":
        issues = validate_modinfo(path, packaged)
    elif suffix == ".civ5proj":
        issues = validate_civ5proj(path)
    elif suffix == ".civ5sln":
        return validate_civ5sln(path)
    else:
        return [Issue("error", f"not a .modinfo, .civ5proj or .civ5sln file: {path.name}")]
    return issues + (validate_civ5xp(path) if civ5xp else [])
