# Repository Rules

## Scope and terminology

- This is the GitHub profile repository `Bluesboy/Bluesboy`.
- The Hugo website is the full bilingual CV.
- The Typst PDFs are concise bilingual resumes.
- Use `CV` for the website and source data; use `Resume` for PDF artifacts.

## Source of truth

- `data/cv.yaml` is the only content source for Hugo and Typst.
- `data/ui.yaml` is the only interface-string source for both renderers.
- Do not duplicate CV content in templates, Markdown, or generated files.
- Never inline an interface label in a template; add a key to `data/ui.yaml`.
- Where the site and the PDF need different wording, add a second key rather than a second copy.
- Keep site title and description in `hugo.toml` only; the site has no content files.
- `scripts/validate_cv.py` checks font coverage for both data files.
- Keep shared values unlocalized. Store translated text as `{en, ru}`.
- Every localized field must contain both `en` and `ru`.
- Store months as `YYYY-MM`; use `end: null` for current employment.
- Store every location as `city` plus ISO-3166-1 alpha-2 `country_code`, with `country` localized.
- Add `remote: true` only to remote entries; an absent flag means on-site.
- Read it as `item.at("remote", default: false)` in Typst, which panics on a missing key.
- Omit `country` only when the city is its own territory, as for Hong Kong.
- Join city and country through `layouts/partials/location.html` or `place()` in `resume.typ`; never inline.
- Do not store calculated age, employment duration, total experience, or release version.
- Keep YAML sequences indentless: sequence indicators align with their mapping key.
- Update `schema/cv.schema.json` with every data-model change.
- Keep `minItems` a contract, never a snapshot of how much data exists today.
- Do not keep a field no renderer reads: either render it or drop it.
- Store skill items as plain strings; only the group names are localized.
- Validate data through `scripts/validate_cv.py` or `make test/schema`.
- Keep the semantic rules there in step with the renderers: period order, one open period,
  at least three responsibilities and achievements per detailed entry, URL shape.
- Install `jsonschema[format-nongpl]`; plain `jsonschema` silently skips `format` checks.

## Content rules

- Hugo renders all work entries and all responsibilities and achievements.
- PDF renders concise selected experience without a fixed page-count limit.
- Russian responsibilities use neutral noun-based wording where appropriate.
- Current English responsibilities use Present Simple; previous roles use Past Simple.
- Achievements describe completed results and use past tense.
- Responsibilities and achievements must remain visually distinguishable in PDF.
- Keep salary localized and separate from contact information.
- Phone is optional. Never reintroduce it when absent from `data/cv.yaml`.
- Do not store or render a birth date; it is personal data with no rendering purpose.
- Store every external profile, Telegram included, in `personal.profiles`.
- Use the optional `label` on a profile when the displayed text differs from the network name.
- Do not hardcode profile links or per-network branches in renderers.

## Hugo website

