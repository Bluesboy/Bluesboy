#import "@preview/altacv:1.6.0": alta

#let lang = sys.inputs.at("lang", default: "en")
#let version = sys.inputs.at("version", default: "dev")
#let source = yaml("data/cv.yaml")
// Interface strings live beside the CV data so the website renders the
// same labels; both used to keep private copies that had already drifted.
#let ui = yaml("data/ui.yaml")

#let t(value) = if type(value) == dictionary { value.at(lang) } else { value }
#let take(items, count) = items.slice(0, calc.min(items.len(), count))
#let localize(items) = items.map(t)
// City and country live apart in the data so the website can emit a real
// PostalAddress; the PDF wants them joined. `country` is absent for a
// city that is its own territory.
#let place(value) = {
  let city = t(value.city)
  if "country" in value { city + ", " + t(value.country) } else { city }
}
#let section-label(value) = text(size: 10.5pt, value)
#let l(key) = t(ui.at(key))

#let detailed-work = (
  source
    .experience
    .filter(item => item.detailed)
    .map(item => {
      let responsibilities = localize(take(item.responsibilities, 3))
      let achievements = localize(take(item.achievements, 3))
      let entry = (
        name: t(item.company),
        position: text(size: 10.5pt, t(item.position)),
        // `remote` is optional and only ever true; absent means on-site.
        // Hugo treats a missing key as falsy, Typst panics on it.
        location: place(item.location)
          + if item.at("remote", default: false) {
            " · " + l("remote")
          } else { "" },
        startDate: item.period.start,
        highlights: (
          strong(l("responsibilities")) + text(": " + responsibilities.at(0)),
          responsibilities.at(1),
          responsibilities.at(2),
          strong(l("achievements")) + text(": " + achievements.at(0)),
          achievements.at(1),
          achievements.at(2),
        ),
      )
      if item.website != "" {
        entry += (
          url: if item.website.starts-with("http") {
            item.website
          } else {
            "https://" + item.website
          },
        )
      }
      if item.period.end != none {
        entry += (endDate: item.period.end)
      }
      entry
    })
)

#let earlier-work = (
  source
    .experience
    .filter(item => not item.detailed)
    .map(item => {
      let end = if item.period.end == none { "" } else {
        "–" + item.period.end.slice(0, 4)
      }
      (
        item.period.start.slice(0, 4),
        end,
        ": ",
        t(item.company),
        " — ",
        t(item.position),
      ).join()
    })
)

#let profiles = {
  let entries = source.personal.profiles.map(profile => (
    network: if profile.network == "HeadHunter" { "website" } else {
      profile.network
    },
    username: profile.at("label", default: profile.network),
    url: profile.url,
  ))
  if source.site.url != "" {
    entries.push((
      network: "website",
      username: "Full CV",
      url: source.site.url,
    ))
  }
  entries
}

#let resume = (
  basics: (
    name: t(source.personal.full_name),
    label: t(source.target.position)
      + " · "
      + t(source.target.work_format)
      + " · "
      + l("salary")
      + ": "
      + t(source.target.salary),
    summary: t(source.summary.at(0)),
    email: source.personal.email,
    image: path(source.personal.avatar),
  )
    + if "phone" in source.personal { (phone: source.personal.phone) } else {
      (:)
    }
    + if profiles.len() > 0 {
      (profiles: profiles)
    } else {
      (:)
    },
  work: detailed-work,
  focusAreas: earlier-work,
  skills: source.skills.map(group => (
    name: t(group.area),
    keywords: group.items,
  )),
  certificates: source
    .skills
    .map(group => group.items.map(item => (
      name: item,
      issuer: t(group.area),
    )))
    .sum(default: ()),
  about: localize(source.about),
  languages: source.languages.map(item => (
    language: t(item.language),
    fluency: t(item.level),
    rating: item.rating,
  )),
  education: source.education.map(item => (
    institution: t(item.institution),
    studyType: t(item.specialization),
    endDate: item.year,
    score: t(item.level),
  )),
  meta: (
    canonical: source.site.url,
    version: version,
  ),
)

#let labels = (
  work: section-label(l("experience")),
  focusAreas: section-label(l("earlier")),
  present: l("present"),
  certificates: section-label(l("coreSkills")),
  languages: section-label(l("languages")),
  education: section-label(l("education")),
  about: section-label(l("about")),
  months: ui.months.short.at(lang),
)

// Presentation tweaks that used to live here as show rules matching
// AltaCV internals now live in the vendored theme itself:
// solid accent skill-group dividers -> internal/primitives.typ,
// the one-line role/salary header  -> internal/header.typ,
// the Telegram profile glyph        -> internal/icons.typ.

#alta(
  resume,
  labels: labels,
  preferences: (
    font: "IBM Plex Sans",
    bodySize: 10pt,
    paper: "a4",
    margin: (x: 0.85cm, y: 0.55cm),
    accent: rgb("#0F6A73"),
    imageSize: 6em,
    imagePosition: "right",
    uppercaseName: false,
    dateFormat: "long",
    maxRating: 7,
    columnRatio: 0.70,
    // The grid holds only the long left column and the sidebar; the tail
    // runs full width, so page two is not stuck at 62% once the sidebar
    // has run out.
    leftColumnSections: ("work",),
    rightColumnSections: ("certificates", "languages"),
    fullWidthSections: ("focusAreas", "education", "about"),
    pageFooter: none,
  ),
)
