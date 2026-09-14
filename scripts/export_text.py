#!/usr/bin/env python3
"""Render clipboard-friendly bilingual TXT files from canonical CV data."""

import argparse
import re
from pathlib import Path

import yaml

LOCALES = ("en", "ru")
KINDS = ("profile", "skills", "experience", "education",
         "hh", "linkedin", "wellfound", "hirist")

# What each platform accepts in a field, in characters unless noted.
# LinkedIn: headline 220, About 2600, one position description 2000,
# and 50 skills at most. Wellfound: the mini-resume is 160.
FIELD_LIMITS = {
    "linkedin.headline": 220,
    "linkedin.about": 2600,
    "linkedin.role": 2000,
    "wellfound.mini_resume": 160,
}
LINKEDIN_SKILLS = 50
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
        f"{localized(ui['timezone'], lang)}: {personal['timezone']}",
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



def bullets(items: list[str]) -> list[str]:
    return [f"• {item}" for item in items]


def role_heading(job: dict, ui: dict, lang: str) -> str:
    """One line a platform form never breaks up: title, company, dates, place."""
    location = place(job["location"], lang)
    if job.get("remote", False):
        location += f" · {localized(ui['remote'], lang)}"
    parts = [
        localized(job["position"], lang),
        localized(job["company"], lang),
        period(job, ui, lang),
        location,
    ]
    return " — ".join(parts)


def role_body(job: dict, ui: dict, lang: str, limit: int | None = None) -> str:
    """Scope, achievements and responsibilities, trimmed to fit a field.

    A platform that caps a description silently truncates whatever does not
    fit, so drop whole items instead: responsibilities first, then the
    achievements the CV does not mark as featured, last to first.
    """
    scope = [localized(job["scope"], lang)] if "scope" in job else []
    achievements = [
        (localized(item, lang), item.get("featured", False))
        for item in job.get("achievements", [])
    ]
    responsibilities = [localized(item, lang) for item in job.get("responsibilities", [])]

    def assemble() -> str:
        blocks = list(scope)
        if achievements:
            blocks.append("\n".join((
                localized(ui["highlights"], lang) + ":",
                *bullets([text for text, _ in achievements]),
            )))
        if responsibilities:
            blocks.append("\n".join((
                localized(ui["responsibilities"], lang) + ":",
                *bullets(responsibilities),
            )))
        return "\n\n".join(blocks)

    body = assemble()
    if limit is None:
        return body
    while len(body) > limit and responsibilities:
        responsibilities.pop()
        body = assemble()
    while len(body) > limit and any(not featured for _, featured in achievements):
        index = max(i for i, (_, featured) in enumerate(achievements) if not featured)
        achievements.pop(index)
        body = assemble()
    return body


def skill_names(cv: dict, featured: bool | None = None) -> list[str]:
    return [
        item["name"]
        for group in cv["skills"]
        for item in group["items"]
        if featured is None or item.get("featured", False) is featured
    ]


def skill_groups(cv: dict, lang: str, featured: bool) -> list[str]:
    lines = []
    for group in cv["skills"]:
        names = [
            item["name"] for item in group["items"]
            if item.get("featured", False) is featured
        ]
        if names:
            lines.append(f"{localized(group['area'], lang)}: {', '.join(names)}")
    return lines


def languages_lines(cv: dict, lang: str) -> list[str]:
    return [
        f"{localized(item['language'], lang)} — {localized(item['level'], lang)}"
        for item in cv["languages"]
    ]


def education_lines(cv: dict, lang: str) -> list[str]:
    return [
        " — ".join((
            item["year"],
            localized(item["institution"], lang),
            localized(item["level"], lang),
            localized(item["specialization"], lang),
        ))
        for item in cv["education"]
    ]


def field_label(ui: dict, key: str, lang: str) -> str:
    return localized(ui["exportFields"][key], lang)


