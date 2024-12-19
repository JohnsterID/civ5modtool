# Civilization V Solution (.civ5sln) Schema

## Overview
The .civ5sln file is a solution file that contains references to one or more Civilization V mod projects (.civ5proj files). It follows a simplified version of the Visual Studio solution file format.

## File Format
- XML format with UTF-8 encoding
- Root element: `Project` with namespace `xmlns="http://schemas.microsoft.com/developer/msbuild/2003"`

## Schema Structure

```xml
<?xml version="1.0" encoding="utf-8"?>
<Project DefaultTargets="Deploy" ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
    <PropertyGroup>
        <!-- Basic Solution Properties -->
        <Name>Required. The name of the solution</Name>
        <Configuration>Optional. Build configuration (e.g., "Default")</Configuration>
        <ProjectGuid>Required. A unique GUID for the solution</ProjectGuid>
    </PropertyGroup>
    
    <!-- Project References -->
    <ItemGroup>
        <Projects Include="path/to/project.civ5proj">
            <ProjectName>Required. Name of the referenced project</ProjectName>
        </Projects>
        <!-- Multiple project references can be included -->
    </ItemGroup>
</Project>
```

## Required Properties
1. `Name`: String - The name of the solution
2. `ProjectGuid`: GUID - A unique identifier for the solution
3. At least one `Projects` element with:
   - `Include` attribute: Path to .civ5proj file
   - `ProjectName` child element: Name of the referenced project

## Optional Properties
1. `Configuration`: String - Build configuration name (typically "Default")

## Example
```xml
<?xml version="1.0" encoding="utf-8"?>
<Project DefaultTargets="Deploy" ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
    <PropertyGroup>
        <Name>Community Patch</Name>
        <Configuration>Default</Configuration>
        <ProjectGuid>{0d66d522-b624-4bc5-acfe-15a0c5b729f4}</ProjectGuid>
    </PropertyGroup>
    <ItemGroup>
        <Projects Include="Community Patch.civ5proj">
            <ProjectName>Community Patch</ProjectName>
        </Projects>
    </ItemGroup>
</Project>
```

## File Naming Convention
The .civ5sln file name should match the base name of the mod (without version number):
```
Mod Name.civ5sln
```

Example:
```
Community Patch.civ5sln
```

Note: The solution file should have the same base name as its corresponding .civ5proj file, even if the .modinfo file has a prefix number or version (e.g., "(1) Community Patch (v 139).modinfo").

## Notes
- All paths should use Windows-style backslashes
- GUIDs should be lowercase and enclosed in curly braces
- The solution file typically resides in the same directory as its referenced projects