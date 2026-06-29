// Mirrors backend/services/filters.py::apply_rent_bed_filters -- used to narrow the
// already-fetched results client-side so tweaking rent/bed inputs doesn't re-query.
export function applyRentBedFilters(listings, { minRent, maxRent, minBeds, maxBeds } = {}) {
  let result = listings
  if (minRent != null) result = result.filter((l) => l.rent != null && l.rent >= minRent)
  if (maxRent != null) result = result.filter((l) => l.rent != null && l.rent <= maxRent)
  if (minBeds != null) result = result.filter((l) => l.beds != null && l.beds >= minBeds)
  if (maxBeds != null) result = result.filter((l) => l.beds != null && l.beds <= maxBeds)
  return result
}
