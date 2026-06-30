// Anchors (tether locations) are labelled A, B, C … in display order so pills and the
// map can reference them compactly instead of repeating long addresses.
export function anchorLetter(index) {
  let i = index + 1
  let s = ''
  while (i > 0) {
    const rem = (i - 1) % 26
    s = String.fromCharCode(65 + rem) + s
    i = Math.floor((i - 1) / 26)
  }
  return s
}

// { locationId: "A" } keyed by display order of the given locations.
export function buildAnchorLetters(locations) {
  const map = {}
  locations.forEach((loc, i) => {
    map[loc.id] = anchorLetter(i)
  })
  return map
}