- Read data through `hugo.Data.cv`.
- English lives at `/`; Russian lives at `/ru/`.
- Production URL is `https://cv.shamil.pro/`; preserve `static/CNAME`.
- Do not show the website URL as a contact linking to the current page.
- Resume buttons point to stable GitHub Release assets, not Pages copies.
- Keep the site responsive, semantic, accessible, and JavaScript-free.
- Size type in `rem`, never in `px`, so a raised browser font size scales the whole page.
- Stack label/value pairs into one column below 560px.
- Keep fonts and icons local. Do not add CDN or runtime network dependencies.
- Website and PDF share one bundled family: IBM Plex Sans, weights 400 and 700 only.
- Serve fonts as WOFF2; keep the TTF faces for Typst and do not publish them.
- Regenerate bundled faces only through `scripts/build_fonts.py`, then commit them.
- Font Awesome is subset to the icons the vendored theme can request; widen it by rerunning that script.
- Keep the upstream Font Awesome package in `sources/fontawesome/` for regeneration.
- Widening the character coverage means widening `RANGES` in that script and rerunning it.
- Inline contact icons as SVG from `layouts/partials/icon.html`; do not ship icon webfonts to the browser.
- Read `personal.avatar` through `layouts/partials/image.html`; never hardcode the image path.
- Serve derived image variants only; do not ship the master image to the browser.
- Preserve canonical, hreflang, OpenGraph, and JSON-LD metadata.
- Derive JSON-LD from `data/cv.yaml`; keep `worksFor`, `alumniOf`, `knowsAbout`, and `knowsLanguage` populated.
- Keep `layouts/robots.txt` advertising the sitemap.
- Keep a bilingual `404.html`; mark it `noindex`.
- Define every colour as a token on `:root`; override only tokens inside the dark and print blocks.
- Light is the default theme; dark comes only from the topbar switch, never from `prefers-color-scheme`.
- Keep the theme switch CSS-only: a checkbox plus `:root:has(#theme-toggle:checked)`, guarded by `@supports`.
- Keep `theme-color` in step with `--page` for both colour schemes.
- Give language-switch links `lang` and `hreflang`.
- Use `--line-strong` for control borders (3:1) and `--line` only for decorative rules.
- Never hardcode `#fff` on an `--accent` or `--ink` fill; use `--on-accent` / `--on-ink`.
- Respect `prefers-reduced-motion`.
- Render external profiles as clickable contacts and include them in JSON-LD `sameAs`.
- Minification is configured in `hugo.toml`; do not rely on the `--minify` flag.
- Do not edit `build/`, `public/`, or other generated output manually.

## PDF resumes

- `resume.typ` adapts `data/cv.yaml`; it is presentation logic, not content storage.
- Build with local fonts through `--font-path assets/fonts --ignore-system-fonts`.
- Never depend on a system font; the build must produce identical output on any machine.
- Typst packages are vendored under `vendor/typst` and resolved with `--package-path`.
- Never restore a network package fetch; the PDF build must work offline.
- Mark every edit to a vendored package with a `LOCAL PATCH (Bluesboy/cv)` comment.
- Keep presentation overrides in the vendored sources, not as show rules matching package internals.
- Exclude `vendor/` from `make fmt` and `make lint`.
- Preserve EN/RU output names:
  - `shamil-sattarov-resume-en.pdf`
  - `shamil-sattarov-resume-ru.pdf`
- Show the web URL as the linked text `Full CV`.
- Keep salary outside the contact bar.
- Keep the contact bar on one line; omit location from it.
- Preserve clickable GitHub, LinkedIn, HeadHunter, Telegram, and `Full CV` links.
- Keep section headings smaller than the candidate name and role headings.
- Keep section order: detailed experience, earlier experience, education.
- Keep skill groups as named subsections with solid divider lines.
- Keep both PDFs concise, readable, and free of unnecessary page breaks; preserve clickable links.

## Build interface

- Use the `Makefile` as the local and CI entry point.
- `make preview`: Hugo development server.
- `make build`: website and both PDFs.
- `make fmt`: format Typst.
- `make lint`: YAML, Actions, and Typst lint.
- `make ci VERSION=v1.0.0`: schema validation and complete reproducible build.
- Preserve the Makefile style: section separators, `#--` headings, slash targets, and `##` help descriptions.

## Release workflow

- Use Conventional Commits and Cocogitto semantic versioning.
- First release is `v1.0.0`; later versions come from `cog bump --auto`.
- Cocogitto creates a tag on the merge commit; it does not create a bump commit.
- A merge to `master` builds, releases both PDFs plus `SHA256SUMS`, and deploys Pages.
- Keep release and Pages deployment in one workflow.
- Keep Git history checkout complete with `fetch-depth: 0`.
- Do not add GoReleaser or tracked copies of generated PDFs.

## Required verification

- After relevant changes, run `make fmt`, `make lint`, and `make ci VERSION=v1.0.0`.
- Run `git diff --check` before completion.
- For PDF changes, verify page counts and visually inspect every page in EN and RU.
- For link changes, verify PDF annotations and generated Hugo URLs.
- Do not commit, tag, push, or create a release unless explicitly requested.

## Licensing

- Preserve attribution for AltaCV, Almeida CV, and Font Awesome in `LICENSE`.
- MIT covers repository software only. Personal CV data and avatar remain excluded.
