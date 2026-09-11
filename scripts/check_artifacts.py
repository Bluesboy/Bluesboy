#!/usr/bin/env python3
"""Check built artifacts against the rendering rules in AGENTS.md.

Every expectation is derived from `data/cv.yaml` and `data/ui.yaml`, the same
files both renderers read, so a check cannot drift into describing a layout the
data no longer has. `scripts/validate_cv.py` guards the data; this guards what
came out of it.

Run through `make test/build`, which builds the artifacts first.
"""

import html.parser
import json
import re
import sys
from pathlib import Path

import yaml
from pypdf import PdfReader

LOCALES = ("en", "ru")
# Order is the contract from AGENTS.md; the labels themselves live in ui.yaml.
PDF_SECTIONS = ("summary", "coreSkills", "experience", "earlier", "education", "languages")
# The website keeps its own order, which mobile reads top to bottom.
SITE_SECTIONS = ("summary", "contacts", "core", "selected-work", "experience", "about", "education", "additional")

root = Path(__file__).resolve().parent.parent
with (root / "data/cv.yaml").open(encoding="utf-8") as source:
    cv = yaml.safe_load(source)
with (root / "data/ui.yaml").open(encoding="utf-8") as source:
    ui = yaml.safe_load(source)

build = root / "build"
problems: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        problems.append(message)


def flatten(text: str) -> str:
    """One line of text, the way a parser reading the file sees it."""
    return re.sub(r"\s+", " ", text)


def skills(featured_only: bool) -> list[str]:
    return [item["name"] for group in cv["skills"] for item in group["items"]
            if item.get("featured", False) or not featured_only]


def detailed() -> list[dict]:
    return [job for job in cv["experience"] if job["detailed"]]


def pdf_period(job: dict, lang: str) -> str:
    def month(value: str) -> str:
        year, number = value.split("-")
        return f"{ui['months']['short'][lang][int(number) - 1]} {year}"

    end = ui["present"][lang] if job["period"]["end"] is None else month(job["period"]["end"])
    return f"{month(job['period']['start'])} – {end}"


# --- PDF ------------------------------------------------------------------

pdf_shape: dict[str, tuple[int, int, int]] = {}

