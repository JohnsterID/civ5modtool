""".modinfo reader and writer.

The writer produces the same bytes as Vox Populi's scripts/generate_modinfo.py
(style "vp": LF, newline at the end; checked against all six VP projects by
tests/test_vp_repo.py) or as ModBuddy's own build (style "modbuddy": CRLF, no
newline at the end; checked against a ModBuddy-built CP v139 file). Both: UTF-8
with BOM, two-space indent, "/" in file paths, an MD5 for every file, actions
grouped by set in first-use order.
"""
from pathlib import Path, PureWindowsPath
from typing import List, Tuple
import xml.etree.ElementTree as ET

from .models import Action, Association, EntryPoint, FileEntry, ModProject
from .xmltext import escape_xml, md5_of, mod_file_path, parse_bool, write_text


def _text(elem, default: str = "") -> str:
    return elem.text if elem is not None and elem.text is not None else default


def _assoc_from_attrs(elem) -> Association:
    return Association(type=elem.tag, name=elem.get("title", ""), id=elem.get("id", ""),
                       min_version=elem.get("minversion", "0"), max_version=elem.get("maxversion", "999"))


def read_modinfo(path: Path) -> ModProject:
    root = ET.parse(str(path)).getroot()
    if root.tag != "Mod":
        raise ValueError(f"{path}: root element is <{root.tag}>, not <Mod>")
    props = root.find("Properties")
    if props is None:
        props = ET.Element("Properties")

    def prop(tag, default=""):
        return _text(props.find(tag), default)

    def flag(tag, default):
        return parse_bool(_text(props.find(tag), None), default)

    p = ModProject(name=prop("Name"), mod_guid=root.get("id", ""), version=root.get("version", "1"))
    p.teaser = prop("Teaser")
    p.description = prop("Description")
    p.authors = prop("Authors")
    p.special_thanks = prop("SpecialThanks").strip()
    p.homepage = prop("Homepage").strip()
    p.hide_setup_game = flag("HideSetupGame", False)
    p.affects_saves = flag("AffectsSavedGames", True)
    p.min_save_version = prop("MinCompatibleSaveVersion", "0") or "0"
    p.supports_singleplayer = flag("SupportsSinglePlayer", True)
    p.supports_multiplayer = flag("SupportsMultiplayer", True)
    p.supports_hotseat = flag("SupportsHotSeat", False)
    p.supports_mac = flag("SupportsMac", True)
    p.reload_audio = flag("ReloadAudioSystem", False)
    p.reload_landmark = flag("ReloadLandmarkSystem", False)
    p.reload_strategic_view = flag("ReloadStrategicViewSystem", False)
    p.reload_unit = flag("ReloadUnitSystem", False)

    for section, target in (("Dependencies", p.dependencies), ("References", p.references),
                            ("Blocks", p.blockers)):
        sec = root.find(section)
        for child in (sec if sec is not None else []):
            target.append(_assoc_from_attrs(child))

    files = root.find("Files")
    for f in (files if files is not None else []):
        if f.tag != "File":
            continue
        # the game (Modding::PackageManager::LoadModInfo) treats a missing import as 1
        p.files.append(FileEntry(path=_text(f).strip().replace("/", "\\"),
                                 import_to_vfs=parse_bool(f.get("import"), True),
                                 md5=(f.get("md5") or "").upper()))

    actions = root.find("Actions")
    for action_set in (actions if actions is not None else []):
        for action in action_set:
            p.actions.append(Action(action_set=action_set.tag, action_type=action.tag,
                                    filename=_text(action).strip()))

    eps = root.find("EntryPoints")
    for ep in (eps if eps is not None else []):
        p.entry_points.append(EntryPoint(type=ep.get("type", ""), file=ep.get("file", ""),
                                         name=_text(ep.find("Name")), description=_text(ep.find("Description"))))
    return p


def _assoc_line(a: Association, with_title: bool) -> str:
    tag = a.type if a.type in ("Game", "Dlc", "Mod") else "Mod"
    if tag == "Game":
        return f'    <Game minversion="{a.min_version}" maxversion="{a.max_version}" />'
    line = f'    <{tag} id="{escape_xml(a.id)}" minversion="{a.min_version}" maxversion="{a.max_version}"'
    if tag == "Mod" and with_title:
        line += f' title="{escape_xml(a.name)}"'
    return line + " />"


def _section(lines: List[str], tag: str, assocs: List[Association], allowed) -> None:
    items = [a for a in assocs if a.type in allowed or (a.type not in ("Game", "Dlc", "Mod") and "Mod" in allowed)]
    if not items:
        lines.append(f"  <{tag} />")
        return
    lines.append(f"  <{tag}>")
    lines.extend(_assoc_line(a, True) for a in items)
    lines.append(f"  </{tag}>")


