"""Refresh the MD5 attributes of an existing .modinfo in place.

Only the md5="..." values change (one is added to a <File> that has none);
every other byte - order, formatting, BOM, line endings, unknown elements -
stays as it was. The mod folder is the .modinfo's folder.
"""
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
from typing import List
import re

from .xmltext import md5_of, mod_file_path

_FILE = re.compile(r"(<File\b)([^>]*)(>)([^<]*)(</File>)")
_MD5 = re.compile(r'(\bmd5\s*=\s*)(["\'])([^"\']*)\2', re.I)


@dataclass
class Md5Report:
    changed: List[str] = field(default_factory=list)   # stale or missing md5 attribute
    missing: List[str] = field(default_factory=list)   # listed but not on disk
    unchanged: int = 0

    @property
    def clean(self) -> bool:
        return not self.changed and not self.missing


def update_md5(modinfo: Path, check_only: bool = False, mod_dir: Path = None) -> Md5Report:
    raw = modinfo.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw[3:].decode("utf-8") if bom else raw.decode("utf-8")
    mod_dir = mod_dir or modinfo.parent
    report = Md5Report()

    def fix(m):
        start, attrs, gt, path_text, end = m.groups()
        rel = unescape(path_text).strip()
        disk = mod_file_path(mod_dir, rel)
        if not disk.is_file():
            report.missing.append(rel)
            return m.group(0)
        actual = md5_of(disk)
        old = _MD5.search(attrs)
        if old and old.group(3).upper() == actual:
            report.unchanged += 1
            return m.group(0)
        report.changed.append(rel)
        if old:
            attrs = attrs[:old.start(3)] + actual + attrs[old.end(3):]
        else:
            attrs = f' md5="{actual}"' + attrs
        return start + attrs + gt + path_text + end

    new_text = _FILE.sub(fix, text)
    if not check_only and new_text != text:
        modinfo.write_bytes((b"\xef\xbb\xbf" if bom else b"") + new_text.encode("utf-8"))
    return report
