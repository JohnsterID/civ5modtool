# .civ5proj

ModBuddy's project: an MSBuild file (`xmlns="http://schemas.microsoft.com/developer/msbuild/2003"`), UTF-8 with
BOM, CRLF. The layout below is the one in Vox Populi's six projects, which modtools writes and reads.

```xml
<?xml version="1.0" encoding="utf-8"?>
<Project DefaultTargets="Deploy" ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <PropertyGroup>
    <Configuration Condition=" '$(Configuration)' == '' ">Default</Configuration>
    <ProjectGuid>{0d66d522-b624-4bc5-acfe-15a0c5b729f4}</ProjectGuid>
    <Name>(1) Community Patch</Name>
    <Guid>d1b6328c-ff44-4b0d-aad7-c657f83610cd</Guid>     <!-- the mod id, no braces -->
    <ModVersion>151</ModVersion>
    <Stability>Stable</Stability>
    <Teaser>...</Teaser>
    <Description>...</Description>
    <Authors>...</Authors>
    <SpecialThanks>...</SpecialThanks>
    <Categories>$Categories$</Categories>
    <AffectsSavedGames>true</AffectsSavedGames>
    <MinCompatibleSaveVersion>151</MinCompatibleSaveVersion>
    <SupportsSinglePlayer>true</SupportsSinglePlayer>
    <SupportsMultiplayer>true</SupportsMultiplayer>
    <SupportsHotSeat>true</SupportsHotSeat>
    <SupportsMac>true</SupportsMac>
    <ReloadUnitSystem>true</ReloadUnitSystem>
    <ReloadLandmarkSystem>true</ReloadLandmarkSystem>
    <ReloadStrategicViewSystem>true</ReloadStrategicViewSystem>
    <ReloadAudioSystem>false</ReloadAudioSystem>
    <HideSetupGame>false</HideSetupGame>
    <Homepage>...</Homepage>
    <AssemblyName>Community Patch</AssemblyName>
    <RootNamespace>Community Patch</RootNamespace>
    <ModReferences>   <Association>...</Association> </ModReferences>
    <ModDependencies>
      <Association>
        <Type>Dlc</Type>                         <!-- Game, Dlc or Mod -->
        <Name>Babylon (Nebuchadnezzar II)</Name> <!-- <Name /> when empty -->
        <Id>7459BA32-5764-44ae-8E95-01AD0E0EFD48</Id>
        <MinVersion>0</MinVersion>
        <MaxVersion>999</MaxVersion>
      </Association>
    </ModDependencies>
    <ModBlockers>     <Association>...</Association> </ModBlockers>
    <ModActions>
      <Action>
        <Set>OnModActivated</Set>
        <Type>UpdateDatabase</Type>
        <FileName>Database Changes\Foo.sql</FileName>
      </Action>
    </ModActions>
    <ModContent>
      <Content>                                  <!-- Squads writes <Content xmlns="">; both are read -->
        <Type>InGameUIAddin</Type>
        <Name>Foo</Name>
        <Description>...</Description>
        <FileName>LUA/Foo.xml</FileName>
      </Content>
    </ModContent>
  </PropertyGroup>
  <PropertyGroup Condition=" '$(Configuration)' == 'Default' ">
    <OutputPath>.</OutputPath>
  </PropertyGroup>
  <PropertyGroup Condition=" '$(Configuration)' == 'Package Only' ">
    <PackageMod>true</PackageMod>
    <DeployMod>false</DeployMod>
  </PropertyGroup>
  <PropertyGroup Condition=" '$(Configuration)' == 'Deploy Only' ">
    <PackageMod>false</PackageMod>
    <DeployMod>true</DeployMod>
  </PropertyGroup>
  <ItemGroup>
    <Folder Include="LUA" />
  </ItemGroup>
  <ItemGroup>
    <Content Include="LUA\Foo.lua">
      <SubType>Lua</SubType>                     <!-- ModBuddy writes Lua for every file type -->
      <ImportIntoVFS>True</ImportIntoVFS>        <!-- True / False -->
    </Content>
  </ItemGroup>
  <Import Project="$(MSBuildExtensionsPath)\Firaxis\ModBuddy\Civ5Mod.targets" />
</Project>
```

Notes:

- **Mod sections:** `ModReferences`, `ModDependencies`, `ModBlockers`, `ModActions` and `ModContent` must be
  inside the first `PropertyGroup`. ModBuddy and `generate_modinfo.py` ignore them elsewhere. modtools also
  reads projects that have them at the project root, and `validate` reports that as an error.
- **`ImportIntoVFS`:** `generate_modinfo.py` treats anything but exactly `True` as not imported. modtools
  reads it case-insensitively and `validate` warns about other spellings.
- **Defaults when an element is missing** (`generate_modinfo.py`): `AffectsSavedGames`,
  `SupportsSinglePlayer`, `SupportsMultiplayer` and `SupportsMac` true; `SupportsHotSeat`, `HideSetupGame` and
  `Reload*System` false; `MinCompatibleSaveVersion` 0; `ModVersion` 1.
- **`.modinfo` → `.civ5proj` (modtools):** a `.modinfo` carries no `ProjectGuid`, folders, `SubType` or
  `AssemblyName`. modtools uses a stable GUID derived from the mod id, the folders of the listed files,
  `Lua`, and the name without its `(N) ` prefix.
