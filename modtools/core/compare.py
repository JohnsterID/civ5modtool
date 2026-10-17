"""Semantic comparison of two mods (.modinfo or .civ5proj, in any combination).

Formatting, file order and "/" vs "\\" are ignored; properties, associations,
the file list (path, import flag, and MD5 when both sides carry one),
actions (in order within each set) and entry points are compared.
"""
from pathlib import Path
from typing import List

from .models import ModProject

PROPERTIES = ("name", "mod_guid", "version", "teaser", "description", "authors", "special_thanks", "homepage",
              "hide_setup_game", "affects_saves", "min_save_version", "supports_singleplayer",
              "supports_multiplayer", "supports_hotseat", "supports_mac", "reload_audio", "reload_landmark",
              "reload_strategic_view", "reload_unit")


def load(path: Path) -> ModProject:
    if path.suffix.lower() == ".civ5proj":
        return ModProject.from_civ5proj(path)
    return ModProject.from_modinfo(path)


def _norm(path: str) -> str:
    return path.replace("\\", "/").strip().lower()


def compare_projects(a: ModProject, b: ModProject) -> List[str]:
    diffs = []
    for prop in PROPERTIES:
        va, vb = getattr(a, prop), getattr(b, prop)
        if isinstance(va, str):
            va, vb = va.strip(), vb.strip()
            if prop == "mod_guid":
                va, vb = va.strip("{}").lower(), vb.strip("{}").lower()
        if va != vb:
            diffs.append(f"{prop}: {va!r} != {vb!r}")

    for kind in ("dependencies", "references", "blockers"):
        key = lambda x: (x.type, x.id.strip("{}").lower(), x.min_version, x.max_version)  # noqa: E731
        sa, sb = {key(x) for x in getattr(a, kind)}, {key(x) for x in getattr(b, kind)}
        for item in sorted(sa - sb):
            diffs.append(f"{kind}: only in first: {item}")
        for item in sorted(sb - sa):
            diffs.append(f"{kind}: only in second: {item}")

    fa, fb = {_norm(f.path): f for f in a.files}, {_norm(f.path): f for f in b.files}
    for path in sorted(set(fa) - set(fb)):
        diffs.append(f"files: only in first: {fa[path].path}")
    for path in sorted(set(fb) - set(fa)):
        diffs.append(f"files: only in second: {fb[path].path}")
    for path in sorted(set(fa) & set(fb)):
        x, y = fa[path], fb[path]
        if x.import_to_vfs != y.import_to_vfs:
            diffs.append(f"files: import flag differs: {x.path} ({int(x.import_to_vfs)} != {int(y.import_to_vfs)})")
        if x.md5 and y.md5 and x.md5.upper() != y.md5.upper():
            diffs.append(f"files: md5 differs: {x.path}")

    act = lambda p: [(x.action_set, x.action_type, _norm(x.filename)) for x in p.actions]  # noqa: E731
    if sorted(act(a)) != sorted(act(b)):
        only_a = [x for x in act(a) if x not in act(b)]
        only_b = [x for x in act(b) if x not in act(a)]
        diffs += [f"actions: only in first: {x}" for x in only_a] + [f"actions: only in second: {x}" for x in only_b]
    elif act(a) != act(b):
        diffs.append("actions: same actions in a different order (database updates run in that order)")

    ep = lambda p: sorted((x.type, _norm(x.file), x.name, x.description) for x in p.entry_points)  # noqa: E731
    if ep(a) != ep(b):
        diffs += [f"entry points: only in first: {x}" for x in ep(a) if x not in ep(b)]
        diffs += [f"entry points: only in second: {x}" for x in ep(b) if x not in ep(a)]
    return diffs
