#!/usr/bin/env python3
"""Render clipboard-friendly bilingual TXT files from canonical CV data."""

import argparse
import re
from pathlib import Path

import yaml

LOCALES = ("en", "ru")
KINDS = ("profile", "skills", "experience", "education")
ROOT = Path(__file__).resolve().parent.parent


def localized(value: dict[str, str], lang: str) -> str:
    return value[lang]


def section(label: str, lines: list[str]) -> str:
    return "\n".join((label.upper(), *lines))


def place(location: dict, lang: str) -> str:
    parts = [localized(location["city"], lang)]
    if "country" in location:
        parts.append(localized(location["country"], lang))
    return ", ".join(parts)


def period(job: dict, ui: dict, lang: str) -> str:
    def month(value: str) -> str:
        year, number = value.split("-")
        return f"{ui['months']['long'][lang][int(number) - 1]} {year}"

    end = (
        ui["present"][lang]
        if job["period"]["end"] is None
        else month(job["period"]["end"])
    )
    return f"{month(job['period']['start'])} – {end}"


def render_profile(cv: dict, ui: dict, lang: str) -> str:
    personal = cv["personal"]
    details = [
        f"{localized(ui['location'], lang)}: {place(personal['location'], lang)}",
        f"{localized(ui['format'], lang)}: "
        f"{localized(cv['target']['work_format'], lang)}",
        f"{localized(ui['businessTravel'], lang)}: "
        f"{localized(personal['business_travel'], lang)}",
    ]
    contacts = [f"{localized(ui['email'], lang)}: {personal['email']}"]
    contacts.extend(
        f"{profile['network']}: {profile['url']}"
        for profile in personal["profiles"]
    )
    contacts.append(f"{localized(ui['cvSite'], lang)}: {cv['site']['url']}")
    languages = [
        f"{localized(item['language'], lang)} — {localized(item['level'], lang)}"
        for item in cv["languages"]
    ]
    how = [f"— {localized(item, lang)}" for item in cv["about"]]

    blocks = [
        f"{localized(personal['full_name'], lang)}\n"
        f"{localized(cv['target']['position'], lang)}",
        section(
            localized(ui["exportAbout"], lang),
            [localized(item, lang) for item in cv["summary"]],
        ),
        section(localized(ui["details"], lang), details),
        section(localized(ui["contacts"], lang), contacts),
        section(localized(ui["languages"], lang), languages),
        section(localized(ui["about"], lang), how),
    ]
    return "\n\n".join(blocks) + "\n"


def render_skills(cv: dict, ui: dict, lang: str) -> str:
    def groups(featured: bool) -> list[str]:
        result = []
        for group in cv["skills"]:
            names = [
                item["name"] for item in group["items"]
                if item.get("featured", False) is featured
            ]
            if names:
                result.append(f"{localized(group['area'], lang)}: {', '.join(names)}")
        return result

    blocks = [
        section(localized(ui["stack"], lang), groups(True)),
        section(localized(ui["additionalSkills"], lang), groups(False)),
    ]
    return "\n\n".join(blocks) + "\n"


def render_experience(cv: dict, ui: dict, lang: str) -> str:
    roles = []
    for job in cv["experience"]:
        location = place(job["location"], lang)
        if job.get("remote", False):
            location += f" · {localized(ui['remote'], lang)}"
        metadata = [
            localized(job["position"], lang),
            localized(job["company"], lang),
            period(job, ui, lang),
            location,
        ]
        if job["website"]:
            metadata.append(job["website"])
        if "scope" in job:
            metadata.extend(("", localized(job["scope"], lang)))
        metadata.extend(("", localized(ui["highlights"], lang).upper()))
        metadata.extend(f"— {localized(item, lang)}" for item in job["achievements"])
        metadata.extend(("", localized(ui["responsibilities"], lang).upper()))
        metadata.extend(f"— {localized(item, lang)}" for item in job["responsibilities"])
        roles.append("\n".join(metadata))

    body = "\n\n---\n\n".join(roles)
    return section(localized(ui["experience"], lang), [body]) + "\n"


def render_education(cv: dict, ui: dict, lang: str) -> str:
    entries = []
    for item in cv["education"]:
        entries.append("\n".join((
            item["year"],
            localized(item["institution"], lang),
            localized(item["level"], lang),
            localized(item["specialization"], lang),
        )))
    body = "\n\n---\n\n".join(entries)
    return section(localized(ui["education"], lang), [body]) + "\n"


def output_name(cv: dict, kind: str, lang: str) -> str:
    name = cv["personal"]["full_name"]["en"].lower()
    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    return f"{slug}-{kind}-{lang}.txt"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build" / "text")
    args = parser.parse_args()

    with (ROOT / "data" / "cv.yaml").open(encoding="utf-8") as source:
        cv = yaml.safe_load(source)
    with (ROOT / "data" / "ui.yaml").open(encoding="utf-8") as source:
        ui = yaml.safe_load(source)

    renderers = {
        "profile": render_profile,
        "skills": render_skills,
        "experience": render_experience,
        "education": render_education,
    }
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    for lang in LOCALES:
        for kind in KINDS:
            path = output_dir / output_name(cv, kind, lang)
            path.write_text(renderers[kind](cv, ui, lang), encoding="utf-8")
            try:
                print(path.relative_to(ROOT))
            except ValueError:
                print(path)


if __name__ == "__main__":
    main()