def about_text(cv: dict, lang: str, skip_lead: bool = False) -> str:
    """Summary followed by the How I work points, as one field of prose."""
    summary = cv["summary"][1:] if skip_lead else cv["summary"]
    paragraphs = [localized(item, lang) for item in summary]
    paragraphs.extend(bullets([localized(item, lang) for item in cv["about"]]))
    return "\n\n".join(paragraphs)


def detailed_roles(cv: dict) -> list[dict]:
    return [job for job in cv["experience"] if job.get("detailed", False)]


def earlier_roles(cv: dict) -> list[dict]:
    return [job for job in cv["experience"] if not job.get("detailed", False)]


def platform_blocks(kind: str, cv: dict, ui: dict, lang: str) -> list[tuple[str, str, str]]:
    """The fields of one platform as (limit key, field label, value)."""
    personal, target = cv["personal"], cv["target"]
    position = localized(target["position"], lang)
    lead = localized(cv["summary"][0], lang)
    blocks: list[tuple[str, str, str]] = []

    if kind == "linkedin":
        blocks.append(("linkedin.headline", field_label(ui, "headline", lang), position))
        blocks.append(("linkedin.about", field_label(ui, "about", lang), about_text(cv, lang)))
        for job in detailed_roles(cv):
            body = role_body(job, ui, lang, FIELD_LIMITS["linkedin.role"])
            blocks.append(("linkedin.role", role_heading(job, ui, lang), body))
        for job in earlier_roles(cv):
            blocks.append(("", role_heading(job, ui, lang), role_body(job, ui, lang)))
        names = skill_names(cv, featured=True) + skill_names(cv, featured=False)
        blocks.append(("linkedin.skills", field_label(ui, "skills", lang),
                       "\n".join(names[:LINKEDIN_SKILLS])))
    elif kind == "hh":
        blocks.append(("", field_label(ui, "desiredPosition", lang), position))
        blocks.append(("", field_label(ui, "keySkills", lang),
                       "\n".join(skill_names(cv, featured=True))))
        blocks.append(("", field_label(ui, "profileSummary", lang), about_text(cv, lang)))
        for job in cv["experience"]:
            blocks.append(("", role_heading(job, ui, lang), role_body(job, ui, lang)))
    elif kind == "wellfound":
        blocks.append(("", field_label(ui, "role", lang), position))
        blocks.append(("wellfound.mini_resume", field_label(ui, "miniResume", lang), lead))
        blocks.append(("", field_label(ui, "about", lang),
                       about_text(cv, lang, skip_lead=True)))
        for job in detailed_roles(cv):
            blocks.append(("", role_heading(job, ui, lang), role_body(job, ui, lang)))
        blocks.append(("", field_label(ui, "skills", lang),
                       ", ".join(skill_names(cv, featured=True))))
    elif kind == "hirist":
        blocks.append(("", field_label(ui, "headline", lang), position))
        blocks.append(("", field_label(ui, "profileSummary", lang),
                       "\n\n".join(localized(item, lang) for item in cv["summary"])))
        blocks.append(("", field_label(ui, "keySkills", lang),
                       ", ".join(skill_names(cv, featured=True))))
        for job in detailed_roles(cv):
            blocks.append(("", role_heading(job, ui, lang), role_body(job, ui, lang)))
    else:
        raise ValueError(f"unknown platform {kind!r}")

    blocks.append(("", localized(ui["languages"], lang), "\n".join(languages_lines(cv, lang))))
    blocks.append(("", localized(ui["education"], lang), "\n".join(education_lines(cv, lang))))
    blocks.append(("", localized(ui["contacts"], lang), "\n".join([
        personal["email"],
        *(profile["url"] for profile in personal["profiles"]),
        cv["site"]["url"],
    ])))
    return blocks


def render_platform(kind: str):
    def render(cv: dict, ui: dict, lang: str) -> str:
        parts = [f"{label}\n{body}" for _, label, body in platform_blocks(kind, cv, ui, lang)]
        return "\n\n".join(parts) + "\n"

    return render


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
        "hh": render_platform("hh"),
        "linkedin": render_platform("linkedin"),
        "wellfound": render_platform("wellfound"),
        "hirist": render_platform("hirist"),
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
