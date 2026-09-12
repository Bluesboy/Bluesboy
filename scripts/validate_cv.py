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
job_ids: list[str] = []
achievement_owners: dict[str, bool] = {}
resume_groups: dict[str, list[int]] = {}
for i, job in enumerate(cv["experience"]):
    if "id" in job:
        job_ids.append(job["id"])
    check("resume_company" not in job or not job["detailed"],
          f"experience[{i}].resume_company: only compact earlier roles use a short name")
    check("resume_group" not in job or not job["detailed"],
          f"experience[{i}].resume_group: detailed roles cannot be grouped")
    if "resume_group" in job:
        resume_groups.setdefault(job["resume_group"], []).append(i)
        check(job["period"]["end"] is not None,
              f"experience[{i}].resume_group: grouped roles must have a closed period")
    for achievement in job["achievements"]:
        if "id" in achievement:
            check(achievement["id"] not in achievement_owners,
                  f"experience[{i}].achievements: duplicate id {achievement['id']!r}")
            achievement_owners[achievement["id"]] = job["detailed"]
    if not job["detailed"]:
        continue
    check("id" in job, f"experience[{i}].id: detailed entries need a stable id")
    for field in ("responsibilities", "achievements"):
        check(len(job[field]) >= 3,
              f"experience[{i}].{field}: detailed entries need at least 3, found {len(job[field])}")
    check("scope" in job, f"experience[{i}].scope: detailed entries need a role scope")
    check(any(item.get("featured", False) for item in job["achievements"]),
          f"experience[{i}].achievements: detailed entries need a featured achievement")

check(len(job_ids) == len(set(job_ids)), "experience: ids must not be duplicated")
for group, indices in resume_groups.items():
    check(len(indices) >= 2, f"experience.resume_group {group!r}: groups need at least two roles")
    check(indices == list(range(indices[0], indices[-1] + 1)),
          f"experience.resume_group {group!r}: grouped roles must be contiguous")
    check(group in ui.get("resumeGroups", {}),
          f"experience.resume_group {group!r}: missing ui.resumeGroups label")

# The first summary paragraph is what head.html hands to the meta description
# and the share cards. A search snippet shows roughly the first 155 characters,
# so the opening has to stand on its own; the cap only keeps the lead from
# growing into a paragraph.
for lang in ("en", "ru"):
    lead = cv["summary"][0][lang]
    check(len(lead) <= 200,
          f"summary[0].{lang}: lead paragraph is {len(lead)} characters, keep it under 200")

skill_items = [item for group in cv["skills"] for item in group["items"]]
skill_names = [item["name"] for item in skill_items]
check(len(skill_names) == len(set(skill_names)), "skills: names must not be duplicated")
skill_ids = [item["id"] for item in skill_items if "id" in item]
check(len(skill_ids) == len(set(skill_ids)), "skills: ids must not be duplicated")
check(any(item.get("featured", False) for item in skill_items),
      "skills: at least one core skill must be featured")
# Core stack is the scannable list, not an inventory: AGENTS.md aims at about
# 30-35 visible items, and every other skill still shows under Additional
# technologies on the website.
featured_skills = [item for item in skill_items if item.get("featured", False)]
check(len(featured_skills) <= 38,
      f"skills: {len(featured_skills)} featured items, keep the core stack at 38 or fewer")

selected_achievements: list[str] = []
for i, item in enumerate(cv["selected_work"]):
    achievement_id = item["achievement_id"]
    selected_achievements.append(achievement_id)
    check(achievement_id in achievement_owners,
          f"selected_work[{i}].achievement_id: unknown id {achievement_id!r}")
    check(achievement_owners.get(achievement_id, False),
          f"selected_work[{i}].achievement_id: selected work must belong to a detailed role")
    for skill_id in item["skill_ids"]:
        check(skill_id in skill_ids,
              f"selected_work[{i}].skill_ids: unknown id {skill_id!r}")
check(len(selected_achievements) == len(set(selected_achievements)),
      "selected_work: achievement references must not be duplicated")

# The outcome line is a restatement, not a source: every figure in it has to
# be stated by the achievement it points at, in either language, whether the
# achievement spells the number out or writes it in digits.
NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "один": "1", "одну": "1", "одной": "1", "минуты": "1",
    "два": "2", "две": "2", "двух": "2", "три": "3", "трёх": "3", "трех": "3",
    "четыре": "4", "четырёх": "4", "пять": "5", "пяти": "5",
    "тремя": "3", "двумя": "2", "одним": "1", "десять": "10", "десяти": "10",
}
achievement_text = {
    item["id"]: " ".join(item[lang] for lang in ("en", "ru"))
    for job in cv["experience"] for item in job["achievements"] if "id" in item
}


def figures(text: str) -> set[str]:
    found = set(re.findall(r"\d+", text))
    for word, digit in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", text, re.I):
            found.add(digit)
    return found


for i, item in enumerate(cv["selected_work"]):
    supported = figures(achievement_text.get(item["achievement_id"], ""))
    for lang in ("en", "ru"):
        line = item["outcome"][lang]
        check(len(line) <= 60,
              f"selected_work[{i}].outcome.{lang}: {len(line)} characters, keep the line under 60")
        unsupported = sorted(figures(line) - supported)
        check(not unsupported,
              f"selected_work[{i}].outcome.{lang}: figure(s) {unsupported} are not in the achievement")


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
