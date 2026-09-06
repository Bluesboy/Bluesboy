#!/usr/bin/env python3
"""Regenerate the bundled IBM Plex Sans faces in assets/fonts.

Not part of `make build` — the generated faces are committed, exactly like
the vendored Typst packages, so that building the CV needs no network and
no system fonts. Run this only to change the family, the weights or the
character coverage, then commit the result.

Source is the Google Fonts copy of IBM Plex Sans, pinned to a commit so a
rerun reproduces the same bytes. The upstream file is a variable font; the
two static instances below are cut from it rather than downloaded
separately, so both weights come from one audited source.

Typst cannot read WOFF2 (checked on 0.15.1), so each weight ships twice:
TTF for `typst compile --font-path assets/fonts`, WOFF2 for the browser.
Only the WOFF2 files are ever published — Hugo emits what templates ask
for, and no template asks for the TTFs.

Requires: pip install fonttools brotli
"""

import sys
import urllib.request
from pathlib import Path

COMMIT = "8409f033cd7dee08914990602f0df5f5e70e0c14"
BASE = f"https://raw.githubusercontent.com/google/fonts/{COMMIT}/ofl/ibmplexsans"
VARIABLE = f"{BASE}/IBMPlexSans%5Bwdth,wght%5D.ttf"
LICENSE = f"{BASE}/OFL.txt"
EXPECTED_VERSION = "Version 3.201"

# Weights the design actually uses. main.css asks for 400 and 700 only;
# altacv asks for regular and bold. Adding a weight means adding a file to
# every page load, so keep this list short and deliberate.
WEIGHTS = {400: "Regular", 700: "Bold"}

# Coverage. Deliberately narrow: the CV is English and Russian, and every
# extra block costs bytes on the critical path. scripts/validate_cv.py
# enforces that data/cv.yaml stays inside these ranges, so widening the
# content means widening this list and rerunning this script.
RANGES = [
    (0x0020, 0x007E),  # Basic Latin
    (0x00A0, 0x00FF),  # Latin-1 Supplement — guillemets, middle dot, accents
    (0x0400, 0x045F),  # Cyrillic — Russian, Ukrainian, Belarusian
    (0x0490, 0x0491),  # Ukrainian ge with upturn
    (0x2010, 0x2027),  # dashes, curly quotes, ellipsis
    (0x2030, 0x2030),  # per mille
    (0x2039, 0x203A),  # single guillemets
    (0x2044, 0x2044),  # fraction slash
    (0x2116, 0x2116),  # numero
    (0x20AC, 0x20AC),  # euro
    (0x20B4, 0x20B4),  # hryvnia
    (0x20BD, 0x20BD),  # ruble
    (0x2212, 0x2212),  # minus
]

FEATURES = ["kern", "liga", "calt", "ccmp", "locl", "mark", "mkmk"]

root = Path(__file__).resolve().parent.parent
out_dir = root / "assets/fonts"


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def cut(source: Path, unicodes: set[int], target: Path, flavor: str | None,
        features: list[str] | None = None) -> int:
    from fontTools import subset
    from fontTools.ttLib import TTFont

    options = subset.Options()
    options.layout_features = FEATURES if features is None else features
    options.name_IDs = ["*"]
    options.name_legacy = True
    options.notdef_outline = True
    options.recalc_bounds = True
    font = TTFont(source)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=unicodes)
    subsetter.subset(font)
    font.flavor = flavor
    font.save(target)
    return target.stat().st_size


def covered() -> set[int]:
    """Every codepoint the bundled faces carry."""
    return {c for start, end in RANGES for c in range(start, end + 1)}


# Font Awesome. Only Typst uses these — the website inlines its five
# glyphs as SVG — so they are cut down to what the vendored altacv can
# possibly ask for. Both the icon names and their codepoints are read out
# of vendor/typst, so the subset cannot drift from the theme.
AWESOME = {
    "Font Awesome 7 Free-Solid-900.otf",
    "Font Awesome 7 Brands-Regular-400.otf",
}
AWESOME_SOURCE = "sources/fontawesome"


def awesome_codepoints() -> set[int]:
    import re

    icons = (root / "vendor/typst/preview/altacv/1.6.0/internal/icons.typ").read_text(
        encoding="utf-8")
    names = set(re.findall(r'^\s+\w+: "([a-z-]+)",', icons, re.M))
    table = (root / "vendor/typst/preview/fontawesome/0.6.1/lib-gen-map.typ").read_text(
        encoding="utf-8")
    points: set[int] = set()
    for name in names:
        match = re.search(r'"%s":\s*"([^"]+)"' % re.escape(name), table)
        if match is None:
            raise SystemExit(f"{name!r} is not in the fontawesome map")
        points.update(int(h, 16) for h in re.findall(r"\{([0-9a-fA-F]+)\}", match.group(1)))
    return points


def build_awesome() -> None:
    from fontTools.ttLib import TTFont

    archive = root / AWESOME_SOURCE
    if not archive.is_dir():
        print(f"skipping Font Awesome: put the upstream OTFs in {AWESOME_SOURCE}/")
        return
    points = awesome_codepoints()
    for name in sorted(AWESOME):
        source = archive / name
        font = TTFont(source)
        wanted = points & set(font.getBestCmap())
        target = out_dir / name
        size = cut(source, wanted, target, None, features=[])
        print(f"{name:42} {size:>7} B  ({len(wanted)} glyphs)")


def main() -> int:
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    unicodes = covered()
    out_dir.mkdir(parents=True, exist_ok=True)

    variable = out_dir / ".plex-variable.ttf"
    variable.write_bytes(fetch(VARIABLE))
    (out_dir / "OFL-IBMPlexSans.txt").write_bytes(fetch(LICENSE))

    version = next(
        str(r) for r in TTFont(variable)["name"].names
        if r.nameID == 5 and r.platformID == 3
    )
    if version != EXPECTED_VERSION:
        print(f"upstream is {version!r}, expected {EXPECTED_VERSION!r}", file=sys.stderr)
        variable.unlink()
        return 1

    for weight, label in WEIGHTS.items():
        static = out_dir / f".plex-{weight}.ttf"
        instance = instancer.instantiateVariableFont(
            TTFont(variable),
            {"wght": weight, "wdth": 100},
            updateFontNames=True,
            inplace=False,
        )
        instance.save(static)
        for flavor, suffix in ((None, "ttf"), ("woff2", "woff2")):
            target = out_dir / f"IBMPlexSans-{label}.{suffix}"
            size = cut(static, unicodes, target, flavor)
            print(f"{target.name:28} {size:>7} B")
        static.unlink()

    variable.unlink()
    print(f"\n{len(unicodes)} codepoints requested from {EXPECTED_VERSION}\n")
    build_awesome()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
