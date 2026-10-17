"""modtools command line.

    modtools proj2modinfo <project.civ5proj | mod folder>... [-o FILE | --output-dir DIR] [--style vp|modbuddy] [--strict]
    modtools modinfo2proj <mod.modinfo> [-o FILE.civ5proj] [--no-solution] [--lf]
    modtools update-md5   <mod.modinfo>... [--check]
    modtools validate     <file>... [--packaged] [--civ5xp] [--strict]
    modtools compare      <a> <b>
    modtools civ5xp-install <mod folder> [--mods-dir DIR] [--name NAME] [--replace] [--dry-run]
    modtools gui          [file]

Exit status: 0 ok, 1 problems found (validate errors, stale MD5s with --check,
differences for compare, missing files with --strict), 2 usage or I/O error.
"""
import argparse
import sys
from pathlib import Path
from typing import List, Optional
import xml.etree.ElementTree as ET

from .. import __version__
from ..core import civ5xp
from ..core.civ5proj import default_civ5proj_path, read_civ5proj
from ..core.compare import compare_projects, load
from ..core.md5 import update_md5
from ..core.modinfo import read_modinfo, write_modinfo
from ..core.validate import validate_path


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _project_file(arg: str) -> Path:
    """A .civ5proj, or a folder holding exactly one."""
    path = Path(arg)
    if path.is_dir():
        found = sorted(path.glob("*.civ5proj"))
        if len(found) != 1:
            raise ValueError(f"{path}: expected one .civ5proj, found {len(found)}")
        return found[0]
    if not path.is_file():
        raise ValueError(f"not found: {path}")
    return path


def cmd_proj2modinfo(a) -> int:
    if a.output and len(a.projects) > 1:
        raise ValueError("--output takes one project; use --output-dir for several")
    status = 0
    for arg in a.projects:
        proj = _project_file(arg)
        p = read_civ5proj(proj)
        out = Path(a.output) if a.output else Path(a.output_dir or proj.parent) / p.modinfo_filename()
        missing = write_modinfo(p, out, proj.parent, a.style)
        for m in missing:
            _err(f"warning: file not found, left out: {m}")
        print(f"wrote {out} ({len(p.files) - len(missing)} files)")
        if missing and a.strict:
            status = 1
    return status


def cmd_modinfo2proj(a) -> int:
    src = Path(a.modinfo)
    p = read_modinfo(src)
    out = Path(a.output) if a.output else default_civ5proj_path(p, src.parent)
    p.write_civ5proj(out, create_solution=not a.no_solution, newline="\n" if a.lf else "\r\n")
    print(f"wrote {out}" + ("" if a.no_solution else f" and {out.with_suffix('.civ5sln')}"))
    return 0


def cmd_update_md5(a) -> int:
    status = 0
    for arg in a.modinfo:
        path = Path(arg)
        r = update_md5(path, check_only=a.check)
        verb = "stale" if a.check else "updated"
        for m in r.missing:
            _err(f"{path.name}: file not found: {m}")
        for c in r.changed:
            print(f"{path.name}: {verb}: {c}")
        print(f"{path.name}: {len(r.changed)} {verb}, {r.unchanged} current, {len(r.missing)} missing")
        if r.missing or (a.check and r.changed):
            status = 1
    return status


def cmd_validate(a) -> int:
    status = 0
    for arg in a.files:
        path = Path(arg)
        issues = validate_path(path, packaged=a.packaged, civ5xp=a.civ5xp)
        errors = [i for i in issues if i.severity == "error"]
        for i in issues:
            print(f"{path.name}: {i}")
        print(f"{path.name}: {len(errors)} errors, {len(issues) - len(errors)} warnings")
        if errors or (a.strict and issues):
            status = 1
    return status


def cmd_compare(a) -> int:
    diffs = compare_projects(load(Path(a.first)), load(Path(a.second)))
    for d in diffs:
        print(d)
    print("same" if not diffs else f"{len(diffs)} differences")
    return 1 if diffs else 0


