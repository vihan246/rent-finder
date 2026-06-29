from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from services.cache import merge_listing, save_listings_cache
from services.geo import candidates_within_radius, prefilter_radius_miles
from services.rentcast import search_listings
from services.routing import travel_minutes_matrix

RENTCAST_LIMIT = 100


async def run_search(
    locations: list[dict[str, Any]],
    commute: dict[str, Any],
    filters: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Core search used by both POST /search and the demo script.

    For each tether location: pull nearby rentals from RentCast, cheaply pre-filter by
    straight-line distance, then ask Google Routes for the real travel time in the
    chosen mode and keep listings within the time budget (ANY-match across locations).

    Returns the merged listings plus usage counts so callers can manage quota. Also
    writes a listings_cache.json snapshot for the static export tooling.
    """
    filters = filters or {}
    mode = commute["mode"]
    max_minutes = float(commute["max_minutes"])
    transit_modes = commute.get("transit_modes")

    radius = prefilter_radius_miles(mode, max_minutes)

    merged: dict[str, Any] = {}
    location_summaries: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    routing_elements_used = 0

    for index, loc in enumerate(locations):
        loc_id = loc.get("id") or f"loc_{index + 1}"
        label = loc.get("label") or f"Location {index + 1}"
        origin = (loc["lat"], loc["lng"])

        raw = await search_listings(
            latitude=loc["lat"],
            longitude=loc["lng"],
            radius_miles=radius,
            min_rent=filters.get("min_rent"),
            max_rent=filters.get("max_rent"),
            min_beds=filters.get("min_beds"),
            max_beds=filters.get("max_beds"),
            limit=RENTCAST_LIMIT,
        )

        candidates = candidates_within_radius(raw, origin, radius)
        location_summaries.append(
            {"id": loc_id, "label": label, "lat": loc["lat"], "lng": loc["lng"]}
        )
        if not candidates:
            continue

        origins = [(c["lat"], c["lng"]) for c in candidates]
        grid = await travel_minutes_matrix(
            origins, [origin], mode=mode, transit_modes=transit_modes
        )
        routing_elements_used += len(candidates)

        for candidate, row in zip(candidates, grid):
            minutes = row[0]
            if minutes is not None and minutes <= max_minutes:
                merge_listing(merged, candidate, loc_id, label, minutes, mode)

    now = datetime.now(timezone.utc).isoformat()
    save_listings_cache(
        {
            "last_refreshed_at": now,
            "commute": commute,
            "locations": location_summaries,
            "listings": merged,
        }
    )

    return {
        "last_refreshed_at": now,
        "commute": commute,
        "locations": location_summaries,
        "listings": list(merged.values()),
        "count": len(merged),
        "errors": errors,
        "rentcast_requests_used": len(locations),
        "routing_elements_used": routing_elements_used,
    }
