"""Core data models for Civilization V mod files."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import xml.etree.ElementTree as ET
import hashlib
import os
import uuid
import logging
from .paths import normalize_game_path, normalize_system_path, paths_equal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FileEntry:
    """Represents a file in the mod."""
    path: str
    import_to_vfs: bool
    type: str = ""  # SubType in civ5proj
    md5: Optional[str] = None

    @staticmethod
    def calculate_md5(file_path: str) -> str:
        """Calculate MD5 hash of a file."""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest().upper()
        except Exception as e:
            logger.error(f"Error calculating MD5 for {file_path}: {e}")
            return ""

@dataclass
class Association:
    """Represents a dependency or blocker association."""
    type: str  # "Game", "Dlc", or "Mod"
    name: str = ""
    id: Optional[str] = None
    min_version: str = "0"
    max_version: str = "999"

@dataclass
class Action:
    """Represents a mod action."""
    action_set: str  # e.g., "OnModActivated"
    action_type: str  # e.g., "UpdateDatabase"
    filename: str

@dataclass
class EntryPoint:
    """Represents a mod entry point."""
    type: str
    file: str
    name: str = ""
    description: str = ""

@dataclass
class ModProject:
    """Represents a complete mod project."""
    # Basic Properties
    name: str
    project_guid: str = field(default_factory=lambda: f"{{{str(uuid.uuid4())}}}")
    mod_guid: str = field(default_factory=lambda: f"{{{str(uuid.uuid4())}}}")
    version: str = "1"
    stability: str = "Stable"
    teaser: str = ""
    description: str = ""
    authors: str = ""
    special_thanks: str = ""
    homepage: str = ""

    # Support Flags
    affects_saves: bool = True
    min_save_version: str = field(default="")  # defaults to version if empty
    supports_singleplayer: bool = True
    supports_multiplayer: bool = True
    supports_hotseat: bool = True
    supports_mac: bool = True
    hide_setup_game: bool = False

    # System Flags
    reload_audio: bool = True
    reload_landmark: bool = True
    reload_strategic_view: bool = True
    reload_unit: bool = True

    # Content
    dependencies: List[Association] = field(default_factory=list)
    blockers: List[Association] = field(default_factory=list)
    files: List[FileEntry] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    entry_points: List[EntryPoint] = field(default_factory=list)

    @property
    def min_compatible_save_version(self) -> str:
        """Get minimum compatible save version, defaults to current version."""
        return self.min_save_version or self.version

    def to_modinfo(self, base_path: Path) -> ET.Element:
        """Convert to modinfo XML format."""
        root = ET.Element("Mod")
        root.set("id", self.mod_guid)
        root.set("version", self.version)

        # Properties section
        props = ET.SubElement(root, "Properties")
        ET.SubElement(props, "Name").text = self.name
        ET.SubElement(props, "Teaser").text = self.teaser
        ET.SubElement(props, "Description").text = self.description
        ET.SubElement(props, "Authors").text = self.authors
        if self.homepage:
            ET.SubElement(props, "Homepage").text = self.homepage
        
        # Support flags
        ET.SubElement(props, "SupportsSinglePlayer").text = "1" if self.supports_singleplayer else "0"
        ET.SubElement(props, "SupportsMultiplayer").text = "1" if self.supports_multiplayer else "0"
        ET.SubElement(props, "SupportsHotSeat").text = "1" if self.supports_hotseat else "0"
        ET.SubElement(props, "SupportsMac").text = "1" if self.supports_mac else "0"
        
        # System properties
        ET.SubElement(props, "AffectsSavedGames").text = "1" if self.affects_saves else "0"
        ET.SubElement(props, "MinCompatibleSaveVersion").text = self.min_compatible_save_version
        ET.SubElement(props, "HideSetupGame").text = "1" if self.hide_setup_game else "0"
        ET.SubElement(props, "ReloadAudioSystem").text = "1" if self.reload_audio else "0"
        ET.SubElement(props, "ReloadLandmarkSystem").text = "1" if self.reload_landmark else "0"
        ET.SubElement(props, "ReloadStrategicViewSystem").text = "1" if self.reload_strategic_view else "0"
        ET.SubElement(props, "ReloadUnitSystem").text = "1" if self.reload_unit else "0"

        # Dependencies
        if any(d.type in ["Game", "Dlc"] for d in self.dependencies):
            deps = ET.SubElement(root, "Dependencies")
            for dep in self.dependencies:
                if dep.type == "Game":
                    game = ET.SubElement(deps, "Game")
                    game.set("minversion", dep.min_version)
                    game.set("maxversion", dep.max_version)
                elif dep.type == "Dlc":
                    dlc = ET.SubElement(deps, "Dlc")
                    dlc.set("id", dep.id)
                    dlc.set("minversion", dep.min_version)
                    dlc.set("maxversion", dep.max_version)

        # References (always included)
        ET.SubElement(root, "References")

        # Blockers
        if self.blockers:
            blocks = ET.SubElement(root, "Blocks")
            for block in self.blockers:
                if block.type == "Mod":
                    mod = ET.SubElement(blocks, "Mod")
                    mod.set("id", block.id)
                    mod.set("minversion", block.min_version)
                    mod.set("maxversion", block.max_version)
                    mod.set("title", block.name)

        # Files
        if self.files:
            files = ET.SubElement(root, "Files")
            for file in sorted(self.files, key=lambda x: normalize_game_path(x.path)):
                file_elem = ET.SubElement(files, "File")
                
                if file.import_to_vfs:
                    sys_path = normalize_system_path(base_path, file.path)
                    if os.path.exists(sys_path):
                        try:
                            md5 = FileEntry.calculate_md5(sys_path)
                            if md5:
                                file_elem.set("md5", md5)
                        except Exception as e:
                            logger.warning(f"Error calculating MD5 for {sys_path}: {e}")
                    else:
                        logger.warning(f"File not found: {sys_path} (game path: {file.path})")
                
                file_elem.set("import", "1" if file.import_to_vfs else "0")
                file_elem.text = normalize_game_path(file.path)

        # Actions
        if self.actions:
            actions = ET.SubElement(root, "Actions")
            action_groups = {}
            for action in self.actions:
                if action.action_set not in action_groups:
                    action_groups[action.action_set] = []
                action_groups[action.action_set].append(action)

            for set_name, set_actions in action_groups.items():
                set_elem = ET.SubElement(actions, set_name)
                for action in set_actions:
                    if action.action_type == "UpdateDatabase":
                        ET.SubElement(set_elem, "UpdateDatabase").text = normalize_game_path(action.filename)
                    elif action.action_type == "SetDllPath":
                        ET.SubElement(set_elem, "SetDllPath").text = normalize_game_path(action.filename)

        # Entry Points
        if self.entry_points:
            entry_points = ET.SubElement(root, "EntryPoints")
            for ep in self.entry_points:
                ep_elem = ET.SubElement(entry_points, "EntryPoint")
                ep_elem.set("type", ep.type)
                ep_elem.set("file", normalize_game_path(ep.file))
                if ep.name:
                    name_elem = ET.SubElement(ep_elem, "Name")
                    name_elem.text = ep.name
                if ep.description:
                    desc_elem = ET.SubElement(ep_elem, "Description")
                    desc_elem.text = ep.description

        return root

    def to_civ5proj(self) -> ET.Element:
        """Convert to civ5proj XML format."""
        ns = "http://schemas.microsoft.com/developer/msbuild/2003"
        ET.register_namespace('', ns)
        root = ET.Element("Project", {
            "DefaultTargets": "Deploy",
            "ToolsVersion": "4.0",
            "xmlns": ns
        })

        # Basic Properties
        props = ET.SubElement(root, "PropertyGroup")
        ET.SubElement(props, "Configuration").text = "Default"
        ET.SubElement(props, "ProjectGuid").text = self.project_guid
        ET.SubElement(props, "Name").text = self.name
        ET.SubElement(props, "Guid").text = self.mod_guid
        ET.SubElement(props, "ModVersion").text = self.version
        ET.SubElement(props, "Stability").text = self.stability
        ET.SubElement(props, "Teaser").text = self.teaser
        ET.SubElement(props, "Description").text = self.description
        ET.SubElement(props, "Authors").text = self.authors
        ET.SubElement(props, "SpecialThanks").text = self.special_thanks
        ET.SubElement(props, "Homepage").text = self.homepage

        # Support Flags
        ET.SubElement(props, "AffectsSavedGames").text = str(self.affects_saves).lower()
        ET.SubElement(props, "MinCompatibleSaveVersion").text = self.min_compatible_save_version
        ET.SubElement(props, "SupportsSinglePlayer").text = str(self.supports_singleplayer).lower()
        ET.SubElement(props, "SupportsMultiplayer").text = str(self.supports_multiplayer).lower()
        ET.SubElement(props, "SupportsHotSeat").text = str(self.supports_hotseat).lower()
        ET.SubElement(props, "SupportsMac").text = str(self.supports_mac).lower()
        ET.SubElement(props, "HideSetupGame").text = str(self.hide_setup_game).lower()
        ET.SubElement(props, "ReloadUnitSystem").text = str(self.reload_unit).lower()
        ET.SubElement(props, "ReloadLandmarkSystem").text = str(self.reload_landmark).lower()
        ET.SubElement(props, "ReloadStrategicViewSystem").text = str(self.reload_strategic_view).lower()

        # Dependencies
        if self.dependencies:
            deps = ET.SubElement(root, "ModDependencies")
            for dep in self.dependencies:
                assoc = ET.SubElement(deps, "Association")
                ET.SubElement(assoc, "Type").text = dep.type
                ET.SubElement(assoc, "Name").text = dep.name
                ET.SubElement(assoc, "Id").text = dep.id
                ET.SubElement(assoc, "MinVersion").text = dep.min_version
                ET.SubElement(assoc, "MaxVersion").text = dep.max_version

        # Blockers
        if self.blockers:
            blocks = ET.SubElement(root, "ModBlockers")
            for block in self.blockers:
                assoc = ET.SubElement(blocks, "Association")
                ET.SubElement(assoc, "Type").text = block.type
                ET.SubElement(assoc, "Name").text = block.name
                ET.SubElement(assoc, "Id").text = block.id
                ET.SubElement(assoc, "MinVersion").text = block.min_version
                ET.SubElement(assoc, "MaxVersion").text = block.max_version

        # Actions
        if self.actions:
            actions = ET.SubElement(root, "ModActions")
            for action in self.actions:
                action_elem = ET.SubElement(actions, "Action")
                ET.SubElement(action_elem, "Set").text = action.action_set
                ET.SubElement(action_elem, "Type").text = action.action_type
                ET.SubElement(action_elem, "FileName").text = normalize_game_path(action.filename)

        # Content Files
        if self.files:
            files = ET.SubElement(root, "ItemGroup")
            for file in sorted(self.files, key=lambda x: normalize_game_path(x.path)):
                content = ET.SubElement(files, "Content", {"Include": normalize_game_path(file.path)})
                if file.type:
                    ET.SubElement(content, "SubType").text = file.type
                ET.SubElement(content, "ImportIntoVFS").text = str(file.import_to_vfs).lower()

        # Entry Points
        if self.entry_points:
            content = ET.SubElement(root, "ModContent")
            for ep in self.entry_points:
                ep_elem = ET.SubElement(content, "Content")
                ET.SubElement(ep_elem, "Type").text = ep.type
                if ep.name:
                    ET.SubElement(ep_elem, "Name").text = ep.name
                if ep.description:
                    ET.SubElement(ep_elem, "Description").text = ep.description
                ET.SubElement(ep_elem, "FileName").text = normalize_game_path(ep.file)

        return root

    @classmethod
    def from_modinfo(cls, modinfo_path: Path) -> 'ModProject':
        """Create ModProject from a .modinfo file."""
        tree = ET.parse(str(modinfo_path))
        root = tree.getroot()
        
        # Extract basic properties
        props = root.find("Properties")
        project = cls(
            name=props.find("Name").text,
            mod_guid=root.get("id"),
            version=root.get("version"),
            teaser=props.find("Teaser").text,
            description=props.find("Description").text,
            authors=props.find("Authors").text,
            homepage=props.find("Homepage").text if props.find("Homepage") is not None else "",
        )

        # Support flags
        project.supports_singleplayer = props.find("SupportsSinglePlayer").text == "1"
        project.supports_multiplayer = props.find("SupportsMultiplayer").text == "1"
        project.supports_hotseat = props.find("SupportsHotSeat").text == "1"
        project.supports_mac = props.find("SupportsMac").text == "1"
        
        # System properties
        project.affects_saves = props.find("AffectsSavedGames").text == "1"
        project.min_save_version = props.find("MinCompatibleSaveVersion").text
        project.hide_setup_game = props.find("HideSetupGame").text == "1" if props.find("HideSetupGame") is not None else False
        project.reload_audio = props.find("ReloadAudioSystem").text == "1"
        project.reload_landmark = props.find("ReloadLandmarkSystem").text == "1"
        project.reload_strategic_view = props.find("ReloadStrategicViewSystem").text == "1"
        project.reload_unit = props.find("ReloadUnitSystem").text == "1"

        # Dependencies
        deps = root.find("Dependencies")
        if deps is not None:
            game = deps.find("Game")
            if game is not None:
                project.dependencies.append(Association(
                    type="Game",
                    id=None,  # Game dependency doesn't have an ID
                    min_version=game.get("minversion", "0"),
                    max_version=game.get("maxversion", "999")
                ))
            for dlc in deps.findall("Dlc"):
                project.dependencies.append(Association(
                    type="Dlc",
                    id=dlc.get("id"),
                    min_version=dlc.get("minversion", "0"),
                    max_version=dlc.get("maxversion", "999")
                ))

        # Blockers
        blocks = root.find("Blocks")
        if blocks is not None:
            for mod in blocks.findall("Mod"):
                project.blockers.append(Association(
                    type="Mod",
                    name=mod.get("title"),
                    id=mod.get("id"),
                    min_version=mod.get("minversion", "0"),
                    max_version=mod.get("maxversion", "999")
                ))

        # Files
        files = root.find("Files")
        if files is not None:
            for file in files.findall("File"):
                project.files.append(FileEntry(
                    path=normalize_game_path(file.text),
                    import_to_vfs=file.get("import") == "1",
                    md5=file.get("md5")
                ))

        # Actions
        actions = root.find("Actions")
        if actions is not None:
            for action_set in actions:
                set_name = action_set.tag
                for action in action_set:
                    action_type = action.tag
                    project.actions.append(Action(
                        action_set=set_name,
                        action_type=action_type,
                        filename=normalize_game_path(action.text)
                    ))

        # Entry Points
        entry_points = root.find("EntryPoints")
        if entry_points is not None:
            for ep in entry_points.findall("EntryPoint"):
                name = ep.find("Name")
                desc = ep.find("Description")
                project.entry_points.append(EntryPoint(
                    type=ep.get("type"),
                    file=normalize_game_path(ep.get("file")),
                    name=name.text if name is not None else "",
                    description=desc.text if desc is not None else ""
                ))

        return project

    @classmethod
    def from_civ5proj(cls, civ5proj_path: Path) -> 'ModProject':
        """Create ModProject from a .civ5proj file."""
        tree = ET.parse(str(civ5proj_path))
        root = tree.getroot()
        ns = {'ms': 'http://schemas.microsoft.com/developer/msbuild/2003'}

        # Find PropertyGroup with mod properties
        props = None
        for prop_group in root.findall('ms:PropertyGroup', ns):
            if prop_group.find('ms:Name', ns) is not None:
                props = prop_group
                break

        if props is None:
            raise ValueError("PropertyGroup section missing from project file")

        def get_text(elem, tag, default=""):
            node = elem.find(f'ms:{tag}', ns)
            return node.text if node is not None else default

        def get_bool(elem, tag, default=True):
            node = elem.find(f'ms:{tag}', ns)
            return node.text.lower() == "true" if node is not None else default

        # Create project instance
        project = cls(
            name=get_text(props, "Name"),
            project_guid=get_text(props, "ProjectGuid"),
            mod_guid=get_text(props, "Guid"),
            version=get_text(props, "ModVersion"),
            stability=get_text(props, "Stability", "Stable"),
            teaser=get_text(props, "Teaser"),
            description=get_text(props, "Description"),
            authors=get_text(props, "Authors"),
            special_thanks=get_text(props, "SpecialThanks"),
            homepage=get_text(props, "Homepage"),
        )

        # Support flags
        project.affects_saves = get_bool(props, "AffectsSavedGames")
        project.min_save_version = get_text(props, "MinCompatibleSaveVersion")
        project.supports_singleplayer = get_bool(props, "SupportsSinglePlayer")
        project.supports_multiplayer = get_bool(props, "SupportsMultiplayer")
        project.supports_hotseat = get_bool(props, "SupportsHotSeat")
        project.supports_mac = get_bool(props, "SupportsMac")
        project.hide_setup_game = get_bool(props, "HideSetupGame", False)
        project.reload_unit = get_bool(props, "ReloadUnitSystem")
        project.reload_landmark = get_bool(props, "ReloadLandmarkSystem")
        project.reload_strategic_view = get_bool(props, "ReloadStrategicViewSystem")

        # Dependencies
        for assoc in root.findall('.//ms:ModDependencies/ms:Association', ns):
            project.dependencies.append(Association(
                type=get_text(assoc, "Type"),
                name=get_text(assoc, "Name"),
                id=get_text(assoc, "Id"),
                min_version=get_text(assoc, "MinVersion", "0"),
                max_version=get_text(assoc, "MaxVersion", "999")
            ))

        # Blockers
        for assoc in root.findall('.//ms:ModBlockers/ms:Association', ns):
            project.blockers.append(Association(
                type=get_text(assoc, "Type"),
                name=get_text(assoc, "Name"),
                id=get_text(assoc, "Id"),
                min_version=get_text(assoc, "MinVersion", "0"),
                max_version=get_text(assoc, "MaxVersion", "999")
            ))

        # Actions
        for action in root.findall('.//ms:ModActions/ms:Action', ns):
            project.actions.append(Action(
                action_set=get_text(action, "Set"),
                action_type=get_text(action, "Type"),
                filename=normalize_game_path(get_text(action, "FileName"))
            ))

        # Files
        for content in root.findall('.//ms:ItemGroup/ms:Content', ns):
            file_path = content.get('Include')
            if file_path:
                project.files.append(FileEntry(
                    path=normalize_game_path(file_path),
                    import_to_vfs=get_bool(content, "ImportIntoVFS", False),
                    type=get_text(content, "SubType")
                ))

        # Entry Points
        for content in root.findall('.//ms:ModContent/ms:Content', ns):
            project.entry_points.append(EntryPoint(
                type=get_text(content, "Type"),
                file=normalize_game_path(get_text(content, "FileName")),
                name=get_text(content, "Name"),
                description=get_text(content, "Description")
            ))

        return project

    def write_modinfo(self, output_path: Path, base_path: Optional[Path] = None):
        """Write the project to a .modinfo file."""
        if base_path is None:
            base_path = output_path.parent
        
        tree = ET.ElementTree(self.to_modinfo(base_path))
        
        # Use minidom for pretty printing
        from xml.dom import minidom
        rough_string = ET.tostring(tree.getroot(), 'utf-8')
        reparsed = minidom.parseString(rough_string)
        
        with open(output_path, "w", encoding='utf-8') as f:
            f.write(reparsed.toprettyxml(indent="  "))

    def write_civ5proj(self, output_path: Path, create_solution: bool = True):
        """Write the project to a .civ5proj file."""
        tree = ET.ElementTree(self.to_civ5proj())
        
        # Use base name (without version or prefix) for project files
        output_dir = output_path.parent
        base_name = self.name.split(" (v ")[0]  # Remove version if present
        if base_name.startswith("(1) "):  # Remove prefix if present
            base_name = base_name[4:]  # Remove "(1) " prefix
        output_path = output_dir / f"{base_name}.civ5proj"
        
        # Use minidom for pretty printing
        from xml.dom import minidom
        rough_string = ET.tostring(tree.getroot(), 'utf-8')
        reparsed = minidom.parseString(rough_string)
        
        with open(output_path, "w", encoding='utf-8') as f:
            f.write(reparsed.toprettyxml(indent="  "))

        # Create or update solution file if requested
        if create_solution:
            from .solution import ModSolution
            sln_path = output_dir / f"{base_name}.civ5sln"
            
            # Try to load existing solution or create new one
            try:
                solution = ModSolution.from_sln(sln_path)
                
                # Check if project is already in solution
                proj_paths = [p.path for p in solution.projects]
                if output_path.name not in proj_paths:
                    from .solution import ProjectReference
                    solution.projects.append(ProjectReference(
                        path=output_path.name,
                        name=self.name
                    ))
            except (FileNotFoundError, ET.ParseError):
                # Create new solution
                solution = ModSolution.create_for_project(output_path, self.name)
            
            # Write solution file
            solution.write(sln_path)