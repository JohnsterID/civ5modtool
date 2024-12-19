"""Solution file handling for Civilization V mods."""
import re
from dataclasses import dataclass, field
from pathlib import Path
import uuid
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

@dataclass
class ProjectReference:
    """Represents a project reference in a solution."""
    path: str
    name: str
    guid: str = ""

@dataclass
class ModSolution:
    """Represents a Civilization V solution (.civ5sln)."""
    name: str
    guid: str = field(default_factory=lambda: f"{{{str(uuid.uuid4())}}}")
    configuration: str = "Default"
    projects: List[ProjectReference] = field(default_factory=list)

    @staticmethod
    def normalize_path(path: str) -> str:
        """Normalize path to Windows style."""
        return str(Path(path)).replace('/', '\\')

    def to_sln(self) -> str:
        """Convert to Visual Studio solution format."""
        lines = [
            "",  # BOM will be added when writing
            "Microsoft Visual Studio Solution File, Format Version 11.00",
            "# ModBuddy Solution File, Format Version 11.00"
        ]

        # Add project declarations
        for proj in self.projects:
            proj_path = self.normalize_path(proj.path)
            # ModBuddy project type GUID
            lines.append(f'Project("{{F5FC21B5-7CC2-458A-ABBA-992F515BBA20}}") = "{proj.name}", "{proj_path}", "{proj.guid}"')
            lines.append("EndProject")

        # Add solution configurations
        lines.extend([
            "Global",
            "\tGlobalSection(SolutionConfigurationPlatforms) = preSolution",
            "\t\tDefault|x86 = Default|x86",
            "\t\tDeploy Only|x86 = Deploy Only|x86",
            "\t\tPackage Only|x86 = Package Only|x86",
            "\tEndGlobalSection"
        ])

        # Add project configurations
        lines.append("\tGlobalSection(ProjectConfigurationPlatforms) = postSolution")
        for proj in self.projects:
            # VS uses uppercase GUIDs in configuration section
            guid = proj.guid.strip('{}').upper()
            lines.extend([
                f"\t\t{{{guid}}}.Default|x86.ActiveCfg = Default|x86",
                f"\t\t{{{guid}}}.Default|x86.Build.0 = Default|x86",
                f"\t\t{{{guid}}}.Deploy Only|x86.ActiveCfg = Deploy Only|x86",
                f"\t\t{{{guid}}}.Deploy Only|x86.Build.0 = Deploy Only|x86",
                f"\t\t{{{guid}}}.Package Only|x86.ActiveCfg = Package Only|x86",
                f"\t\t{{{guid}}}.Package Only|x86.Build.0 = Package Only|x86"
            ])
        lines.append("\tEndGlobalSection")

        # Add solution properties
        lines.extend([
            "\tGlobalSection(SolutionProperties) = preSolution",
            "\t\tHideSolutionNode = FALSE",
            "\tEndGlobalSection",
            "EndGlobal"
        ])

        return "\n".join(lines)

    def write(self, path: Path):
        """Write the solution to a .civ5sln file."""
        content = self.to_sln()
        # Write with BOM for Visual Studio compatibility
        with open(path, "w", encoding='utf-8-sig') as f:
            f.write(content)

    @classmethod
    def from_sln(cls, path: Path) -> 'ModSolution':
        """Create ModSolution from a .civ5sln file."""
        with open(path, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        # Extract solution name from first project name
        proj_match = re.search(r'Project.*?\s*=\s*"([^"]+)"', content)
        if not proj_match:
            raise ValueError("No project found in solution file")
        name = proj_match.group(1)

        # Create solution instance
        solution = cls(name=name)

        # Extract projects
        proj_pattern = r'Project\("({[^}]+})"\)\s*=\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"({[^}]+})"'
        for match in re.finditer(proj_pattern, content, re.MULTILINE):
            type_guid, proj_name, proj_path, proj_guid = match.groups()
            if type_guid.lower() == "{f5fc21b5-7cc2-458a-abba-992f515bba20}":  # ModBuddy project type
                solution.projects.append(ProjectReference(
                    name=proj_name,
                    path=proj_path,
                    guid=proj_guid
                ))

        return solution

    @classmethod
    def create_for_project(cls, project_path: Path, project_name: Optional[str] = None) -> 'ModSolution':
        """Create a new solution for a project."""
        if project_name is None:
            project_name = project_path.stem
        
        return cls(
            name=project_name,
            projects=[ProjectReference(
                path=str(project_path.name),
                name=project_name,
                guid=str(uuid.uuid4())
            )]
        )