for lang in LOCALES:
    name = f"shamil-sattarov-resume-{lang}.pdf"
    path = build / "pdf" / name
    if not path.exists():
        problems.append(f"{name}: missing; run make build/pdf")
        continue

    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    page_flats = [flatten(page) for page in pages]
    flat = flatten("\n".join(pages))

    check(len(pages) == 2, f"{name}: {len(pages)} pages, expected two")

    positions = []
    for key in PDF_SECTIONS:
        heading = ui[key][lang]
        index = flat.find(heading)
        check(index >= 0, f"{name}: section {heading!r} is missing")
        positions.append(index)
    present = [p for p in positions if p >= 0]
    check(present == sorted(present),
          f"{name}: sections are out of order, expected "
          + " → ".join(ui[key][lang] for key in PDF_SECTIONS))

    # An ATS matches literal strings, so every core skill has to survive
    # rendering exactly as it is stored.
    for skill in skills(featured_only=True):
        check(skill in flat, f"{name}: core skill {skill!r} is not in the text")

    check(cv["personal"]["full_name"][lang] in page_flats[0],
          f"{name}: candidate name is missing from the header")
    check(cv["target"]["position"][lang] in page_flats[0],
          f"{name}: target position is missing from the header")
    for paragraph in cv["summary"]:
        check(flatten(paragraph[lang]) in flat, f"{name}: summary paragraph is missing")

    domain = re.sub(r"^https?://", "", cv["site"]["url"]).rstrip("/")
    contacts = [cv["personal"]["email"]]
    contacts += [profile.get("label", profile["network"]) for profile in cv["personal"]["profiles"]
                 if lang in profile.get("resume_languages", list(LOCALES))]
    contacts.append(domain)
    check(" · ".join(contacts) in page_flats[0],
          f"{name}: visible contact bar is incomplete or out of order")

    for job in detailed():
        company, position = job["company"][lang], job["position"][lang]
        check(company in flat and position in flat,
              f"{name}: detailed role {company!r} — {position!r} is incomplete")
        scope = flatten(job["scope"][lang])
        check(scope in flat,
              f"{name}: scope of {company!r} is missing")
        role_parts = [company, position, pdf_period(job, lang), scope]
        for item in job["achievements"]:
            if item.get("featured", False):
                achievement = flatten(item[lang])
                role_parts.append(achievement)
                check(achievement in flat,
                      f"{name}: featured achievement of {company!r} is missing")
        check(any(all(part in page for part in role_parts) for page in page_flats),
              f"{name}: detailed role {company!r} is split across pages")

    earlier = [job for job in cv["experience"] if not job["detailed"]]
    for job in earlier:
        if "resume_group" not in job:
            company = job.get("resume_company", job["company"])[lang]
            entry = f"{pdf_period(job, lang)} — {company} — {job['position'][lang]}"
            check(entry in flat, f"{name}: earlier role {company!r} is incomplete")
    for group, label in ui["resumeGroups"].items():
        jobs = [job for job in earlier if job.get("resume_group") == group]
        if jobs:
            years = f"{jobs[-1]['period']['start'][:4]}–{jobs[0]['period']['end'][:4]}"
            entry = f"{years} — {label[lang]}"
            check(entry in flat, f"{name}: grouped earlier experience {label[lang]!r} is incomplete")

    for item in cv["education"]:
        entry = f"{item['year']} — {item['institution'][lang]} — {item['specialization'][lang]}"
        check(entry in flat, f"{name}: education entry {item['institution'][lang]!r} is incomplete")
        check(item["level"][lang] not in flat,
              f"{name}: education level {item['level'][lang]!r} should be omitted")
    for item in cv["languages"]:
        entry = f"{item['language'][lang]} — {item['level'][lang]}"
        check(entry in flat, f"{name}: language entry {item['language'][lang]!r} is incomplete")

    # The footer carries identity onto a page that may be read on its own.
    for number, page in enumerate(pages, 1):
        page_flat = flatten(page)
        check(cv["personal"]["full_name"][lang] in page_flat
              and domain in page_flat
              and f"{number}/{len(pages)}" in page_flat,
              f"{name}: page {number} has no identity footer")

    uris = set()
    for page in reader.pages:
        for annotation in page.get("/Annots", []):
            action = annotation.get_object().get("/A", {})
            if "/URI" in action:
                uris.add(str(action["/URI"]))

    expected = {f"mailto:{cv['personal']['email']}", cv["site"]["url"]}
    for profile in cv["personal"]["profiles"]:
        if lang in profile.get("resume_languages", list(LOCALES)):
            expected.add(profile["url"])
    for job in detailed():
        if job["website"]:
            expected.add("https://" + job["website"])
    missing = sorted(expected - uris)
    check(not missing, f"{name}: links are not clickable: {missing}")
    # A contact dropped from this locale must not keep a live annotation.
    for profile in cv["personal"]["profiles"]:
        if lang not in profile.get("resume_languages", list(LOCALES)):
            check(profile["url"] not in uris,
                  f"{name}: {profile['network']} is excluded here but still linked")

    # One family, two weights, both subset into the file. A third face means
    # a system font leaked in or an icon font came back through --font-path.
    embedded = set()
    for page in reader.pages:
        fonts = (page.get("/Resources") or {}).get("/Font") or {}
        for key in fonts:
            base = str(fonts[key].get_object().get("/BaseFont", "")).lstrip("/")
            embedded.add(base.split("+")[-1])
    check(embedded == {"IBMPlexSansRoman-Regular", "IBMPlexSansRoman-Bold"},
          f"{name}: embedded faces are {sorted(embedded)}, expected the two IBM Plex weights")

    # Selected Work is a website section: its outcome lines summarise what the
    # PDF already states in full, and must not leak into the two-page resume.
    for item in cv["selected_work"]:
        check(flatten(item["outcome"][lang]) not in flat,
              f"{name}: the Selected Work outcome line reached the PDF")

    meta = reader.metadata or {}
    for field in ("/Title", "/Author", "/Subject"):
        check(bool(meta.get(field)), f"{name}: document metadata {field} is empty")

    keywords = [word.strip() for word in str(meta.get("/Keywords", "")).split(",")]
    for skill in skills(featured_only=True):
        check(skill in keywords, f"{name}: keyword {skill!r} is missing from the metadata")
    check(cv["site"]["url"] in keywords, f"{name}: the CV domain is not among the keywords")
    builds = [word for word in keywords if re.fullmatch(r"v?\d+\.\d+\.\d+[\w.-]*", word)]
    check(not builds, f"{name}: keywords carry a build identifier: {builds}")

    # A block rendered twice reads as a duplicate to a human and to a parser.
    lines = [line.strip() for page in pages for line in page.splitlines()]
    counted: dict[str, int] = {}
    for line in lines:
        if len(line) > 40:
            counted[line] = counted.get(line, 0) + 1
    repeats = sorted(line for line, times in counted.items() if times > 1)
    check(not repeats, f"{name}: duplicated line(s): {repeats[:2]}")

    bullets = sum(1 for line in lines if line.startswith(("•", "-", "–")))
    pdf_shape[lang] = (len(pages), len(present), bullets)

