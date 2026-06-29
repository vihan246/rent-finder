from __future__ import annotations

from typing import Any


def apply_rent_bed_filters(
    listings: list[dict[str, Any]],
    *,
    min_rent: float | None = None,
    max_rent: float | None = None,
    min_beds: float | None = None,
    max_beds: float | None = None,
) -> list[dict[str, Any]]:
    if min_rent is not None:
        listings = [l for l in listings if l["rent"] is not None and l["rent"] >= min_rent]
    if max_rent is not None:
        listings = [l for l in listings if l["rent"] is not None and l["rent"] <= max_rent]
    if min_beds is not None:
        listings = [l for l in listings if l["beds"] is not None and l["beds"] >= min_beds]
    if max_beds is not None:
        listings = [l for l in listings if l["beds"] is not None and l["beds"] <= max_beds]
    return listings
