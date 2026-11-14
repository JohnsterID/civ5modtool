"""Rebuild tests/data/modbuddy/*.modinfo with ModBuddy's own build (Windows, Civ5 SDK).

Each test mod (tests/helpers.py MODBUDDY_VARIANTS) is written as a .civ5proj and
built by the SDK's MSBuild targets, headless, as ModBuddy's Build command does.

usage: python tools/modbuddy_refs.py [--sdk "<Civ5 SDK folder>"] [--check]
--check compares instead of writing (exit 1 on a difference).
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tests.helpers import MODBUDDY_VARIANTS, make_variant  # noqa: E402

DEFAULT_SDK = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Sid Meier's Civilization V SDK")
MSBUILD = Path(r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\MSBuild.exe")
OUT = ROOT / "tests" / "data" / "modbuddy"


def build(sdk: Path, variant: str, work: Path) -> bytes:
    ext = work / "ext"
    if not ext.exists():  # the targets import $(MSBuildExtensionsPath)\Firaxis\ModBuddy\...
        shutil.copytree(sdk / "ModBuddy" / "Build", ext / "Firaxis" / "ModBuddy")
    mod = work / variant / "Mod"
    mod.mkdir(parents=True)
    project = make_variant(mod, variant)
    proj = mod / "Test Mod.civ5proj"
    project.write_civ5proj(proj, create_solution=False)
    out = work / variant / "out"
    r = subprocess.run([str(MSBUILD), str(proj), "/t:Build", "/nologo", "/v:minimal",
                        f"/p:MSBuildExtensionsPath={ext}", r"/p:Civ5Path=C:\none", r"/p:Civ5UserPath=C:\none",
                        f"/p:SafeName={project.name}",  # set by the ModBuddy IDE: the mod's name
                        f"/p:BuildDir={out}\\"], capture_output=True, text=True)
    built = list(out.glob("*.modinfo"))
    if r.returncode or len(built) != 1:
        sys.exit(f"{variant}: build failed\n{r.stdout}\n{r.stderr}")
    return built[0].read_bytes()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sdk", type=Path, default=DEFAULT_SDK)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    status = 0
    with tempfile.TemporaryDirectory() as tmp:
        for variant in MODBUDDY_VARIANTS:
            data, ref = build(a.sdk, variant, Path(tmp)), OUT / f"{variant}.modinfo"
            if a.check:
                same = ref.is_file() and ref.read_bytes() == data
                print(f"{variant}: {'same' if same else 'DIFFERENT'}")
                status |= not same
            else:
                OUT.mkdir(parents=True, exist_ok=True)
                ref.write_bytes(data)
                print(f"{variant}: wrote {ref.relative_to(ROOT)} ({len(data)} bytes)")
    return status


if __name__ == "__main__":
    sys.exit(main())
