# .modinfo

The file the game loads. Two sources describe it here:

- **Written by:** ModBuddy's build, and Vox Populi's `scripts/generate_modinfo.py`, which reproduces it. modtools
  writes the same bytes.
- **Read by:** `Modding::PackageManager::LoadModInfo` in the game (IDA, Linux `Civ5XP` with symbols; the
  Windows EXEs share the code). It copies everything into the modding database
  (`Mods`, `ModProperties`, `ModRelationships`, `DlcRelationships`, `GameVersionRelationships`, `ModFiles`,
  `ModActions`, `ModEntryPoints`).

## Layout (as written)

UTF-8 with BOM, two-space indent. ModBuddy: CRLF, no newline at the end. `generate_modinfo.py`: LF, newline at
the end (modtools `--style modbuddy` / `--style vp`).

```xml
<?xml version="1.0" encoding="utf-8"?>
<Mod id="d1b6328c-ff44-4b0d-aad7-c657f83610cd" version="151">
  <Properties>
    <Name>(1) Community Patch</Name>
    <Teaser>...</Teaser>
    <Description>...</Description>
    <Authors>...</Authors>
    <SpecialThanks>...</SpecialThanks>            <!-- only if not empty -->
    <HideSetupGame>0</HideSetupGame>
    <Homepage>...</Homepage>                      <!-- only if not empty -->
    <AffectsSavedGames>1</AffectsSavedGames>
    <MinCompatibleSaveVersion>151</MinCompatibleSaveVersion>   <!-- only if not 0 -->
    <SupportsSinglePlayer>1</SupportsSinglePlayer>
    <SupportsMultiplayer>1</SupportsMultiplayer>
    <SupportsHotSeat>1</SupportsHotSeat>
    <SupportsMac>1</SupportsMac>
    <ReloadAudioSystem>0</ReloadAudioSystem>
    <ReloadLandmarkSystem>1</ReloadLandmarkSystem>
    <ReloadStrategicViewSystem>1</ReloadStrategicViewSystem>
    <ReloadUnitSystem>1</ReloadUnitSystem>
  </Properties>
  <Dependencies>                                  <!-- <Dependencies /> when empty; same for the next two -->
    <Game minversion="1.0.3.124" maxversion="1.0.3.999" />
    <Dlc id="7459BA32-5764-44ae-8E95-01AD0E0EFD48" minversion="0" maxversion="999" />
    <Mod id="..." minversion="151" maxversion="999" title="(1) Community Patch" />
  </Dependencies>
  <References>
    <Mod id="..." minversion="17" maxversion="999" title="(2) Vox Populi" />
  </References>
  <Blocks>
    <Mod id="..." minversion="0" maxversion="999" title="..." />
  </Blocks>
  <Files>
    <File md5="0123...CDEF" import="1">LUA/Foo.lua</File>        <!-- every file has an md5 -->
    <File md5="..." import="0">Database Changes/Foo.sql</File>
  </Files>
  <Actions>                                       <!-- grouped by set, in first-use order -->
    <OnModActivated>
      <UpdateDatabase>Database Changes/Foo.sql</UpdateDatabase>
    </OnModActivated>
    <OnGetDLLPath>
      <SetDllPath>CvGameCore_Expansion2.dll</SetDllPath>
    </OnGetDLLPath>
  </Actions>
  <EntryPoints>
    <EntryPoint type="InGameUIAddin" file="LUA/Foo.xml">
      <Name>Foo</Name>
      <Description>...</Description>
    </EntryPoint>
  </EntryPoints>
</Mod>
```

- File paths and entry point `file`s use `/`. Action file names are written as the project had them (VP mixes `/`
  and `\`).
- Text and attribute values escape `&`, `<`, `>` and `"`.
- The file name is `<Name> (v <version>).modinfo`.

## What the game reads

| Item | How the game reads it |
|---|---|
| `<Mod id>` | text. |
| `<Mod version>` | integer. If it is not an integer ≥ 0 the mod is not recorded. |
| `<Properties>` | generic: every child is stored as name/value text. The EXE looks up `SupportsSinglePlayer`, `SupportsMultiplayer`, `AffectsSavedGames`, `Reload*System`, `Name`, `Teaser`, and `MinCompatibleSaveVersion` (SQL `Value <= ?` for save compatibility); the UI Lua reads others with `Modding.GetModProperty`. |
| Booleans | `t…`/`T…` true, `f…`/`F…` false, otherwise a number (`FXmlNVPair::GetVal(bool&)`), so `1`/`0` and `true`/`false` both work. |
| `Dependencies` / `References` / `Blocks` | children `Mod` (`id`, `minversion`, `maxversion` as integers, `title`), `Dlc` (`id`, integer versions), `Game` (`minversion`/`maxversion` as text). A missing `maxversion` means no upper limit. |
| `<File>` | text = path (stored as written, plus a lower-cased `EvaluatedPath` under the mod folder, 260-character buffers); `md5` stored as text; `import` boolean, **default 1** when absent. |
| `<Actions>` | each child is a set (`Location`), each grandchild an action (`Action`, text = `Param1`). Registered action types: `UpdateDatabase`, `UpdateUserData`, `ExecuteScript`, `SetDllPath` (`CvModdingFrameworkAppSide::Initialize`). Sets used: `OnModActivated`, `OnGetDLLPath`, `OnCreateModUserData`. |
| `<EntryPoints>` | `type`, `file`, `Name`, `Description`. Types looked up: `InGameUIAddin`, `DiplomacyUIAddin`, `CityViewUIAddin`, `Custom` (UI Lua), `Map`, `MapScript` (EXE). `Map`/`MapScript` are joined to the files by `ModEntryPoints.File = ModFiles.Path`, an exact match. |

## MD5s

The MD5s are only compared by `Modding::Installer::CanInstallMod`, when a packaged `.civ5mod` (Steam
Workshop / mod browser) is installed: each file's MD5 is computed and compared case-insensitively, and the
first mismatch aborts the install with error 16. A mod placed in the MODS folder (as VP's installer does) is
read by `LoadModInfo` without any MD5 check. `Modding.GetEvaluatedFilePath` returns the stored MD5 to Lua.

## Paths on Civ5XP (Linux)

`LoadModInfo` builds each file's `EvaluatedPath` by lower-casing the `<File>` text and appending it to the mod
folder with `PathAppendW`. Civ5XP's `PathAppendW` shim joins with `\` and does nothing else. Every file open
(`CreateFileW`, `_wfopen`, ...) then goes through `DOS2POSIXPathW` → `DOS2MacPath`:

- **Separators:** each `\` becomes `/`.
- **Absolute paths:** in an absolute path, everything after `Aspyr/Sid Meier's Civilization 5/MODS` (or after
  `steamassets`) is lower-cased.
- **Relative paths:** these are lower-cased entirely.

So under `$XDG_DATA_HOME/Aspyr/Sid Meier's Civilization 5/MODS` (default `~/.local/share/...`) every folder and
file name of a mod must be lower case on disk; the `.modinfo` text can keep its case.
