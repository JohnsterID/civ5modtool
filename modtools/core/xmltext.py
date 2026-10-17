"""Text helpers shared by the writers: escaping, booleans, file output."""
from pathlib import Path
import hashlib
import os


def escape_xml(text: str) -> str:
    """Escape element text and attribute values the way ModBuddy and VP's
    generate_modinfo.py do (&, <, > and ")."""
    if not text:
        return ""
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


def parse_bool(value, default: bool) -> bool:
    """Booleans as the game reads them (FXmlNVPair::GetVal(bool&)): a value
    starting with t/T is true, f/F false, otherwise a number (0 = false)."""
    if value is None:
        return default
    value = value.strip()
    if not value:
        return default
    if value[0] in "tT":
        return True
    if value[0] in "fF":
        return False
    try:
        return int(value) != 0
    except ValueError:
        return default


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def write_text(path: Path, text: str, newline: str = "\n", bom: bool = True) -> None:
    """Write `text` (built with "\\n") as UTF-8, with a BOM like ModBuddy, and
    the requested line ending."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig" if bom else "utf-8", newline=newline) as f:
        f.write(text)


def _parts(path: str):
    return [p for p in path.replace("\\", "/").split("/") if p and p != "."]


def disk_parts(mod_dir: Path, path: str):
    """The names on disk for a mod-relative path ("/" or "\\"), matching each
    part case-insensitively when the exact name is not there (as Windows does).
    None if some part does not exist."""
    cur, names = mod_dir, []
    for part in _parts(path):
        try:
            entries = os.listdir(cur)
        except OSError:
            return None
        match = part if part in entries else next((e for e in entries if e.lower() == part.lower()), None)
        if match is None:
            return None
        names.append(match)
        cur = cur / match
    return names


def mod_file_path(mod_dir: Path, path: str) -> Path:
    """The file for a mod-relative path on this system: exact, or matched
    case-insensitively (so a Windows-cased list finds a lower-cased Civ5XP
    copy on Linux). Falls back to the path as written if nothing matches."""
    exact = mod_dir.joinpath(*_parts(path))
    if exact.exists():
        return exact
    names = disk_parts(mod_dir, path)
    return mod_dir.joinpath(*names) if names else exact
