# ModBuddy builds of the test mods

`<variant>.modinfo` is what ModBuddy's own build (Civ5 SDK) writes for the test mod
`tests.helpers.make_variant(folder, "<variant>")`. `test_modinfo.TestModBuddyBuilds` checks that
`--style modbuddy` writes the same bytes. The mods and their files are this project's own test data.

Rebuild or check them on Windows with the Civ5 SDK installed:

```bash
python tools/modbuddy_refs.py           # writes tests/data/modbuddy/*.modinfo
python tools/modbuddy_refs.py --check   # exit 1 if a build differs
```
