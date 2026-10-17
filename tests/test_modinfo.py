"""The .modinfo reader and writer."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from modtools.core.modinfo import modinfo_text, read_modinfo, write_modinfo
from modtools.core.models import FileEntry, ModProject
from modtools.core.xmltext import parse_bool
from tests.helpers import FILES, make_mod

DATA = Path(__file__).parent / "data"
CP139 = DATA / "(1) Community Patch (v 139).modinfo"


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest().upper()


class TestWriter(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.project = make_mod(self.tmp)

    def test_exact_text(self):
        text, missing = modinfo_text(self.project, self.tmp)
        self.assertEqual(missing, [])
        m = {k: md5(v) for k, v in FILES.items()}
        self.assertEqual(text, f"""<?xml version="1.0" encoding="utf-8"?>
<Mod id="0f0e0d0c-0b0a-4908-8706-050403020100" version="3">
  <Properties>
    <Name>(7) Test Mod</Name>
    <Teaser>A &lt;test&gt; &amp; &quot;quote&quot;</Teaser>
    <Description>Line one
Line two</Description>
    <Authors>Me</Authors>
    <SpecialThanks>You</SpecialThanks>
    <HideSetupGame>0</HideSetupGame>
    <Homepage>https://example.com/?a=1&amp;b=2</Homepage>
    <AffectsSavedGames>1</AffectsSavedGames>
    <MinCompatibleSaveVersion>2</MinCompatibleSaveVersion>
    <SupportsSinglePlayer>1</SupportsSinglePlayer>
    <SupportsMultiplayer>1</SupportsMultiplayer>
    <SupportsHotSeat>1</SupportsHotSeat>
    <SupportsMac>1</SupportsMac>
    <ReloadAudioSystem>0</ReloadAudioSystem>
    <ReloadLandmarkSystem>0</ReloadLandmarkSystem>
    <ReloadStrategicViewSystem>0</ReloadStrategicViewSystem>
    <ReloadUnitSystem>1</ReloadUnitSystem>
  </Properties>
  <Dependencies>
    <Game minversion="1.0.3.124" maxversion="1.0.3.999" />
    <Dlc id="7459BA32-5764-44ae-8E95-01AD0E0EFD48" minversion="0" maxversion="999" />
    <Mod id="d1b6328c-ff44-4b0d-aad7-c657f83610cd" minversion="151" maxversion="999" title="(1) Community Patch" />
  </Dependencies>
  <References>
    <Mod id="8411a7a8-dad3-4622-a18e-fcc18324c799" minversion="17" maxversion="999" title="(2) Vox Populi" />
  </References>
  <Blocks>
    <Mod id="11111111-2222-3333-4444-555555555555" minversion="0" maxversion="999" title="Old Mod" />
  </Blocks>
  <Files>
    <File md5="{m['Lua/Main.lua']}" import="1">Lua/Main.lua</File>
    <File md5="{m['SQL/Changes.sql']}" import="0">SQL/Changes.sql</File>
    <File md5="{m['Text/en_US/Text.xml']}" import="0">Text/en_US/Text.xml</File>
    <File md5="{m['UI/Addin.xml']}" import="1">UI/Addin.xml</File>
    <File md5="{m['Maps/Small & Wet.lua']}" import="1">Maps/Small &amp; Wet.lua</File>
  </Files>
  <Actions>
    <OnModActivated>
      <UpdateDatabase>SQL/Changes.sql</UpdateDatabase>
      <UpdateDatabase>Text\\en_US\\Text.xml</UpdateDatabase>
    </OnModActivated>
  </Actions>
  <EntryPoints>
    <EntryPoint type="InGameUIAddin" file="UI/Addin.xml">
      <Name>Addin</Name>
      <Description>The addin</Description>
    </EntryPoint>
    <EntryPoint type="MapScript" file="Maps/Small &amp; Wet.lua">
      <Name>Small &amp; Wet</Name>
      <Description></Description>
    </EntryPoint>
  </EntryPoints>
