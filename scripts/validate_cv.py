#!/usr/bin/env python3
"""Validate the canonical CV data against its JSON Schema."""

import json
import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fonts import covered  # noqa: E402  (path set above)

root = Path(__file__).resolve().parent.parent
with (root / "data/cv.yaml").open(encoding="utf-8") as source:
    cv = yaml.safe_load(source)
with (root / "data/ui.yaml").open(encoding="utf-8") as source:
    ui = yaml.safe_load(source)
with (root / "schema/cv.schema.json").open(encoding="utf-8") as source:
    schema = json.load(source)

validator = Draft202012Validator(schema, format_checker=FormatChecker())
errors = sorted(validator.iter_errors(cv), key=lambda error: list(error.path))
if errors:
    for error in errors:
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        print(f"{path}: {error.message}")
    raise SystemExit(1)


problems: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        problems.append(message)


# --- rules JSON Schema cannot state --------------------------------------

# `format: "uri"` is a no-op unless jsonschema was installed with an extra,
# so URLs are checked here too rather than trusted to a checker that may
# not be registered.
for label, url in (
    ("site.url", cv["site"]["url"]),
    *((f"personal.profiles[{i}].url", p["url"])
      for i, p in enumerate(cv["personal"]["profiles"])),
):
    parsed = urllib.parse.urlsplit(url)
    check(parsed.scheme in {"http", "https"} and bool(parsed.netloc),
          f"{label}: {url!r} is not an absolute http(s) URL")

# Employer sites are stored as bare hostnames; "" marks one that is gone.
for i, job in enumerate(cv["experience"]):
    site = job["website"]
    check(site == "" or re.fullmatch(r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}", site) is not None,
          f"experience[{i}].website: {site!r} is neither empty nor a hostname")

# Periods must run forwards, only the current job may be open, and the list
# is expected newest first — none of which a schema can express.
open_periods = [i for i, job in enumerate(cv["experience"]) if job["period"]["end"] is None]
check(len(open_periods) <= 1,
      f"experience: {len(open_periods)} entries have no end date; at most one may be current")

starts = []
for i, job in enumerate(cv["experience"]):
    start, end = job["period"]["start"], job["period"]["end"]
    starts.append(start)
    check(end is None or end >= start,
          f"experience[{i}].period: {end} ends before it starts ({start})")
check(starts == sorted(starts, reverse=True),
      "experience: entries are not in reverse-chronological order")

# Detailed roles keep full website content and a useful curated resume view.
# featured defaults to false in both renderers; JSON Schema defaults do not
# populate missing keys.
for i, job in enumerate(cv["experience"]):
    if not job["detailed"]:
        continue
    for field in ("responsibilities", "achievements"):
        check(len(job[field]) >= 3,
              f"experience[{i}].{field}: detailed entries need at least 3, found {len(job[field])}")
    check("scope" in job, f"experience[{i}].scope: detailed entries need a role scope")
    check(any(item.get("featured", False) for item in job["achievements"]),
          f"experience[{i}].achievements: detailed entries need a featured achievement")

skill_names = [item["name"] for group in cv["skills"] for item in group["items"]]
check(len(skill_names) == len(set(skill_names)), "skills: names must not be duplicated")
check(any(item.get("featured", False) for group in cv["skills"] for item in group["items"]),
      "skills: at least one core skill must be featured")


def check_ui(node, path="ui"):
    if not isinstance(node, dict):
        problems.append(f"{path}: expected a localized value or a group of values")
    elif "en" in node or "ru" in node:
        check(set(node) == {"en", "ru"}, f"{path}: both en and ru are required")
        for value in node.values():
            check(isinstance(value, str) and bool(value)
                  or isinstance(value, list) and len(value) == 12
                  and all(isinstance(item, str) and item for item in value),
                  f"{path}: expected nonempty text or 12 month names")
    else:
        for key, value in node.items():
            check_ui(value, f"{path}.{key}")


check_ui(ui)

if problems:
    for problem in problems:
        print(f"data/cv.yaml: {problem}")
    raise SystemExit(1)


def strings(node):
    """Every string in the data, wherever it sits."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from strings(value)


# The bundled faces carry a deliberately narrow Latin + Cyrillic subset, so
# a character outside it would silently render as a fallback face on the web
# and as a blank box in the PDF. Fail here instead, where the message can
# say what to do about it.
glyphs = covered()
failed = False
for name, document in (("data/cv.yaml", cv), ("data/ui.yaml", ui)):
    unsupported = sorted(
        {c for text in strings(document) for c in text if ord(c) not in glyphs and ord(c) >= 0x20}
    )
    for char in unsupported:
        label = unicodedata.name(char, "unnamed")
        print(f"{name}: U+{ord(char):04X} {char!r} ({label}) is outside the bundled font subset")
        failed = True
if failed:
    print("Widen RANGES in scripts/build_fonts.py, rerun it, and commit the fonts.")
    raise SystemExit(1)

print("data/cv.yaml: valid")
