# Civilization V Project (.civ5proj) Schema

## Overview
The .civ5proj file is a project file that defines a Civilization V mod, including its properties, dependencies, and content files. It follows a modified version of the MSBuild project file format.

## File Format
- XML format with UTF-8 encoding
- Root element: `Project` with namespace `xmlns="http://schemas.microsoft.com/developer/msbuild/2003"`

## Schema Structure

```xml
<?xml version="1.0" encoding="utf-8"?>
<Project DefaultTargets="Deploy" ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
    <PropertyGroup>
        <!-- Basic Mod Properties -->
        <Configuration>Optional. Build configuration (e.g., "Default")</Configuration>
        <ProjectGuid>Required. A unique GUID for the project</ProjectGuid>
        <Name>Required. The display name of the mod</Name>
        <Guid>Required. The mod's unique identifier GUID</Guid>
        <ModVersion>Required. The version number of the mod</ModVersion>
        <Stability>Optional. Stability status (e.g., "Stable", "Beta")</Stability>
        <Teaser>Required. Short description of the mod</Teaser>
        <Description>Required. Full description of the mod</Description>
        <Authors>Required. List of mod authors</Authors>
        <SpecialThanks>Optional. Acknowledgments</SpecialThanks>
        <Homepage>Optional. URL to mod's homepage</Homepage>
        
        <!-- Compatibility Flags -->
        <AffectsSavedGames>Required. Boolean. Whether the mod affects save games</AffectsSavedGames>
        <MinCompatibleSaveVersion>Required. Minimum save game version compatible</MinCompatibleSaveVersion>
        <SupportsSinglePlayer>Required. Boolean</SupportsSinglePlayer>
        <SupportsMultiplayer>Required. Boolean</SupportsMultiplayer>
        <SupportsHotSeat>Required. Boolean</SupportsHotSeat>
        <SupportsMac>Required. Boolean</SupportsMac>
        
        <!-- System Flags -->
        <ReloadUnitSystem>Required. Boolean</ReloadUnitSystem>
        <ReloadLandmarkSystem>Required. Boolean</ReloadLandmarkSystem>
        <ReloadStrategicViewSystem>Required. Boolean</ReloadStrategicViewSystem>
        <HideSetupGame>Optional. Boolean. Whether to hide in setup</HideSetupGame>
    </PropertyGroup>

    <!-- Dependencies -->
    <ModDependencies>
        <Association>
            <Type>Required. Type of dependency ("Game", "Dlc", "Mod")</Type>
            <Name>Required. Name of the dependency</Name>
            <Id>Required. GUID of the dependency</Id>
            <MinVersion>Optional. Minimum version required</MinVersion>
            <MaxVersion>Optional. Maximum version supported</MaxVersion>
        </Association>
    </ModDependencies>

    <!-- Mod Blockers (Incompatible Mods) -->
    <ModBlockers>
        <Association>
            <Type>Required. Always "Mod"</Type>
            <Name>Required. Name of blocked mod</Name>
            <Id>Required. GUID of blocked mod</Id>
            <MinVersion>Optional. Minimum version blocked</MinVersion>
            <MaxVersion>Optional. Maximum version blocked</MaxVersion>
        </Association>
    </ModBlockers>

    <!-- Mod Actions -->
    <ModActions>
        <Action>
            <Set>Required. When action occurs (e.g., "OnModActivated")</Set>
            <Type>Required. Type of action (e.g., "UpdateDatabase", "SetDllPath")</Type>
            <FileName>Required. Path to the file for this action</FileName>
        </Action>
    </ModActions>

    <!-- Content Files -->
    <ItemGroup>
        <Content Include="path/to/file">
            <SubType>Optional. File type hint (e.g., "Lua")</SubType>
            <ImportIntoVFS>Required. Boolean. Whether to import into game's VFS</ImportIntoVFS>
        </Content>
    </ItemGroup>

    <!-- Entry Points -->
    <ModContent>
        <Content>
            <Type>Required. Type of entry point (e.g., "InGameUIAddin")</Type>
            <Name>Optional. Display name</Name>
            <Description>Optional. Description</Description>
            <FileName>Required. Path to entry point file</FileName>
        </Content>
    </ModContent>
</Project>
```

## Required Properties
1. Core Properties:
   - `ProjectGuid`: GUID - Project's unique identifier
   - `Name`: String - Mod's display name
   - `Guid`: GUID - Mod's unique identifier
   - `ModVersion`: String - Version number
   - `Teaser`: String - Short description
   - `Description`: String - Full description
   - `Authors`: String - Author list

2. Compatibility Flags (all Boolean):
   - `AffectsSavedGames`
   - `MinCompatibleSaveVersion`
   - `SupportsSinglePlayer`
   - `SupportsMultiplayer`
   - `SupportsHotSeat`
   - `SupportsMac`

3. System Flags (all Boolean):
   - `ReloadUnitSystem`
   - `ReloadLandmarkSystem`
   - `ReloadStrategicViewSystem`

## Optional Properties
1. `Configuration`: String - Build configuration
2. `Stability`: String - Stability status
3. `SpecialThanks`: String - Acknowledgments
4. `Homepage`: String - URL
5. `HideSetupGame`: Boolean

## Dependencies and Blockers
Each `Association` under `ModDependencies` or `ModBlockers` requires:
1. `Type`: String - Type of dependency
2. `Name`: String - Name of dependency
3. `Id`: GUID - Unique identifier
4. Optional version constraints:
   - `MinVersion`: String
   - `MaxVersion`: String

## Actions
Each `Action` requires:
1. `Set`: String - When action occurs
2. `Type`: String - Type of action
3. `FileName`: String - Path to file

## Content Files
Each `Content` requires:
1. `Include`: Attribute - Path to file
2. `ImportIntoVFS`: Boolean - Whether to import into game's VFS
3. Optional `SubType`: String - File type hint

## Entry Points
Each `Content` under `ModContent` requires:
1. `Type`: String - Type of entry point
2. `FileName`: String - Path to file
Optional:
1. `Name`: String - Display name
2. `Description`: String - Description

## File Naming Convention
The .civ5proj file name should be the base name of the mod (without version number):
```
Mod Name.civ5proj
```

Example:
```
Community Patch.civ5proj
```

Note: Even if the corresponding .modinfo file has a prefix number or version (e.g., "(1) Community Patch (v 139).modinfo"), the .civ5proj file should use only the base name.

## Notes
- All paths should use Windows-style backslashes
- GUIDs should be lowercase and enclosed in curly braces
- File paths are relative to the project file's location
- Boolean values should be "true" or "false" (case-insensitive)
- Version numbers typically follow semantic versioning