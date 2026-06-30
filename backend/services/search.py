from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from services.cache import merge_listing, save_listings_cache
from services.geo import candidates_within_radius, prefilter_radius_miles
from services.rentcast import search_listings
from services.routing import travel_minutes_matrix

RENTCAST_LIMIT = 100


def _routing_key(criterion: dict[str, Any]) -> tuple[str, Optional[str]]:
    """A criterion's distinct Google Routes call: mode, plus transit sub-mode when it's
    transit (so 'transit rail' and 'transit bus' are separate, but two walk criteria
    share one call)."""
    mode = criterion["mode"]
    return (mode, criterion.get("transit_modes") if mode == "transit" else None)


async def run_search(
    locations: list[dict[str, Any]],
    criteria: list[dict[str, Any]],
    filters: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Core search used by both POST /search and the demo script.

    For each tether location: pull nearby rentals from RentCast, cheaply pre-filter by
    straight-line distance, then ask Google Routes for the real travel time for each
    distinct commute mode. A listing is kept if it satisfies ANY criterion (OR) from
    ANY location, carrying one tag per (location, mode) it qualifies under.

    Returns the merged listings plus usage counts so callers can manage quota. Also
    writes a listings_cache.json snapshot for the static export tooling.
    """
    filters = filters or {}

    # Generous pre-filter radius: the widest reach across all criteria, so no candidate
    # that any criterion could accept gets dropped before routing trims precisely.
    radius = max(
        prefilter_radius_miles(c["mode"], float(c["max_minutes"])) for c in criteria
    )
    # One routing call per distinct (mode, transit sub-mode); each criterion maps to one.
    routing_keys = list({_routing_key(c) for c in criteria})

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

        # Travel minutes per candidate, indexed by routing key (reused across criteria).
        minutes_by_key: dict[tuple[str, Optional[str]], list] = {}
        for mode, transit_modes in routing_keys:
            grid = await travel_minutes_matrix(
                origins, [origin], mode=mode, transit_modes=transit_modes
            )
            minutes_by_key[(mode, transit_modes)] = [row[0] for row in grid]
            routing_elements_used += len(candidates)

        for i, candidate in enumerate(candidates):
            for criterion in criteria:
                minutes = minutes_by_key[_routing_key(criterion)][i]
                if minutes is not None and minutes <= float(criterion["max_minutes"]):
                    merge_listing(merged, candidate, loc_id, label, minutes, criterion["mode"])

    now = datetime.now(timezone.utc).isoformat()
    save_listings_cache(
        {
            "last_refreshed_at": now,
            "criteria": criteria,
            "locations": location_summaries,
            "listings": merged,
        }
    )

    return {
        "last_refreshed_at": now,
        "criteria": criteria,
        "locations": location_summaries,
        "listings": list(merged.values()),
        "count": len(merged),
        "errors": errors,
        "rentcast_requests_used": len(locations),
        "routing_elements_used": routing_elements_used,
    }