</Mod>
""")

    def test_empty_sections_and_omitted_properties(self):
        p = ModProject(name="Bare", mod_guid="0f0e0d0c-0b0a-4908-8706-050403020100")
        text, _ = modinfo_text(p, self.tmp)
        for line in ("  <Dependencies />", "  <References />", "  <Blocks />", "  <Files>\n  </Files>"):
            self.assertIn(line, text)
        for absent in ("SpecialThanks", "Homepage", "MinCompatibleSaveVersion", "<Actions>", "<EntryPoints>"):
            self.assertNotIn(absent, text)  # ModBuddy leaves them out when empty / "0"

    def test_styles(self):
        out = self.tmp / "vp.modinfo"
        write_modinfo(self.project, out, self.tmp, "vp")
        raw = out.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf<?xml"))
        self.assertNotIn(b"\r\n", raw)
        self.assertTrue(raw.endswith(b"</Mod>\n"))
        write_modinfo(self.project, out, self.tmp, "modbuddy")
        raw = out.read_bytes()
        self.assertTrue(raw.endswith(b"</Mod>"))
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"))

    def test_missing_files(self):
        self.project.files.append(FileEntry("Gone.lua", True))
        self.project.files.append(FileEntry("Known.lua", True, md5="ABC"))
        text, missing = modinfo_text(self.project, self.tmp)
        self.assertEqual(len(missing), 2)
        self.assertNotIn("Gone.lua", text)  # no MD5 to write: left out, as ModBuddy does
        self.assertIn('<File md5="ABC" import="1">Known.lua</File>', text)  # keeps the MD5 it was read with


class TestReader(unittest.TestCase):
    def test_roundtrip_is_byte_identical(self):
        tmp = Path(tempfile.mkdtemp())
        project = make_mod(tmp)
        first = tmp / "a.modinfo"
        write_modinfo(project, first, tmp)
        again = tmp / "b.modinfo"
        write_modinfo(read_modinfo(first), again, tmp)
        self.assertEqual(first.read_bytes(), again.read_bytes())

    def test_modbuddy_file_is_reproduced_exactly(self):
        """CP v139's .modinfo was built by ModBuddy; its files are not in tests/data,
        so the writer keeps the MD5s it read."""
        out = Path(tempfile.mkdtemp()) / "cp.modinfo"
        write_modinfo(read_modinfo(CP139), out, CP139.parent, "modbuddy")
        self.assertEqual(out.read_bytes(), CP139.read_bytes())

    def test_cp139_contents(self):
        p = read_modinfo(CP139)
        self.assertEqual((p.name, p.version, p.min_save_version), ("(1) Community Patch", "139", "139"))
        self.assertTrue(p.affects_saves and p.supports_multiplayer and p.supports_hotseat)
        self.assertEqual({d.type for d in p.dependencies}, {"Game", "Dlc"})
        self.assertTrue(all(f.md5 for f in p.files))
        self.assertIn(("OnGetDLLPath", "SetDllPath"), {(a.action_set, a.action_type) for a in p.actions})

    def test_missing_import_means_imported(self):
        """Modding::PackageManager::LoadModInfo defaults import to 1."""
        path = Path(tempfile.mkdtemp()) / "m.modinfo"
        path.write_text('<Mod id="x" version="1"><Properties><Name>N</Name></Properties>'
                        '<Files><File md5="A">a.lua</File><File import="0">b.sql</File></Files></Mod>', encoding="utf-8")
        files = read_modinfo(path).files
        self.assertEqual([f.import_to_vfs for f in files], [True, False])

    def test_parse_bool_like_the_game(self):
        for value, expected in [("1", True), ("0", False), ("true", True), ("False", False), ("T", True),
                                ("yes", None), ("", None), (None, None), ("2", True)]:
            self.assertEqual(parse_bool(value, None), expected, value)


if __name__ == "__main__":
    unittest.main()
