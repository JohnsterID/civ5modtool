# Civilization V Mod Info (.modinfo) Schema

## Overview
The .modinfo file is the final mod descriptor used by Civilization V to load and manage mods. It contains all necessary information about the mod, its dependencies, and its content.

## File Format
- XML format with UTF-8 encoding
- Root element: `Mod`
- No namespace required

## Schema Structure

```xml
<?xml version="1.0" encoding="utf-8"?>
<Mod id="{guid}" version="version_number">
    <!-- Basic Properties -->
    <Properties>
        <Name>Required. Display name of the mod</Name>
        <Teaser>Required. Short description</Teaser>
        <Description>Required. Full description</Description>
        <Authors>Required. List of authors</Authors>
        <Homepage>Optional. URL to mod's homepage</Homepage>
        
        <!-- Support Flags (all required, values: 0 or 1) -->
        <SupportsSinglePlayer>Required. Single player support</SupportsSinglePlayer>
        <SupportsMultiplayer>Required. Multiplayer support</SupportsMultiplayer>
        <SupportsHotSeat>Required. Hot seat support</SupportsHotSeat>
        <SupportsMac>Required. Mac support</SupportsMac>
        
        <!-- System Properties (all required, values: 0 or 1) -->
        <AffectsSavedGames>Required. Whether affects save games</AffectsSavedGames>
        <MinCompatibleSaveVersion>Required. Minimum compatible save version</MinCompatibleSaveVersion>
        <ReloadAudioSystem>Required. Whether to reload audio</ReloadAudioSystem>
        <ReloadLandmarkSystem>Required. Whether to reload landmarks</ReloadLandmarkSystem>
        <ReloadStrategicViewSystem>Required. Whether to reload strategic view</ReloadStrategicViewSystem>
        <ReloadUnitSystem>Required. Whether to reload units</ReloadUnitSystem>
        <HideSetupGame>Optional. Whether to hide in setup (0 or 1)</HideSetupGame>
    </Properties>

    <!-- Dependencies -->
    <Dependencies>
        <!-- Game Dependency -->
        <Game minversion="min_ver" maxversion="max_ver" />
        
        <!-- DLC Dependencies -->
        <Dlc id="{guid}" minversion="min_ver" maxversion="max_ver" />
    </Dependencies>

    <!-- References (always included, can be empty) -->
    <References />

    <!-- Blocked Mods -->
    <Blocks>
        <Mod id="{guid}" minversion="min_ver" maxversion="max_ver" title="mod_name" />
    </Blocks>

    <!-- Files -->
    <Files>
        <File import="0/1" md5="MD5_HASH">path/to/file</File>
    </Files>

    <!-- Actions -->
    <Actions>
        <!-- OnModActivated Actions -->
        <OnModActivated>
            <UpdateDatabase>path/to/sql/or/xml</UpdateDatabase>
            <SetDllPath>path/to/dll</SetDllPath>
        </OnModActivated>
        
        <!-- Other Action Sets -->
        <OnGetDLLPath>
            <SetDllPath>path/to/dll</SetDllPath>
        </OnGetDLLPath>
    </Actions>

    <!-- Entry Points -->
    <EntryPoints>
        <EntryPoint type="entry_type" file="path/to/file">
            <Name>Optional. Display name</Name>
            <Description>Optional. Description</Description>
        </EntryPoint>
    </EntryPoints>
</Mod>
```

## Required Root Attributes
1. `id`: GUID - Unique identifier of the mod
2. `version`: String - Version number of the mod

## Required Properties
1. Core Properties:
   - `Name`: String - Display name
   - `Teaser`: String - Short description
   - `Description`: String - Full description
   - `Authors`: String - Author list

2. Support Flags (all values 0 or 1):
   - `SupportsSinglePlayer`
   - `SupportsMultiplayer`
   - `SupportsHotSeat`
   - `SupportsMac`

3. System Properties (all values 0 or 1):
   - `AffectsSavedGames`
   - `MinCompatibleSaveVersion`
   - `ReloadAudioSystem`
   - `ReloadLandmarkSystem`
   - `ReloadStrategicViewSystem`
   - `ReloadUnitSystem`

## Optional Properties
1. `Homepage`: String - URL
2. `HideSetupGame`: Integer (0 or 1)

## Dependencies Section
1. Game dependency (if present):
   - `minversion`: String - Minimum game version
   - `maxversion`: String - Maximum game version

2. DLC dependencies (if any):
   - `id`: GUID - DLC identifier
   - `minversion`: String - Minimum version
   - `maxversion`: String - Maximum version

## Files Section
Each `File` element requires:
1. `import`: Integer (0 or 1) - Whether to import into VFS
2. `md5`: String - MD5 hash (only for import="1")
3. Text content: Path to file (Windows-style paths)

## Actions Section
Organized by action sets (e.g., "OnModActivated", "OnGetDLLPath"):
1. `UpdateDatabase`: Path to SQL or XML file
2. `SetDllPath`: Path to DLL file

## Entry Points Section
Each `EntryPoint` requires:
1. `type`: String - Type of entry point
2. `file`: String - Path to file
Optional elements:
1. `Name`: String - Display name
2. `Description`: String - Description

## Property Order
The Properties section should maintain this order:
1. `Name`
2. `Teaser`
3. `Description`
4. `Authors`
5. `Homepage`
6. `SupportsSinglePlayer`
7. `SupportsMultiplayer`
8. `SupportsHotSeat`
9. `SupportsMac`
10. `AffectsSavedGames`
11. `MinCompatibleSaveVersion`
12. `HideSetupGame` (if present)
13. `ReloadAudioSystem`
14. `ReloadLandmarkSystem`
15. `ReloadStrategicViewSystem`
16. `ReloadUnitSystem`

## File Naming Convention
The .modinfo file name should include the mod's name and version:
```
Mod Name (v X).modinfo
```

Example:
```
Community Patch (v 139).modinfo
```

Optional prefix numbers (e.g., "(1) ") may be included in the mod name if needed for load order:
```
(1) Community Patch (v 139).modinfo
```

## Notes
- All paths should use Windows-style backslashes
- GUIDs should be lowercase and enclosed in curly braces
- File paths are relative to the mod's root directory
- MD5 hashes should be uppercase
- Boolean values are represented as "0" or "1"
- The `References` section is always included but typically empty
- Version numbers typically follow semantic versioning
- Files with `import="1"` must have valid MD5 hashes