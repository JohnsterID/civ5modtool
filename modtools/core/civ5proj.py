""".civ5proj (ModBuddy project) reader and writer.

Layout as ModBuddy writes it (VP's six projects are the reference): every mod
section (ModReferences, ModDependencies, ModBlockers, ModActions, ModContent)
sits inside the first <PropertyGroup>; files are <Content Include="a\\b"> items
with <SubType> and <ImportIntoVFS>True|False</ImportIntoVFS>; folders are
<Folder Include> items. The reader also accepts projects that put the mod
sections at the project root, and <Content xmlns=""> entry points.
"""
from pathlib import Path, PureWindowsPath
from typing import List, Optional
import xml.etree.ElementTree as ET

from .models import Action, Association, EntryPoint, FileEntry, ModProject
from .xmltext import escape_xml, parse_bool, write_text

NS = "http://schemas.microsoft.com/developer/msbuild/2003"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(elem, tag):
    """A child in the MSBuild namespace or in no namespace (xmlns="")."""
    if elem is None:
        return None
    found = elem.find(f"{{{NS}}}{tag}")
    return found if found is not None else elem.find(tag)


def _children(elem, tag):
    if elem is None:
        return []
    return elem.findall(f"{{{NS}}}{tag}") + elem.findall(tag)


def _text(elem, tag, default=""):
    node = _child(elem, tag)
    return node.text if node is not None and node.text is not None else default


def main_property_group(root):
    groups = _children(root, "PropertyGroup")
    for g in groups:
        if g.get("Condition") is None and (_child(g, "Name") is not None or _child(g, "Guid") is not None):
            return g
    return groups[0] if groups else None


def _section(props, root, tag):
    """A mod section from the main PropertyGroup, or from the project root
    (where some older tools wrote them)."""
    found = _child(props, tag)
    return found if found is not None else _child(root, tag)


def _associations(elem, default_type: str) -> List[Association]:
    return [Association(type=_text(a, "Type", default_type) or default_type, name=_text(a, "Name"),
                        id=_text(a, "Id"), min_version=_text(a, "MinVersion", "0") or "0",
                        max_version=_text(a, "MaxVersion", "999") or "999")
            for a in _children(elem, "Association")]


def read_civ5proj(path: Path) -> ModProject:
    root = ET.parse(str(path)).getroot()
    if _local(root.tag) != "Project":
        raise ValueError(f"{path}: root element is <{_local(root.tag)}>, not <Project>")
    props = main_property_group(root)
    if props is None:
        raise ValueError(f"{path}: no <PropertyGroup>")

    def flag(tag, default):
        node = _child(props, tag)
        return parse_bool(node.text if node is not None else None, default)

    p = ModProject(name=_text(props, "Name"), mod_guid=_text(props, "Guid"),
                   version=_text(props, "ModVersion", "1") or "1")
    p.project_guid = _text(props, "ProjectGuid")
    p.stability = _text(props, "Stability", "Stable")
    p.teaser = _text(props, "Teaser")
    p.description = _text(props, "Description")
    p.authors = _text(props, "Authors")
    p.special_thanks = _text(props, "SpecialThanks").strip()
    p.homepage = _text(props, "Homepage").strip()
    p.categories = _text(props, "Categories")
    p.assembly_name = _text(props, "AssemblyName")
    p.root_namespace = _text(props, "RootNamespace")
    p.hide_setup_game = flag("HideSetupGame", False)
    p.affects_saves = flag("AffectsSavedGames", True)
    p.min_save_version = _text(props, "MinCompatibleSaveVersion", "0") or "0"
    p.supports_singleplayer = flag("SupportsSinglePlayer", True)
    p.supports_multiplayer = flag("SupportsMultiplayer", True)
    p.supports_hotseat = flag("SupportsHotSeat", False)
    p.supports_mac = flag("SupportsMac", True)
    p.reload_audio = flag("ReloadAudioSystem", False)
    p.reload_landmark = flag("ReloadLandmarkSystem", False)
    p.reload_strategic_view = flag("ReloadStrategicViewSystem", False)
    p.reload_unit = flag("ReloadUnitSystem", False)

    p.dependencies = _associations(_section(props, root, "ModDependencies"), "Mod")
    p.references = _associations(_section(props, root, "ModReferences"), "Mod")
    p.blockers = _associations(_section(props, root, "ModBlockers"), "Mod")
    for a in _children(_section(props, root, "ModActions"), "Action"):
        p.actions.append(Action(action_set=_text(a, "Set"), action_type=_text(a, "Type"),
                                filename=_text(a, "FileName").strip()))
    for c in _children(_section(props, root, "ModContent"), "Content"):
        ep = EntryPoint(type=_text(c, "Type"), file=_text(c, "FileName").strip(),
                        name=_text(c, "Name"), description=_text(c, "Description"))
        if ep.type and ep.file:
            p.entry_points.append(ep)

    for group in _children(root, "ItemGroup"):
        for item in group:
            kind, include = _local(item.tag), item.get("Include")
            if not include:
                continue
            if kind == "Folder":
                p.folders.append(include)
            elif kind == "Content":
                p.files.append(FileEntry(path=include, subtype=_text(item, "SubType", "Lua"),
                                         import_to_vfs=parse_bool(_text(item, "ImportIntoVFS", None), False)))
    return p


