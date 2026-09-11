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
    flat = flatten("\n".join(pages))

    # Two pages is the budget; a third means the content outgrew the format.
    check(len(pages) <= 2, f"{name}: {len(pages)} pages, the resume targets two")

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

    for job in detailed():
        company, position = job["company"][lang], job["position"][lang]
        check(company in flat and position in flat,
              f"{name}: detailed role {company!r} — {position!r} is incomplete")
        check(flatten(job["scope"][lang])[:60] in flat,
              f"{name}: scope of {company!r} is missing")
        for item in job["achievements"]:
            if item.get("featured", False):
                check(flatten(item[lang])[:60] in flat,
                      f"{name}: featured achievement of {company!r} is missing")

    for job in cv["experience"]:
        if not job["detailed"]:
            company = job.get("resume_company", job["company"])[lang]
            check(company in flat, f"{name}: earlier role {company!r} is missing")

    # The footer carries identity onto a page that may be read on its own.
    domain = re.sub(r"^https?://", "", cv["site"]["url"]).rstrip("/")
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

    meta = reader.metadata or {}
    for field in ("/Title", "/Author", "/Subject"):
        check(bool(meta.get(field)), f"{name}: document metadata {field} is empty")

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
        self.hreflang: set[str] = set()
        self.headings: list[tuple[int, str]] = []
        self.images: list[dict[str, str]] = []
        self.links: list[tuple[dict[str, str], str]] = []
        self.jsonld: list[dict] = []
        self.lang = ""
        self.text: list[str] = []
        self.summaries = 0
        self._open: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "meta" and "name" in a:
            self.meta[a["name"]] = a.get("content", "")
        elif tag == "link" and a.get("rel") == "alternate":
            self.hreflang.add(a.get("hreflang", ""))
        elif tag == "img":
            self.images.append(a)
        if tag not in self.VOID:
            self._open.append((tag, a))

    def handle_endtag(self, tag):
        while self._open:
            open_tag, attrs = self._open.pop()
            if open_tag == tag:
                break

    def handle_data(self, data):
        self.text.append(data)
        for tag, attrs in reversed(self._open):
            if re.fullmatch(r"h[1-6]", tag):
                self.headings.append((int(tag[1]), data.strip()))
                break
            if tag == "a":
                self.links.append((attrs, data.strip()))
                break
            if tag == "script" and attrs.get("type") == "application/ld+json":
                self.jsonld.append(json.loads(data))
                break
            if tag == "p" and any(
                    "summary-stack" in a.get("class", "") for _, a in self._open):
                self.summaries += 1
                break


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

    check(page.lang == lang, f"{where}: <html lang> is {page.lang!r}, expected {lang!r}")
    check(page.hreflang == {"en", "ru", "x-default"},
          f"{where}: hreflang set is {sorted(page.hreflang)}")

    # head.html hands summary[0] to the meta tag and the share cards, where a
    # search snippet is cut at roughly 160 characters.
    lead = cv["summary"][0][lang]
    check(page.meta.get("description") == lead,
          f"{where}: meta description is not the lead summary paragraph")
    check(page.summaries == len(cv["summary"]),
          f"{where}: {page.summaries} summary paragraphs rendered, "
          f"{len(cv['summary'])} in the data")

    levels = [level for level, _ in page.headings]
    check(levels.count(1) == 1, f"{where}: {levels.count(1)} <h1> elements, expected one")
    for before, after in zip(levels, levels[1:]):
        if after > before:
            check(after == before + 1,
                  f"{where}: heading level jumps from h{before} to h{after}")

    for image in page.images:
        check(bool(image.get("alt", "").strip()),
              f"{where}: <img src={image.get('src')!r}> has no alt text")
    for attrs, label in page.links:
        check(bool(label or attrs.get("aria-label") or attrs.get("title")),
              f"{where}: <a href={attrs.get('href')!r}> has no accessible name")

    # The website shows every skill; the PDF shows the featured subset.
    for skill in skills(featured_only=False):
        check(skill in text, f"{where}: skill {skill!r} is not rendered")

    check(len(page.jsonld) == 1, f"{where}: expected exactly one JSON-LD block")
    for profile in page.jsonld:
        check(profile.get("jobTitle") == cv["target"]["position"][lang],
              f"{where}: JSON-LD jobTitle does not match target.position")
        check(profile.get("description") == lead,
              f"{where}: JSON-LD description is not the lead summary paragraph")
        same_as = set(profile.get("sameAs", []))
        for contact in cv["personal"]["profiles"]:
            check(contact["url"] in same_as,
                  f"{where}: JSON-LD sameAs omits {contact['network']}")
        knows = set(profile.get("knowsAbout", []))
        missing = sorted(set(skills(featured_only=False)) - knows)
        check(not missing, f"{where}: JSON-LD knowsAbout omits {missing[:3]}")

if problems:
    for problem in problems:
        print(f"build: {problem}")
    sys.exit(1)

print("build: artifacts match the rendering rules")