def cmd_civ5xp_install(a) -> int:
    src = Path(a.mod_folder)
    if not src.is_dir():
        raise ValueError(f"not a folder: {src}")
    r = civ5xp.install(src, Path(a.mods_dir) if a.mods_dir else None, a.name, a.replace, a.dry_run)
    if r.collisions:
        for low, names in sorted(r.collisions.items()):
            _err(f"collision once lower-cased: {', '.join(names)} -> {low}")
        _err("nothing copied: rename those files first (Civ5XP would only ever see one of them)")
        return 1
    print(f"{'would copy' if a.dry_run else 'copied'} {r.copied} files to {r.target}")
    return 0


def cmd_gui(a) -> int:
    from ..gui.main import main as gui_main
    return gui_main(a.file)


def create_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="modtools",
                                 description="Civilization V mod files: .modinfo, .civ5proj, .civ5sln")
    ap.add_argument("--version", action="version", version=f"modtools {__version__}")
    sub = ap.add_subparsers(dest="command", metavar="command")

    s = sub.add_parser("proj2modinfo", help="build the .modinfo from a .civ5proj (same bytes as VP's "
                                            "scripts/generate_modinfo.py, or ModBuddy with --style modbuddy)")
    s.add_argument("projects", nargs="+", help=".civ5proj files or mod folders")
    s.add_argument("-o", "--output", help="output file (default: '<Name> (v <version>).modinfo' next to the project)")
    s.add_argument("--output-dir", help="write the .modinfo files here")
    s.add_argument("--style", choices=("vp", "modbuddy"), default="vp",
                   help="vp: LF and a final newline, as VP's generate_modinfo.py (default); "
                        "modbuddy: CRLF and no final newline, as ModBuddy")
    s.add_argument("--strict", action="store_true", help="exit 1 if a listed file is missing")
    s.set_defaults(func=cmd_proj2modinfo)

    s = sub.add_parser("modinfo2proj", help="rebuild a ModBuddy .civ5proj (and .civ5sln) from a .modinfo")
    s.add_argument("modinfo")
    s.add_argument("-o", "--output", help="output .civ5proj (default: '<Name without (N) prefix>.civ5proj' "
                                          "next to the .modinfo)")
    s.add_argument("--no-solution", action="store_true", help="do not create or update the .civ5sln")
    s.add_argument("--lf", action="store_true", help="LF line endings (default CRLF, like ModBuddy)")
    s.set_defaults(func=cmd_modinfo2proj)

    s = sub.add_parser("update-md5", help="refresh the MD5s of a .modinfo in place (nothing else changes)")
    s.add_argument("modinfo", nargs="+")
    s.add_argument("--check", action="store_true", help="only report; exit 1 if any MD5 is stale or a file is missing")
    s.set_defaults(func=cmd_update_md5)

    s = sub.add_parser("validate", help="check .modinfo, .civ5proj or .civ5sln files")
    s.add_argument("files", nargs="+")
    s.add_argument("--packaged", action="store_true",
                   help="the mod is installed as a packaged .civ5mod, where the game checks MD5s: MD5 problems are errors")
    s.add_argument("--civ5xp", action="store_true",
                   help="also check for Civ5XP (Linux), which lower-cases every path under MODS: names on disk must be lower case")
    s.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("civ5xp-install", help="copy a mod into Civ5XP's (Linux) MODS folder with every name lower-cased")
    s.add_argument("mod_folder")
    s.add_argument("--mods-dir", help="MODS folder (default: $XDG_DATA_HOME or ~/.local/share, "
                                      "+ /Aspyr/Sid Meier's Civilization 5/MODS)")
    s.add_argument("--name", help="folder name under MODS (default: the mod folder's name), lower-cased")
    s.add_argument("--replace", action="store_true", help="replace an existing copy")
    s.add_argument("--dry-run", action="store_true", help="only report what would be copied")
    s.set_defaults(func=cmd_civ5xp_install)

    s = sub.add_parser("compare", help="compare two mods (.modinfo/.civ5proj in any combination)")
    s.add_argument("first")
    s.add_argument("second")
    s.set_defaults(func=cmd_compare)

    s = sub.add_parser("gui", help="open the editor window (Tkinter)")
    s.add_argument("file", nargs="?", help=".modinfo or .civ5proj to open")
    s.set_defaults(func=cmd_gui)
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    ap = create_parser()
    a = ap.parse_args(argv)
    if not getattr(a, "func", None):
        ap.print_help()
        return 2
    try:
        return a.func(a)
    except (OSError, ET.ParseError, ValueError) as e:
        _err(f"error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
