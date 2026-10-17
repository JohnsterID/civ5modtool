"""A small mod folder for the tests."""
from pathlib import Path

from modtools.core.models import Action, Association, EntryPoint, FileEntry, ModProject

FILES = {
    "Lua/Main.lua": b"print('hi')\n",
    "SQL/Changes.sql": b"UPDATE Units SET Moves = 3;\n",
    "Text/en_US/Text.xml": b"<GameData/>\n",
    "UI/Addin.xml": b"<Context/>\n",
    "Maps/Small & Wet.lua": b"-- map\n",
}


def make_mod(folder: Path) -> ModProject:
    for rel, data in FILES.items():
        path = folder.joinpath(*rel.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return ModProject(
        name="(7) Test Mod", mod_guid="0f0e0d0c-0b0a-4908-8706-050403020100", version="3",
        teaser="A <test> & \"quote\"", description="Line one\nLine two", authors="Me",
        special_thanks="You", homepage="https://example.com/?a=1&b=2", min_save_version="2",
        supports_hotseat=True, reload_unit=True,
        dependencies=[Association("Game", "", "", "1.0.3.124", "1.0.3.999"),
                      Association("Dlc", "Babylon", "7459BA32-5764-44ae-8E95-01AD0E0EFD48", "0", "999"),
                      Association("Mod", "(1) Community Patch", "d1b6328c-ff44-4b0d-aad7-c657f83610cd", "151", "999")],
        references=[Association("Mod", "(2) Vox Populi", "8411a7a8-dad3-4622-a18e-fcc18324c799", "17", "999")],
        blockers=[Association("Mod", "Old Mod", "11111111-2222-3333-4444-555555555555", "0", "999")],
        files=[FileEntry(r"Lua\Main.lua", True), FileEntry(r"SQL\Changes.sql", False),
               FileEntry(r"Text\en_US\Text.xml", False), FileEntry(r"UI\Addin.xml", True),
               FileEntry(r"Maps\Small & Wet.lua", True)],
        actions=[Action("OnModActivated", "UpdateDatabase", "SQL/Changes.sql"),
                 Action("OnModActivated", "UpdateDatabase", r"Text\en_US\Text.xml")],
        entry_points=[EntryPoint("InGameUIAddin", r"UI\Addin.xml", "Addin", "The addin"),
                      EntryPoint("MapScript", "Maps/Small & Wet.lua", "Small & Wet", "")],
    )