STYLES = {"vp": ("\n", True), "modbuddy": ("\r\n", False)}  # newline, newline at the end


def modinfo_text(p: ModProject, mod_dir: Path, final_newline: bool = True) -> Tuple[str, List[str]]:
    """The .modinfo text (with "\\n" newlines) and the files that were not found
    under `mod_dir`. A missing file keeps the MD5 it was read with, if any, and
    is left out otherwise (as ModBuddy and generate_modinfo.py do)."""
    b = lambda v: "1" if v else "0"  # noqa: E731
    lines = ['<?xml version="1.0" encoding="utf-8"?>',
             f'<Mod id="{escape_xml(p.mod_guid)}" version="{escape_xml(p.version)}">',
             "  <Properties>",
             f"    <Name>{escape_xml(p.name)}</Name>",
             f"    <Teaser>{escape_xml(p.teaser)}</Teaser>",
             f"    <Description>{escape_xml(p.description)}</Description>",
             f"    <Authors>{escape_xml(p.authors)}</Authors>"]
    if p.special_thanks.strip():
        lines.append(f"    <SpecialThanks>{escape_xml(p.special_thanks.strip())}</SpecialThanks>")
    lines.append(f"    <HideSetupGame>{b(p.hide_setup_game)}</HideSetupGame>")
    if p.homepage.strip():
        lines.append(f"    <Homepage>{escape_xml(p.homepage.strip())}</Homepage>")
    lines.append(f"    <AffectsSavedGames>{b(p.affects_saves)}</AffectsSavedGames>")
    if p.min_compatible_save_version != "0":
        lines.append(f"    <MinCompatibleSaveVersion>{escape_xml(p.min_compatible_save_version)}</MinCompatibleSaveVersion>")
    lines += [f"    <SupportsSinglePlayer>{b(p.supports_singleplayer)}</SupportsSinglePlayer>",
              f"    <SupportsMultiplayer>{b(p.supports_multiplayer)}</SupportsMultiplayer>",
              f"    <SupportsHotSeat>{b(p.supports_hotseat)}</SupportsHotSeat>",
              f"    <SupportsMac>{b(p.supports_mac)}</SupportsMac>",
              f"    <ReloadAudioSystem>{b(p.reload_audio)}</ReloadAudioSystem>",
              f"    <ReloadLandmarkSystem>{b(p.reload_landmark)}</ReloadLandmarkSystem>",
              f"    <ReloadStrategicViewSystem>{b(p.reload_strategic_view)}</ReloadStrategicViewSystem>",
              f"    <ReloadUnitSystem>{b(p.reload_unit)}</ReloadUnitSystem>",
              "  </Properties>"]
    _section(lines, "Dependencies", p.dependencies, ("Game", "Dlc", "Mod"))
    _section(lines, "References", p.references, ("Dlc", "Mod"))
    _section(lines, "Blocks", p.blockers, ("Dlc", "Mod"))

    missing = []
    lines.append("  <Files>")
    for f in p.files:
        disk = mod_file_path(mod_dir, f.path)
        if disk.is_file():
            md5 = md5_of(disk)
        else:
            missing.append(str(disk))
            if not f.md5:
                continue
            md5 = f.md5
        game_path = str(PureWindowsPath(f.path)).replace("\\", "/")
        lines.append(f'    <File md5="{md5}" import="{b(f.import_to_vfs)}">{escape_xml(game_path)}</File>')
    lines.append("  </Files>")

    if p.actions:
        lines.append("  <Actions>")
        order = []
        for a in p.actions:
            if a.action_set not in order:
                order.append(a.action_set)
        for action_set in order:
            lines.append(f"    <{action_set}>")
            for a in p.actions:
                if a.action_set == action_set:
                    lines.append(f"      <{a.action_type}>{escape_xml(a.filename)}</{a.action_type}>")
            lines.append(f"    </{action_set}>")
        lines.append("  </Actions>")

    if p.entry_points:
        lines.append("  <EntryPoints>")
        for ep in p.entry_points:
            lines += [f'    <EntryPoint type="{escape_xml(ep.type)}" file="{escape_xml(ep.file.replace(chr(92), "/"))}">',
                      f"      <Name>{escape_xml(ep.name)}</Name>",
                      f"      <Description>{escape_xml(ep.description)}</Description>",
                      "    </EntryPoint>"]
        lines.append("  </EntryPoints>")

    lines += ["</Mod>", ""] if final_newline else ["</Mod>"]
    return "\n".join(lines), missing


def write_modinfo(p: ModProject, output_path: Path, mod_dir: Path, style: str = "vp") -> List[str]:
    newline, final_newline = STYLES[style]
    text, missing = modinfo_text(p, mod_dir, final_newline)
    write_text(output_path, text, newline)
    return missing
