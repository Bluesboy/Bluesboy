#let lang = sys.inputs.at("lang", default: "en")
#let source = yaml("data/cv.yaml")
#let ui = yaml("data/ui.yaml")
#let t(value) = value.at(lang)
#let l(key) = t(ui.at(key))
#let featured(item) = item.at("featured", default: false)
#let place(value) = {
  let city = t(value.city)
  if "country" in value { city + ", " + t(value.country) } else { city }
}
#let month(value) = {
  let parts = value.split("-")
  ui.months.short.at(lang).at(int(parts.at(1)) - 1) + " " + parts.at(0)
}
#let period(value) = (
  month(value.start)
    + " – "
    + if value.end == none {
      l("present")
    } else { month(value.end) }
)
#let accent = rgb("#0F6A73")
#let ink = rgb("#25313A")
#let muted = rgb("#52616B")
#let core = source.skills.map(group => group.items.filter(featured)).flatten()
#let domain = source.site.url.replace(regex("^https?://"), "").trim("/")

#set document(
  title: t(source.personal.full_name) + " — " + l("resumeTitle"),
  author: t(source.personal.full_name),
  description: source.summary.map(t).join(" "),
  keywords: core.map(item => item.name) + (source.site.url,),
  date: none,
)
#set page(
  paper: "a4",
  margin: (x: 15mm, y: 15mm),
  footer: context align(center, text(size: 8pt, fill: muted)[
    #t(source.personal.full_name) · #link(source.site.url, domain) · #counter(page).display("1/1", both: true)
  ]),
)
#set text(
  font: "IBM Plex Sans",
  size: 11pt,
  fill: ink,
  lang: lang,
  hyphenate: false,
)
#set par(leading: 0.66em, spacing: 0.6em)
#set list(indent: 0pt, body-indent: 1em, tight: false, spacing: 0.45em)
#show link: set text(fill: accent)
#show heading.where(level: 1): it => block(
  above: 0.9em,
  below: 0.45em,
  sticky: true,
)[
  #text(size: 11.5pt, weight: "bold", fill: accent, it.body)
  #v(-0.4em)
  #line(length: 100%, stroke: 0.5pt + accent)
]
#show heading.where(level: 2): set text(size: 12pt, weight: "bold")
#show heading.where(level: 2): set block(above: 1em, below: 0.5em)

#set par(spacing: 0.45em)
#text(size: 25pt, weight: "bold", t(source.personal.full_name))
#parbreak()
#text(size: 13pt, weight: "bold", fill: accent, t(source.target.position))
#parbreak()
#let contacts = (
  link("mailto:" + source.personal.email, source.personal.email),
)
#for profile in source.personal.profiles {
  if lang in profile.at("resume_languages", default: ("en", "ru")) {
    contacts.push(link(profile.url, profile.at(
      "label",
      default: profile.network,
    )))
  }
}
#contacts.push(link(source.site.url, domain))
#text(size: 10pt, contacts.join([ · ]))
#parbreak()
#text(
  size: 10pt,
  fill: muted,
)[#place(source.personal.location) · #t(source.target.work_format)]
#set par(spacing: 0.6em)

#heading(level: 1, l("summary"))
#for paragraph in source.summary {
  par(t(paragraph))
}

#heading(level: 1, l("coreSkills"))
#for group in source.skills {
  let items = group.items.filter(featured)
  if items.len() > 0 {
    block(above: 0pt, below: 0.5em, breakable: false)[
      #strong(t(group.area) + ":") #items.map(item => item.name).join(", ")
    ]
  }
}

#heading(level: 1, l("experience"))
#for (index, job) in (
  source.experience.filter(item => item.detailed).enumerate()
) {
  let achievements = job.achievements.filter(featured).map(t)
  // A role is read as one unit: keep it whole, and start the next page when
  // it no longer fits rather than splitting its results off the heading.
  block(
    breakable: false,
    above: if index == 0 { 0pt } else { 1.8em },
    {
      let company = if job.website == "" { t(job.company) } else {
        link("https://" + job.website, t(job.company))
      }
      heading(level: 2)[#company — #t(job.position)]
      block(above: 0pt, below: 0.55em)[
        #text(size: 9.5pt, fill: muted)[
          #period(job.period) · #place(job.location)#if job.at("remote", default: false) { " · " + l("remote") }
        ]
      ]
      block(above: 0pt, below: 0.55em, t(job.scope))
      list(..achievements)
    },
  )
}

#heading(level: 1, l("earlier"))
#for job in source.experience.filter(item => not item.detailed) {
  block(breakable: false, above: 0pt, below: 0.7em)[
    #text(fill: muted, period(job.period)) — #strong(t(job.at("resume_company", default: job.company))) — #t(job.position)
  ]
}

#heading(level: 1, l("education"))
#for item in source.education {
  block(breakable: false, above: 0pt, below: 0.7em)[
    #item.year — #strong(t(item.institution))
    #parbreak()
    #t(item.specialization) · #t(item.level)
  ]
}

#heading(level: 1, l("languages"))
#for item in source.languages {
  par(t(item.language) + " — " + t(item.level))
}