def _derived_folders(p: ModProject) -> List[str]:
    folders = []
    for f in p.files:
        parts = PureWindowsPath(f.path).parts[:-1]
        for i in range(1, len(parts) + 1):
            folder = "\\".join(parts[:i])
            if folder not in folders:
                folders.append(folder)
    return folders


def _assoc_block(lines: List[str], tag: str, assocs: List[Association]) -> None:
    if not assocs:
        return
    lines.append(f"    <{tag}>")
    for a in assocs:
        lines.append("      <Association>")
        lines.append(f"        <Type>{escape_xml(a.type)}</Type>")
        lines.append(f"        <Name>{escape_xml(a.name)}</Name>" if a.name else "        <Name />")
        lines.append(f"        <Id>{escape_xml(a.id)}</Id>" if a.id else "        <Id />")
        lines.append(f"        <MinVersion>{escape_xml(a.min_version)}</MinVersion>")
        lines.append(f"        <MaxVersion>{escape_xml(a.max_version)}</MaxVersion>")
        lines.append("      </Association>")
    lines.append(f"    </{tag}>")


def civ5proj_text(p: ModProject) -> str:
    t = lambda v: "true" if v else "false"  # noqa: E731
    e = escape_xml
    base = p.assembly_name or p.base_name
    lines = ['<?xml version="1.0" encoding="utf-8"?>',
             f'<Project DefaultTargets="Deploy" ToolsVersion="4.0" xmlns="{NS}">',
             "  <PropertyGroup>",
             "    <Configuration Condition=\" '$(Configuration)' == '' \">Default</Configuration>",
             f"    <ProjectGuid>{e(p.ensure_project_guid())}</ProjectGuid>",
             f"    <Name>{e(p.name)}</Name>",
             f"    <Guid>{e(p.mod_guid)}</Guid>",
             f"    <ModVersion>{e(p.version)}</ModVersion>",
             f"    <Stability>{e(p.stability or 'Stable')}</Stability>",
             f"    <Teaser>{e(p.teaser)}</Teaser>",
             f"    <Description>{e(p.description)}</Description>",
             f"    <Authors>{e(p.authors)}</Authors>"]
    if p.special_thanks.strip():
        lines.append(f"    <SpecialThanks>{e(p.special_thanks.strip())}</SpecialThanks>")
    if p.categories:
        lines.append(f"    <Categories>{e(p.categories)}</Categories>")
    lines += [f"    <AffectsSavedGames>{t(p.affects_saves)}</AffectsSavedGames>",
              f"    <MinCompatibleSaveVersion>{e(p.min_compatible_save_version)}</MinCompatibleSaveVersion>",
              f"    <SupportsSinglePlayer>{t(p.supports_singleplayer)}</SupportsSinglePlayer>",
              f"    <SupportsMultiplayer>{t(p.supports_multiplayer)}</SupportsMultiplayer>",
              f"    <SupportsHotSeat>{t(p.supports_hotseat)}</SupportsHotSeat>",
              f"    <SupportsMac>{t(p.supports_mac)}</SupportsMac>",
              f"    <ReloadUnitSystem>{t(p.reload_unit)}</ReloadUnitSystem>",
              f"    <ReloadLandmarkSystem>{t(p.reload_landmark)}</ReloadLandmarkSystem>",
              f"    <ReloadStrategicViewSystem>{t(p.reload_strategic_view)}</ReloadStrategicViewSystem>",
              f"    <ReloadAudioSystem>{t(p.reload_audio)}</ReloadAudioSystem>",
              f"    <HideSetupGame>{t(p.hide_setup_game)}</HideSetupGame>"]
    if p.homepage.strip():
        lines.append(f"    <Homepage>{e(p.homepage.strip())}</Homepage>")
    lines += [f"    <AssemblyName>{e(base)}</AssemblyName>",
              f"    <RootNamespace>{e(p.root_namespace or base)}</RootNamespace>"]
    _assoc_block(lines, "ModReferences", p.references)
    _assoc_block(lines, "ModDependencies", p.dependencies)
    _assoc_block(lines, "ModBlockers", p.blockers)
    if p.actions:
        lines.append("    <ModActions>")
        for a in p.actions:
            lines += ["      <Action>", f"        <Set>{e(a.action_set)}</Set>",
                      f"        <Type>{e(a.action_type)}</Type>",
                      f"        <FileName>{e(a.filename)}</FileName>", "      </Action>"]
        lines.append("    </ModActions>")
    if p.entry_points:
        lines.append("    <ModContent>")
        for ep in p.entry_points:
            lines += ["      <Content>", f"        <Type>{e(ep.type)}</Type>",
                      f"        <Name>{e(ep.name)}</Name>" if ep.name else "        <Name />",
                      f"        <Description>{e(ep.description)}</Description>" if ep.description else "        <Description />",
                      f"        <FileName>{e(ep.file)}</FileName>", "      </Content>"]
        lines.append("    </ModContent>")
    lines += ["  </PropertyGroup>",
              "  <PropertyGroup Condition=\" '$(Configuration)' == 'Default' \">",
              "    <OutputPath>.</OutputPath>",
              "  </PropertyGroup>",
              "  <PropertyGroup Condition=\" '$(Configuration)' == 'Package Only' \">",
              "    <PackageMod>true</PackageMod>",
              "    <DeployMod>false</DeployMod>",
              "  </PropertyGroup>",
              "  <PropertyGroup Condition=\" '$(Configuration)' == 'Deploy Only' \">",
              "    <PackageMod>false</PackageMod>",
              "    <DeployMod>true</DeployMod>",
              "  </PropertyGroup>"]
    folders = p.folders or _derived_folders(p)
    if folders:
        lines.append("  <ItemGroup>")
        lines += [f'    <Folder Include="{e(folder)}" />' for folder in folders]
        lines.append("  </ItemGroup>")
    if p.files:
        lines.append("  <ItemGroup>")
        for f in p.files:
            lines += [f'    <Content Include="{e(str(PureWindowsPath(f.path)))}">',
                      f"      <SubType>{e(f.subtype or 'Lua')}</SubType>",
                      f"      <ImportIntoVFS>{'True' if f.import_to_vfs else 'False'}</ImportIntoVFS>",
                      "    </Content>"]
        lines.append("  </ItemGroup>")
    lines += ['  <Import Project="$(MSBuildExtensionsPath)\\Firaxis\\ModBuddy\\Civ5Mod.targets" />',
              "</Project>", ""]
    return "\n".join(lines)


def write_civ5proj(p: ModProject, output_path: Path, newline: str = "\r\n") -> None:
    write_text(output_path, civ5proj_text(p), newline)


def default_civ5proj_path(p: ModProject, folder: Path, name: Optional[str] = None) -> Path:
    """ModBuddy's project file name: the mod name without its "(N) " prefix."""
    return folder / f"{name or p.base_name}.civ5proj"
