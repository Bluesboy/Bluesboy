// LOCAL PATCH (Bluesboy/cv): a prose "About" list, same shape as
// `focus-areas` — a top-level array of content items under a heading.
// Upstream has no equivalent: `interests` carries the {name, keywords}
// shape, which is wrong for whole sentences.

#let _about(items, labels) = if items.len() > 0 [
  == #labels.about

  #for item in items [- #item]
]
