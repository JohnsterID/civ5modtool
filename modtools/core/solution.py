""".civ5sln (ModBuddy solution) reader and writer.

Format as ModBuddy writes it (VP's solutions are the reference): UTF-8 BOM, an
empty first line, CRLF, upper-case project GUIDs, and the three ModBuddy
configurations Default / Deploy Only / Package Only.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import re
import uuid

MODBUDDY_PROJECT_TYPE = "{F5FC21B5-7CC2-458A-ABBA-992F515BBA20}"
CONFIGURATIONS = ("Default", "Deploy Only", "Package Only")
_PROJECT = re.compile(r'^Project\("(\{[^}]+\})"\)\s*=\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"(\{[^}]*\})"', re.M)


def _guid(value: str) -> str:
    return "{%s}" % value.strip().strip("{}").upper()


@dataclass
class ProjectReference:
    """A project in a solution; `path` is relative to the .civ5sln."""
    path: str
    name: str
    guid: str = ""
    type_guid: str = MODBUDDY_PROJECT_TYPE


@dataclass
class ModSolution:
    name: str
    guid: str = field(default_factory=lambda: "{%s}" % uuid.uuid4())
    configuration: str = "Default"
    projects: List[ProjectReference] = field(default_factory=list)

    @staticmethod
    def normalize_path(path: str) -> str:
        return str(path).replace("/", "\\")

    def to_sln(self) -> str:
        lines = ["",
                 "Microsoft Visual Studio Solution File, Format Version 11.00",
                 "# ModBuddy Solution File, Format Version 11.00"]
        for proj in self.projects:
            if not proj.guid:
                proj.guid = "{%s}" % uuid.uuid4()
            lines.append(f'Project("{_guid(proj.type_guid)}") = "{proj.name}", '
                         f'"{self.normalize_path(proj.path)}", "{_guid(proj.guid)}"')
            lines.append("EndProject")
        lines += ["Global", "\tGlobalSection(SolutionConfigurationPlatforms) = preSolution"]
        lines += [f"\t\t{c}|x86 = {c}|x86" for c in CONFIGURATIONS]
        lines += ["\tEndGlobalSection", "\tGlobalSection(ProjectConfigurationPlatforms) = postSolution"]
        for proj in self.projects:
            for c in CONFIGURATIONS:
                lines.append(f"\t\t{_guid(proj.guid)}.{c}|x86.ActiveCfg = {c}|x86")
                lines.append(f"\t\t{_guid(proj.guid)}.{c}|x86.Build.0 = {c}|x86")
        lines += ["\tEndGlobalSection", "\tGlobalSection(SolutionProperties) = preSolution",
                  "\t\tHideSolutionNode = FALSE", "\tEndGlobalSection", "EndGlobal", ""]
        return "\n".join(lines)

    def write(self, path: Path) -> None:
        with open(path, "w", encoding="utf-8-sig", newline="\r\n") as f:
            f.write(self.to_sln())

    @classmethod
    def from_sln(cls, path: Path) -> "ModSolution":
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        projects = [ProjectReference(path=p, name=n, guid=g, type_guid=t)
                    for t, n, p, g in _PROJECT.findall(content)]
        if not projects:
            raise ValueError(f"{path}: no project in solution")
        return cls(name=projects[0].name, projects=projects)

    @classmethod
    def create_for_project(cls, project_path: Path, project_name: Optional[str] = None,
                           project_guid: Optional[str] = None) -> "ModSolution":
        name = project_name or Path(project_path).stem
        return cls(name=name, projects=[ProjectReference(path=str(Path(project_path).name), name=name,
                                                         guid=project_guid or "{%s}" % uuid.uuid4())])


def add_project_to_solution(sln_path: Path, proj_path: Path, project) -> ModSolution:
    """Create `sln_path` for the project, or add/refresh the project in an
    existing solution (matched by file name or GUID; other projects are kept)."""
    guid = project.ensure_project_guid()
    name = proj_path.stem  # ModBuddy names the project after its file, e.g. "Community Patch"
    rel = proj_path.name if proj_path.parent.resolve() == sln_path.parent.resolve() else str(proj_path)
    try:
        sln = ModSolution.from_sln(sln_path)
    except (FileNotFoundError, ValueError):
        sln = ModSolution.create_for_project(proj_path, name, guid)
    else:
        for ref in sln.projects:
            if ref.path.lower() == rel.lower() or _guid(ref.guid) == _guid(guid):
                ref.path, ref.name, ref.guid = rel, name, guid
                break
        else:
            sln.projects.append(ProjectReference(path=rel, name=name, guid=guid))
    sln.write(sln_path)
    return sln
