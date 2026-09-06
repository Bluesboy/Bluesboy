#import "lib-gen-map.typ": *

// Currently, we assume there is no need to enable Pro sets for only a part of the document,
// so no method is provided to disable Pro sets
#let _fa_use_pro = state("_fa_use_pro", false)
#let fa-use-pro() = {
  _fa_use_pro.update(true)
}

#let _fa_version = state("_fa_version", "7")
#let fa-version(version) = {
  _fa_version.update(version)
}

/// Render a Font Awesome icon by its name or unicode
///
/// Parameters:
/// - `name`: The name of the icon
///   - This can be name in string or unicode of the icon
/// - `solid`: Whether to use the solid version of the icon
/// - `fa-icon-map`: The map of icon names to unicode
///   - Default is a map generated from FontAwesome metadata
///   - *Not recommended* You can provide your own map to override it
/// - `..args`: Additional arguments to pass to the `text` function
///
/// Returns: The rendered icon as a `text` element
#let fa-icon(
  name,
  solid: false,
  fa-icon-map: (:),
  ..args,
) = (
  context {
    let font_base = "Font Awesome " + _fa_version.get()

    // LOCAL PATCH (Bluesboy/cv): this repository vendors only
    // "Font Awesome N Free Solid" and "Font Awesome N Brands" under
    // assets/fonts. Upstream also lists the Regular face ("Font Awesome
    // N Free") in the non-solid branch, which we do not ship, so every
    // brand icon emitted an "unknown font family" warning. Non-solid
    // icons here are always brand marks, so the Regular face is dropped
    // rather than shipping a third OTF for glyphs we never use.
    let default_fonts = if solid {
      (font_base + " Free Solid", font_base + " Brands")
    } else {
      (font_base + " Brands",)
    }

    if _fa_use_pro.get() {
      // TODO: Help needed to test following fonts
      // TODO: FA 7 adds more style for Pro sets
      default_fonts += (
        font_base
          + " Pro"
          + if solid {
            " Solid"
          },
        font_base
          + " Duotone"
          + if solid {
            " Solid"
          },
        font_base
          + " Sharp"
          + if solid {
            " Solid"
          },
        font_base
          + " Sharp Duotone"
          + if solid {
            " Solid"
          },
      )
    }

    let fa-icon-map-final = if fa-icon-map.len() > 0 {
      fa-icon-map
    } else {
      let version = _fa_version.get()
      fa-icon-map-common + fa-icon-map-version.at(version, default: (:))
    }

    text(
      font: default_fonts, // If you see warning here, please check whether the FA font is installed

      // TODO: We might need to check whether this is needed
      weight: if solid { 900 } else { 400 },
      // If the name is in the map, use the unicode from the map
      // If not, pass the name and let the ligature feature handle it
      fa-icon-map-final.at(name, default: name),
      ..args,
    )
  }
)
