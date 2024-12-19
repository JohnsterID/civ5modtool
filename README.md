# Civilization V Mod Tools

A Python package for working with Civilization V mod files (.modinfo, .civ5proj, .civ5sln).

## Features

1. Convert between .modinfo and .civ5proj formats
2. Create/update .civ5sln files when saving .civ5proj files
3. Handle multiple projects in a solution
4. Preserve existing solution settings when updating
5. Maintain correct file naming conventions:
   - .modinfo files include version: `Mod Name (v X).modinfo`
   - .civ5proj/.civ5sln files use base name: `Mod Name.civ5proj`

## Installation

```bash
pip install .
```

## Usage

### Command Line

1. Convert modinfo to civ5proj and create solution:
```bash
# Input: "(1) Community Patch (v 139).modinfo"
# Creates: "Community Patch.civ5proj" and "Community Patch.civ5sln"
modtools modinfo2proj "(1) Community Patch (v 139).modinfo"
```

2. Convert without creating solution:
```bash
# Only creates: "Community Patch.civ5proj"
modtools modinfo2proj --no-solution "(1) Community Patch (v 139).modinfo"
```

3. Convert civ5proj to modinfo:
```bash
# Input: "Community Patch.civ5proj"
# Creates: "Community Patch (v 139).modinfo"
modtools proj2modinfo "Community Patch.civ5proj"
```

4. Validate a mod file:
```bash
# Works with any mod file format
modtools validate "Community Patch.civ5proj"
modtools validate "Community Patch (v 139).modinfo"
```

5. Update MD5 hashes in modinfo:
```bash
# Updates file hashes in the modinfo file
modtools update-md5 "Community Patch (v 139).modinfo"
```

### As a Library

```python
from modtools.core.models import ModProject
from pathlib import Path

# Load a .modinfo file
project = ModProject.from_modinfo(Path("My Mod (v 1).modinfo"))

# Save as .civ5proj with solution
# This will create "My Mod.civ5proj" and "My Mod.civ5sln"
project.write_civ5proj(Path("output.civ5proj"), create_solution=True)

# Load a .civ5proj file
project = ModProject.from_civ5proj(Path("My Mod.civ5proj"))

# Save as .modinfo
project.write_modinfo(Path("My Mod (v 1).modinfo"), Path("."))
```

## Development

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Run tests:
```bash
python -m pytest tests/
```

## License

GPLv3
