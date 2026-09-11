# Repository Rules

## Scope and terminology

- This is the GitHub profile repository `Bluesboy/Bluesboy`.
- The Hugo website is the full bilingual CV.
- The Typst PDFs are concise, platform-neutral bilingual resumes for direct applications and ATS/job boards.
- Use `CV` for the website and source data; use `Resume` for PDF artifacts.

## Source of truth

- `data/cv.yaml` is the only content source for Hugo and Typst.
- `data/ui.yaml` is the only interface-string source for both renderers.
- Do not duplicate CV content in templates, Markdown, or generated files.
- Never inline an interface label in a template; add a key to `data/ui.yaml`.
- Where the site and the PDF need different wording, add a second key rather than a second copy.
- Derive home page and social titles from `personal.full_name` and `target.position`,
  and descriptions from `summary`; `hugo.toml` holds only the site-name fallback and configuration.
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
- Store skills once as `{name, featured?}`; names are unlocalized, group headings are localized.
- Achievements store `{en, ru, featured?}`. In both models absent `featured` means false.
- PDF selects skills and achievements by `featured: true`, never by position or text matching.
- Hugo shows every skill once: featured items in Core stack, others in Additional technologies.
- Keep Additional technologies expanded, visually secondary, and full-width directly below Core stack.
- Render skill groups as compact semantic definition lists with comma-separated technology names,
  without chips; use two columns on desktop and one on mobile.
- Hugo shows all achievements; detailed-role responsibilities and `detailed: false` history
  live in native, initially collapsed `<details>` blocks, with localized summaries.
- Experience may have localized `scope`; every detailed role needs one plus at least one featured achievement.
- Earlier roles may have optional localized `resume_company` for a shorter PDF display name;
  default to `company`. Hugo always shows the full `company` name.
- Validate data through `scripts/validate_cv.py` or `make test/schema`.
- Mechanize a rule wherever it can be: shape in `schema/cv.schema.json`, data semantics in
  `scripts/validate_cv.py`, rendered output in `scripts/check_artifacts.py`.
- Keep the semantic rules there in step with the renderers: period order, one open period,
  at least three responsibilities and achievements per detailed entry, URL shape.
- Install `jsonschema[format-nongpl]`; plain `jsonschema` silently skips `format` checks.

## Content rules

- Hugo renders all work entries and all responsibilities and achievements.
- PDF renders concise selected experience without a fixed page-count limit.
- Russian responsibilities use neutral noun-based wording where appropriate.
- Current English responsibilities use Present Simple; previous roles use Past Simple.
- Achievements describe completed results and use past tense.
- Write `summary` as first-person prose in both languages; keep every list item verb-first with no subject.
- PDF detailed roles render a short scope and selected achievements; full responsibilities stay on the website.
- Do not store or render salary or citizenship; neither has a public CV use case.
- Avatar and About are website-only; preserve useful context without repeating the summary.
- Present About as How I work; keep unique factual information when removing repeated points.
- Store language proficiency as a localized semantic `level`, never a visual `rating`.
- Phone is optional. Never reintroduce it when absent from `data/cv.yaml`.
- Do not store or render a birth date; it is personal data with no rendering purpose.
- Store every external profile, Telegram included, in `personal.profiles`.
- Use the optional `label` on a profile when the displayed text differs from the network name.
- Do not hardcode profile links or per-network branches in renderers.
- Optional profile `resume_languages` lists PDF locales (`en`, `ru`); absent means both,
  an empty list means website-only. Hugo contacts and JSON-LD always include every profile.

## Hugo website

- Read data through `hugo.Data.cv`.
- English lives at `/`; Russian lives at `/ru/`.
- Production URL is `https://cv.shamil.pro/`; preserve `static/CNAME`.
- Do not show the website URL as a contact linking to the current page.
- Resume buttons point to stable GitHub Release assets, not Pages copies.
- Keep the site responsive, semantic, accessible, and JavaScript-free.
- Keep mobile DOM order: identity, summary, contacts with languages, core stack,
  additional technologies, How I work, experience, education. Keep both skill sections together
  on desktop too.
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
- The resume uses standard Typst elements, without a theme dependency.
- Retained Typst packages are vendored under `vendor/typst` and resolved with `--package-path` if used.
- Never restore a network package fetch; the PDF build must work offline.
- Mark every edit to a vendored package with a `LOCAL PATCH (Bluesboy/cv)` comment.
- Keep resume presentation in `resume.typ`; never use show rules matching vendored package internals.
- Exclude `vendor/` from `make fmt` and `make lint`.
- Preserve EN/RU output names:
  - `shamil-sattarov-resume-en.pdf`
  - `shamil-sattarov-resume-ru.pdf`