if len(pdf_shape) == len(LOCALES):
    en, ru = pdf_shape["en"], pdf_shape["ru"]
    check(en == ru,
          f"PDF: the locales render different shapes, "
          f"(pages, sections, bullets) is {en} for en and {ru} for ru")


# --- Website --------------------------------------------------------------

class Page(html.parser.HTMLParser):
    """Just enough of the document to assert on its structure."""

    VOID = {"meta", "link", "img", "br", "hr", "input", "source", "path", "use"}

    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.property_meta: dict[str, str] = {}
        self.hreflang: set[str] = set()
        self.canonical = ""
        self.headings: list[tuple[int, str]] = []
        self.sections: list[str] = []
        self.details = 0
        self.open_details = 0
        self.skill_sections: dict[str, list[str]] = {"core": [], "additional": []}
        self.images: list[dict[str, str]] = []
        self.hrefs: set[str] = set()
        self.anchors: list[dict[str, str]] = []
        self.links: list[tuple[dict[str, str], str]] = []
        self.ids: set[str] = set()
        self.jsonld: list[dict] = []
        self.lang = ""
        self.title = ""
        self.text: list[str] = []
        self.selected_work_text: list[str] = []
        self.summaries = 0
        self._open: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "p" and any("summary-stack" in b.get("class", "") for _, b in self._open):
            self.summaries += 1
        if tag == "section":
            self.sections += [c[:-len("-section")] for c in a.get("class", "").split()
                              if c.endswith("-section") and c not in ("main-section", "side-section")]
        elif tag == "details":
            self.details += 1
            self.open_details += int("open" in a)
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "meta":
            if "name" in a:
                self.meta[a["name"]] = a.get("content", "")
            if "property" in a:
                self.property_meta[a["property"]] = a.get("content", "")
        elif tag == "link" and a.get("rel") == "alternate":
            self.hreflang.add(a.get("hreflang", ""))
        elif tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href", "")
        elif tag == "img":
            self.images.append(a)
        elif tag == "a":
            self.hrefs.add(a.get("href", ""))
            self.anchors.append(a)
        if tag not in self.VOID:
            self._open.append((tag, a))

    def handle_endtag(self, tag):
        while self._open:
            open_tag, attrs = self._open.pop()
            if open_tag == tag:
                break

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_data(self, data):
        # JSON-LD repeats the skills, the lead paragraph, the employer and the
        # schools. Counting it as page text would let the machine-readable copy
        # stand in for content the reader lost, so the corpus stops at <script>.
        if not any(tag in ("script", "style") for tag, _ in self._open):
            self.text.append(data)
            if any(tag == "section" and "selected-work-section" in attrs.get("class", "").split()
                   for tag, attrs in self._open):
                self.selected_work_text.append(data)
        if any(tag == "dd" for tag, _ in self._open):
            for tag, attrs in reversed(self._open):
                if tag != "section":
                    continue
                classes = attrs.get("class", "").split()
                for section in self.skill_sections:
                    if f"{section}-section" in classes:
                        self.skill_sections[section] += [name.strip() for name in data.split(",")]
                break
        for tag, attrs in reversed(self._open):
            if tag == "title":
                self.title += data
                break
            if re.fullmatch(r"h[1-6]", tag):
                self.headings.append((int(tag[1]), data.strip()))
                break
            if tag == "a":
                self.links.append((attrs, data.strip()))
                break
            if tag == "script" and attrs.get("type") == "application/ld+json":
                self.jsonld.append(json.loads(data))
                break


