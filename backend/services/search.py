from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from services.cache import merge_listing, save_listings_cache
from services.geo import distance_miles, prefilter_radius_miles
from services.rentcast import search_all_listings
from services.routing import travel_minutes_matrix


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

    For each tether location: pull the *complete* set of nearby rentals from RentCast
    (paginated), then for each distinct commute mode ask Google Routes for real travel
    times over the listings within that mode's reach. A listing is kept if it satisfies
    ANY criterion (OR) from ANY location, carrying one tag per (location, mode) it
    qualifies under -- so a walk-near listing also shows its transit time.

    Returns the merged listings plus usage counts so callers can manage quota. Also
    writes a listings_cache.json snapshot for the static export tooling.
    """
    filters = filters or {}

    # Each distinct routing key gets its own reach: the widest radius among the criteria
    # that share it. We fetch RentCast once at the overall max radius, then route each
    # mode only over the listings within that mode's radius.
    key_radius: dict[tuple[str, Optional[str]], float] = {}
    for c in criteria:
        k = _routing_key(c)
        r = prefilter_radius_miles(c["mode"], float(c["max_minutes"]))
        key_radius[k] = max(key_radius.get(k, 0.0), r)
    max_radius = max(key_radius.values())

    merged: dict[str, Any] = {}
    location_summaries: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    rentcast_requests_used = 0
    routing_elements_used = 0

    for index, loc in enumerate(locations):
        loc_id = loc.get("id") or f"loc_{index + 1}"
        label = loc.get("label") or f"Location {index + 1}"
        origin = (loc["lat"], loc["lng"])

        pool, pages = await search_all_listings(
            latitude=loc["lat"],
            longitude=loc["lng"],
            radius_miles=max_radius,
            min_rent=filters.get("min_rent"),
            max_rent=filters.get("max_rent"),
            min_beds=filters.get("min_beds"),
            max_beds=filters.get("max_beds"),
        )
        rentcast_requests_used += pages
        location_summaries.append(
            {"id": loc_id, "label": label, "lat": loc["lat"], "lng": loc["lng"]}
        )
        if not pool:
            continue

        # Straight-line distance of every pooled listing to this anchor, reused below.
        dist = [distance_miles(origin, (p["lat"], p["lng"])) if p.get("lat") is not None and p.get("lng") is not None else None for p in pool]

        # minutes_by_key[key][pool_index] = travel minutes (only for in-radius listings).
        minutes_by_key: dict[tuple[str, Optional[str]], dict[int, Optional[float]]] = {}
        for key in key_radius:
            mode, transit_modes = key
            subset_idx = [i for i, d in enumerate(dist) if d is not None and d <= key_radius[key]]
            origins = [(pool[i]["lat"], pool[i]["lng"]) for i in subset_idx]
            grid = await travel_minutes_matrix(
                origins, [origin], mode=mode, transit_modes=transit_modes
            )
            routing_elements_used += len(subset_idx)
            minutes_by_key[key] = {i: grid[j][0] for j, i in enumerate(subset_idx)}

        for i, candidate in enumerate(pool):
            for criterion in criteria:
                minutes = minutes_by_key[_routing_key(criterion)].get(i)
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
        "rentcast_requests_used": rentcast_requests_used,
        "routing_elements_used": routing_elements_used,
    }
