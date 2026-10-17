# Civilization V Mod Tools

Read, convert, check and edit Civilization V mod files: `.modinfo` (what the game loads),
`.civ5proj` and `.civ5sln` (ModBuddy's project and solution). Python 3.9+, standard library only.

The output is byte-identical to the references:

| Command | Reference | Checked by |
|---|---|---|
| `proj2modinfo` (default `--style vp`) | Vox Populi's `scripts/generate_modinfo.py` | `tests/test_vp_repo.py`, all six VP mods (CI, weekly) |
| `proj2modinfo --style modbuddy` | ModBuddy's own build output | `tests/test_modinfo.py`, a ModBuddy-built CP v139 `.modinfo` |
| `modinfo2proj` (`.civ5proj`) | ModBuddy's project layout | VP's six `.modinfo` → `.civ5proj` → `.modinfo` give the same bytes, and the rebuilt project equals VP's own |
| `.civ5sln` | ModBuddy's solution | byte-identical to ModBuddy's `Community Patch.civ5sln` |

For VP's own release, upstream's `generate_modinfo.py` is the tool of record; modtools gives the
same result and adds what that script does not do: converting a published `.modinfo` back into a
ModBuddy project, refreshing MD5s in place, validating, comparing, Civ5XP (Linux) installs, and a GUI.
It runs on Windows and Linux; upstream's script only resolves its `\` paths on Windows.

## Install

```bash
pip install .
```

## Commands

```bash
modtools proj2modinfo "(1) Community Patch"            # folder or .civ5proj; writes "(1) Community Patch (v 151).modinfo"
modtools proj2modinfo "(1)*" "(2)*" --output-dir build  # several projects
modtools modinfo2proj "My Mod (v 3).modinfo"            # writes "My Mod.civ5proj" + "My Mod.civ5sln" next to it
modtools update-md5 "My Mod (v 3).modinfo"              # refresh MD5s in place; --check only reports (exit 1 if stale)
modtools validate "My Mod (v 3).modinfo" "My Mod.civ5proj" "My Mod.civ5sln"
modtools compare "My Mod (v 3).modinfo" "My Mod.civ5proj"
modtools validate --civ5xp "My Mod (v 3).modinfo"       # also check for Civ5XP (Linux)
modtools civ5xp-install "My Mod"                        # copy into Civ5XP's MODS folder, every name lower-cased
modtools gui ["My Mod.civ5proj"]                        # Tkinter editor (also: modtools --gui)
```

Exit status: 0 ok; 1 problems found (validation errors, stale MD5s with `--check`, differences for
`compare`, missing files with `proj2modinfo --strict`); 2 usage or I/O error.

- `proj2modinfo` hashes every listed file. A file missing on disk is left out with a warning, as
  ModBuddy and `generate_modinfo.py` do; `--strict` makes that exit 1.
- `modinfo2proj` rebuilds what a `.modinfo` does not carry the way ModBuddy would: a stable
  `ProjectGuid` derived from the mod id, `Folder` items, `SubType` `Lua`, the three configurations.
  `-o` writes exactly where you say.
- `update-md5` changes only the `md5="..."` values (and adds one where it is missing); order,
  formatting, BOM, line endings and unknown elements stay as they were.
- `validate --packaged` treats MD5 problems as errors (see below); `--strict` exits 1 on warnings too.
- Listed paths are matched to files case-insensitively when the exact case is not on disk, as Windows does,
  so a Windows-cased `.modinfo` still hashes and validates against a lower-cased copy on Linux.

## Civ5XP (Linux)

Civ5XP, Aspyr's Linux build, opens every file through `DOS2POSIXPathW` → `DOS2MacPath`:

- **Separators:** `\` becomes `/`.
- **Case:** in a path containing `Aspyr/Sid Meier's Civilization 5/MODS`, everything after that point is
  lower-cased, both the mod folder and every file in it.

Linux file names are case-sensitive, so a mod works there only if every name under MODS is lower case on
disk. The `.modinfo` can keep its case, because the game lower-cases what it reads.

- **Check:** `validate --civ5xp` reports each listed file whose name on disk is not lower case (an error,
  since Civ5XP will not find it), plus a mod folder name with capitals (a warning).
- **Install:** `civ5xp-install <mod folder>` copies the mod into
  `$XDG_DATA_HOME/Aspyr/Sid Meier's Civilization 5/MODS` (default `~/.local/share/...`; change it with
  `--mods-dir`), with every folder and file name lower-cased. The source is not changed. It refuses names
  that would collide once lower-cased and an existing copy (unless `--replace`); `--dry-run` only reports.
  MD5s are unaffected, because only names change.
- **DLL mods:** Civ5XP runs Linux code, so mods that replace the game core DLL (`SetDllPath`), such as Vox
  Populi's Community Patch, need a Linux build of that DLL. modtools does not provide that.

## What the game actually checks

`validate`'s rules come from the game's own code (IDA, Linux `Civ5XP` with symbols; the Windows EXEs
share it). Details in `modtools/core/validate.py` and `docs/modinfo_schema.md`:

- The mod is only recorded if `<Mod version>` is an integer ≥ 0.
- **MD5s are only compared when a packaged `.civ5mod` is installed** (`Modding::Installer::CanInstallMod`,
  error 16 on a mismatch). Mods in the MODS folder load without any MD5 check, so for them a stale MD5 is a
  warning.
- A `<File>` without `import` counts as `import="1"`.
- Booleans: `t…`/`T…` true, `f…`/`F…` false, otherwise a number, so `1`/`0` and `true`/`false` both work.
- Action types the game runs: `UpdateDatabase`, `UpdateUserData`, `ExecuteScript`, `SetDllPath`; action sets:
  `OnModActivated`, `OnGetDLLPath`, `OnCreateModUserData`. Anything else is ignored.
- Entry point types it looks up: `InGameUIAddin`, `DiplomacyUIAddin`, `CityViewUIAddin`, `Custom`, `Map`,
  `MapScript`. `Map`/`MapScript` entry points are matched to `<Files>` by exact string, so their `file` must
  equal the `<File>` text, same slashes and case.

## As a library

```python
from pathlib import Path
from modtools.core.models import ModProject
from modtools.core.validate import validate_path

project = ModProject.from_civ5proj(Path("Community Patch.civ5proj"))
project.write_modinfo(Path(project.modinfo_filename()))            # style="vp" (default) or "modbuddy"
project.write_civ5proj(Path("Copy.civ5proj"), create_solution=False)
for issue in validate_path(Path("(1) Community Patch (v 151).modinfo")):
    print(issue)
```

Modules: `core.models` (data model), `core.modinfo`, `core.civ5proj`, `core.solution` (readers and
writers), `core.md5`, `core.validate`, `core.compare`, `core.civ5xp`, `cli.main`, `gui.main`.

## Tests

```bash
pip install pytest
python -m pytest tests
VP_REPO=../Community-Patch-DLL python -m pytest tests/test_vp_repo.py   # against a VP checkout (read-only)
```

## License

GPLv3