site_shape: dict[str, tuple[int, int, int, int]] = {}
site = build / "site"
# English lives at /, and the redirect Hugo writes at /en/ is removed by the
# build; a reappearance means that step was dropped.
check(not (site / "en/index.html").exists(),
      "build/site/en/index.html: the /en/ redirect is published again")

for lang in LOCALES:
    path = site / ("index.html" if lang == "en" else f"{lang}/index.html")
    if not path.exists():
        problems.append(f"{path.relative_to(root)}: missing; run make build/site")
        continue

    page = Page()
    page.feed(path.read_text(encoding="utf-8"))
    where = str(path.relative_to(root))
    text = flatten("".join(page.text))
    full_name = cv["personal"]["full_name"][lang]
    target = cv["target"]["position"][lang]
    title = f"{full_name} — {target}"
    canonical = cv["site"]["url"].rstrip("/") + ("/" if lang == "en" else f"/{lang}/")

    check(page.lang == lang, f"{where}: <html lang> is {page.lang!r}, expected {lang!r}")
    check(tuple(page.sections) == SITE_SECTIONS,
          f"{where}: section order is {page.sections}, expected {list(SITE_SECTIONS)}")
    site_shape[lang] = (len(page.sections), len(page.headings), page.details, len(page.hrefs))
    check(flatten(page.title) == title, f"{where}: title does not match name and target.position")
    check(page.canonical == canonical,
          f"{where}: canonical is {page.canonical!r}, expected {canonical!r}")
    check(page.hreflang == {"en", "ru", "x-default"},
          f"{where}: hreflang set is {sorted(page.hreflang)}")

    # head.html hands summary[0] to the meta tag and the share cards, where a
    # search snippet is cut at roughly 160 characters.
    lead = cv["summary"][0][lang]
    check(page.meta.get("description") == lead,
          f"{where}: meta description is not the lead summary paragraph")
    check(page.property_meta.get("og:type") == "profile",
          f"{where}: OpenGraph type is not profile")
    for key, expected in (
            ("og:title", title),
            ("og:description", lead),
            ("og:url", canonical),
    ):
        check(page.property_meta.get(key) == expected,
              f"{where}: {key} does not match the canonical data")
    check(bool(page.property_meta.get("og:image")), f"{where}: og:image is empty")
    for key, expected in (("twitter:title", title), ("twitter:description", lead)):
        check(page.meta.get(key) == expected,
              f"{where}: {key} does not match the canonical data")
    check(page.meta.get("twitter:image") == page.property_meta.get("og:image"),
          f"{where}: Twitter and OpenGraph images differ")
    check(page.summaries == len(cv["summary"]),
          f"{where}: {page.summaries} summary paragraphs rendered, "
          f"{len(cv['summary'])} in the data")
    expected_details = len(detailed()) + int(any(not job["detailed"] for job in cv["experience"]))
    check(page.details == expected_details,
          f"{where}: {page.details} details blocks rendered, expected {expected_details}")
    check(page.open_details == 0,
          f"{where}: {page.open_details} details blocks are initially open")

    selected_text = flatten(" ".join(page.selected_work_text))
    skill_by_id = {item["id"]: item["name"] for group in cv["skills"]
                   for item in group["items"] if "id" in item}
    achievement_by_id = {
        item["id"]: (item, job["id"])
        for job in detailed()
        for item in job["achievements"]
        if "id" in item
    }
    expected_ids = {job["id"] for job in detailed()}
    expected_ids.update(item["achievement_id"] for item in cv["selected_work"])
    check(expected_ids <= page.ids,
          f"{where}: stable anchors are missing: {sorted(expected_ids - page.ids)}")
    # Every in-page link has to land somewhere: the section nav, the Selected
    # Work cards and the skip link all navigate by fragment and nothing else.
    fragments = {href[1:] for href in page.hrefs if href.startswith("#") and len(href) > 1}
    check(fragments <= page.ids,
          f"{where}: fragment links point at no element: {sorted(fragments - page.ids)}")
    for section in ("selected-work", "experience", "stack", "education"):
        check(f"#{section}" in page.hrefs,
              f"{where}: the section nav does not link to #{section}")
    for item in cv["selected_work"]:
        achievement, role_id = achievement_by_id[item["achievement_id"]]
        for value in (item["title"][lang], item["outcome"][lang], achievement[lang],
                      *(skill_by_id[skill_id] for skill_id in item["skill_ids"])):
            check(flatten(value) in selected_text,
                  f"{where}: Selected Work value {value!r} is missing")
        check(f"#{role_id}" in page.hrefs,
              f"{where}: Selected Work item {item['achievement_id']!r} does not link to its role")

    # A collapsed block is still part of the full CV and must survive in the
    # HTML. Check every canonical entry, not only the visible core subset.
    for paragraph in cv["summary"]:
        check(flatten(paragraph[lang]) in text, f"{where}: summary paragraph is missing")
    for job in cv["experience"]:
        company = job["company"][lang]
        check(company in text and job["position"][lang] in text,
              f"{where}: role {company!r} is incomplete")
        if "scope" in job:
            check(flatten(job["scope"][lang]) in text,
                  f"{where}: scope of {company!r} is missing")
        for field in ("responsibilities", "achievements"):
            for item in job[field]:
                check(flatten(item[lang]) in text,
                      f"{where}: {field} item of {company!r} is missing")
    for item in cv["education"]:
        for field in ("institution", "specialization", "level"):
            check(flatten(item[field][lang]) in text,
                  f"{where}: education {field} is missing")
    for item in cv["languages"]:
        check(item["language"][lang] in text and item["level"][lang] in text,
              f"{where}: language {item['language'][lang]!r} is incomplete")

    check(f"mailto:{cv['personal']['email']}" in page.hrefs,
          f"{where}: email link is missing")
    for profile in cv["personal"]["profiles"]:
        check(profile["url"] in page.hrefs,
              f"{where}: profile link {profile['network']!r} is missing")

    levels = [level for level, _ in page.headings]
    check(levels.count(1) == 1, f"{where}: {levels.count(1)} <h1> elements, expected one")
    for before, after in zip(levels, levels[1:]):
        if after > before:
            check(after == before + 1,
                  f"{where}: heading level jumps from h{before} to h{after}")

    for image in page.images:
        check(bool(image.get("alt", "").strip()),
              f"{where}: <img src={image.get('src')!r}> has no alt text")
    for href in page.hrefs:
        links = [(attrs, label) for attrs, label in page.links if attrs.get("href") == href]
        check(any(label.strip() or attrs.get("aria-label") or attrs.get("title")
                  for attrs, label in links),
              f"{where}: <a href={href!r}> has no accessible name")

    # The skill inventory appears once; Selected Work resolves references to
    # the same canonical items rather than defining another inventory.
    expected_core = skills(featured_only=True)
    expected_additional = [item["name"] for group in cv["skills"] for item in group["items"]
                           if not item.get("featured", False)]
    check(page.skill_sections["core"] == expected_core,
          f"{where}: core skills differ from the featured data")
    check(page.skill_sections["additional"] == expected_additional,
          f"{where}: additional skills differ from the non-featured data")

    check(len(page.jsonld) == 1, f"{where}: expected exactly one JSON-LD block")
    for profile in page.jsonld:
        check(profile.get("@context") == "https://schema.org" and profile.get("@type") == "Person",
              f"{where}: JSON-LD root is not a schema.org Person")
        check(profile.get("name") == full_name, f"{where}: JSON-LD name is incorrect")
        check(profile.get("url") == canonical, f"{where}: JSON-LD URL is not canonical")
        check(profile.get("email") == f"mailto:{cv['personal']['email']}",
              f"{where}: JSON-LD email is incorrect")
        check(profile.get("jobTitle") == cv["target"]["position"][lang],
              f"{where}: JSON-LD jobTitle does not match target.position")
        check(profile.get("description") == lead,
              f"{where}: JSON-LD description is not the lead summary paragraph")
        check(str(profile.get("image", "")).startswith(cv["site"]["url"]),
              f"{where}: JSON-LD image is not an absolute site URL")
        address = profile.get("address", {})
        check(address.get("addressLocality") == cv["personal"]["location"]["city"][lang]
              and address.get("addressCountry") == cv["personal"]["location"]["country_code"],
              f"{where}: JSON-LD personal address is incorrect")
        same_as = set(profile.get("sameAs", []))
        for contact in cv["personal"]["profiles"]:
            check(contact["url"] in same_as,
                   f"{where}: JSON-LD sameAs omits {contact['network']}")
        knows = set(profile.get("knowsAbout", []))
        check(knows == set(skills(featured_only=False))
              and len(profile.get("knowsAbout", [])) == len(skills(featured_only=False)),
              f"{where}: JSON-LD knowsAbout differs from the skill data")

        current = next(job for job in cv["experience"] if job["period"]["end"] is None)
        works_for = profile.get("worksFor", {})
        check(works_for.get("name") == current["company"][lang],
              f"{where}: JSON-LD worksFor name is incorrect")
        if current["website"]:
            check(works_for.get("url") == f"https://{current['website']}",
                  f"{where}: JSON-LD worksFor URL is incorrect")
        work_address = works_for.get("address", {})
        check(work_address.get("addressLocality") == current["location"]["city"][lang]
              and work_address.get("addressCountry") == current["location"]["country_code"],
              f"{where}: JSON-LD worksFor address is incorrect")

        alumni = [item.get("name") for item in profile.get("alumniOf", [])]
        check(alumni == [item["institution"][lang] for item in cv["education"]],
              f"{where}: JSON-LD alumniOf differs from education data")
        spoken = [item.get("name") for item in profile.get("knowsLanguage", [])]
        check(spoken == [item["language"][lang] for item in cv["languages"]],
              f"{where}: JSON-LD knowsLanguage differs from language data")

