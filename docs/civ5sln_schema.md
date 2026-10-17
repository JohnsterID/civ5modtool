# .civ5sln

ModBuddy's solution, a Visual Studio 2010 solution file. UTF-8 with BOM, CRLF, an empty first line, tabs. One
`Project` per `.civ5proj`. The project type GUID is ModBuddy's; the project GUID is the `.civ5proj`'s
`ProjectGuid`, upper case. modtools writes it byte-identical to VP's `Community Patch.civ5sln`.

```
(empty line)
Microsoft Visual Studio Solution File, Format Version 11.00
# ModBuddy Solution File, Format Version 11.00
Project("{F5FC21B5-7CC2-458A-ABBA-992F515BBA20}") = "Community Patch", "Community Patch.civ5proj", "{0D66D522-B624-4BC5-ACFE-15A0C5B729F4}"
EndProject
Global
	GlobalSection(SolutionConfigurationPlatforms) = preSolution
		Default|x86 = Default|x86
		Deploy Only|x86 = Deploy Only|x86
		Package Only|x86 = Package Only|x86
	EndGlobalSection
	GlobalSection(ProjectConfigurationPlatforms) = postSolution
		{0D66D522-B624-4BC5-ACFE-15A0C5B729F4}.Default|x86.ActiveCfg = Default|x86
		{0D66D522-B624-4BC5-ACFE-15A0C5B729F4}.Default|x86.Build.0 = Default|x86
		{0D66D522-B624-4BC5-ACFE-15A0C5B729F4}.Deploy Only|x86.ActiveCfg = Deploy Only|x86
		{0D66D522-B624-4BC5-ACFE-15A0C5B729F4}.Deploy Only|x86.Build.0 = Deploy Only|x86
		{0D66D522-B624-4BC5-ACFE-15A0C5B729F4}.Package Only|x86.ActiveCfg = Package Only|x86
		{0D66D522-B624-4BC5-ACFE-15A0C5B729F4}.Package Only|x86.Build.0 = Package Only|x86
	EndGlobalSection
	GlobalSection(SolutionProperties) = preSolution
		HideSolutionNode = FALSE
	EndGlobalSection
EndGlobal
```

- **Project names:** each project's name is its file name without `.civ5proj` ("Community Patch"), not the
  mod name ("(1) Community Patch").
- **Saving a project:** `modinfo2proj` and the GUI create the solution next to the project, or add or refresh
  the project in an existing one, matched by file name or GUID. Other projects in it are kept.
- **`validate`:** checks that each project file exists and that its `ProjectGuid` matches the solution.