- Show the web URL as its linked domain, derived from `site.url`.
- Keep PDF metadata free of build identifiers; keywords carry the core skills and the CV domain.
- Keep a compact textual contact bar: email and visible profile network labels, followed by the domain.
- Keep contacts clickable; allow wrapping rather than shrinking text or clipping.
- Put location and work format on a separate compact line; no photo, salary, or citizenship in PDF.
- Preserve clickable profile links according to `resume_languages` and the CV domain in both locales.
- Keep a small footer with the localized name, linked CV domain, and dynamic current/total page count.
- Keep section headings smaller than the candidate name and role headings.
- Use a single column with semantic top-to-bottom plain-text extraction; no sidebars or content tables.
- Keep order: name, target role, contacts, summary, core expertise, experience, earlier experience, education, languages.
- Keep target positioning independent of historical job titles and grades; preserve factual historical titles.
- Render core skills as compact named text groups, aiming for about 30–35 visible items.
- Detailed roles show company, factual title, month-level dates, location/remote, scope, and featured achievements.
- Keep each detailed role whole: a role that no longer fits starts the next page, heading and results together.
- Earlier roles show dates, company, and title; do not expand their responsibilities or achievements.
- Language proficiency is plain text (language — level), without dots or progress bars.
- Target two readable pages per language through natural pagination, not forced page breaks or tiny type.
- Page one prioritizes the header, summary, core skills, and recent experience; no fixed page-one contract.
- Keep both PDFs concise, readable, and free of unnecessary page breaks; preserve clickable links.

## Build interface

- Use the `Makefile` as the local and CI entry point.
- Recipes run under `bash -eu -o pipefail`; do not rely on a failed command being ignored.
- `make lint` skips a missing linter, so gate CI on `deps/verify` instead.
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
- Validate commit messages in CI only, through `cog check` limited to `--from-latest-tag`;
  a malformed message turns the check red instead of blocking a deployment.
- Keep `check-latest-tag-only` set on the action so the range is stated in the workflow,
  not inferred from `from_latest_tag` in `cog.toml`.
- Keep `ignore_merge_commits` on; the synthetic subject GitHub builds for a pull request
  is not a conventional commit and would otherwise fail the check.
- Install cog in the release job with `install-only: true`: it must not re-check commits
  there, and the skipped step is also the one that overwrites the git identity.
- A merge to `master` builds, releases both PDFs plus `SHA256SUMS`, and deploys Pages.
- Keep release and Pages deployment in one workflow.
- Build before tagging: `version/plan` predicts the tag so a failed build leaves none behind.
- Deploy Pages on every push to master; release PDFs only when a bump is warranted.
- Keep the build a separate workflow step between `version/plan` and `version/release`.
- Do not move it into cog `pre_bump_hooks`: hooks never run on the non-bump pushes that
  still deploy Pages, a failing hook exits through a Rust panic, and the `|| true` in
  `version/release` would report that panic as "no bump-worthy commits".
- Hooks stay absent from `cog.toml`; `--dry-run` skips them, so `version/plan` and the
  local `version/*` targets must remain free of side effects.
- Grant `permissions` per job, never workflow-wide.
- Keep pinned tool versions in the Makefile; CI derives its cache key from `deps/versions`.
- Track the major tag of an action only while upstream keeps it on the newest stable release.
  Pin a patch when it drifts: `typst-community/setup-typst@v5.2.0` because `v5` moves onto
  prereleases, `cocogitto/cocogitto-action@v4.2.0` because `v4` is stale on cog 6.4.0.
- Keep Git history checkout complete with `fetch-depth: 0`.
- Do not add GoReleaser or tracked copies of generated PDFs.

## Required verification

- After relevant changes, run `make fmt`, `make lint`, and `make ci VERSION=v1.0.0`.
- Run `git diff --check` before completion.
- For PDF changes, verify page counts and visually inspect every page in EN and RU.
- `make test/build` runs `scripts/check_artifacts.py` over the built files: section order, literal
  core-skill keywords, clickable contacts per locale, the two-page budget, identity footers,
  duplicated lines, EN/RU parity, meta description, JSON-LD, heading levels, and image alt text.
- Inspect the rendered pages for what no check can see: spacing, widows, and where pages break.
- For link changes, verify PDF annotations and generated Hugo URLs.
- Do not commit, tag, push, or create a release unless explicitly requested.

## Licensing

- Preserve attribution for AltaCV, Almeida CV, and Font Awesome in `LICENSE`.
- MIT covers repository software only. Personal CV data and avatar remain excluded.