if len(site_shape) == len(LOCALES):
    en, ru = site_shape["en"], site_shape["ru"]
    check(en == ru,
          f"website: the locales render different shapes, "
          f"(sections, headings, details, links) is {en} for en and {ru} for ru")

for lang in LOCALES:
    path = site / ("404.html" if lang == "en" else f"{lang}/404.html")
    if not path.exists():
        problems.append(f"{path.relative_to(root)}: missing")
        continue
    page = Page()
    page.feed(path.read_text(encoding="utf-8"))
    where = str(path.relative_to(root))
    check(page.lang == lang, f"{where}: <html lang> is {page.lang!r}, expected {lang!r}")
    check(page.meta.get("robots") == "noindex", f"{where}: robots meta is not noindex")
    h1 = [text for level, text in page.headings if level == 1]
    check(h1 == [ui["notFoundTitle"][lang]], f"{where}: localized h1 is incorrect")
    text = flatten("".join(page.text))
    check(ui["notFoundBody"][lang] in text, f"{where}: localized explanation is missing")
    for home_lang, href in (("en", "/"), ("ru", "/ru/")):
        matches = [anchor for anchor in page.anchors if anchor.get("href") == href]
        check(len(matches) == 1
              and matches[0].get("lang") == home_lang
              and matches[0].get("hreflang") == home_lang,
              f"{where}: {home_lang} home link is missing or lacks language metadata")
        check(f"{ui['notFoundHome'][home_lang]} · {home_lang.upper()}" in text,
              f"{where}: {home_lang} home-link label is missing")

if problems:
    for problem in problems:
        print(f"build: {problem}")
    sys.exit(1)

print("build: artifacts match the rendering rules")
