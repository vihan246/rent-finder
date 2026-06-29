import math
from typing import Any

EARTH_RADIUS_MILES = 3958.8

# Rough straight-line speeds (mph) used only to size a *generous* pre-filter radius
# before the paid routing call trims to real travel time. Deliberately high so we
# never exclude a reachable listing; precision comes from Google Routes afterwards.
MODE_RADIUS_SPEED_MPH = {"walk": 3.5, "transit": 25.0, "drive": 45.0}


def distance_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1 = a
    lat2, lng2 = b

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    sin_sq = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(sin_sq))


def prefilter_radius_miles(mode: str, max_minutes: float) -> float:
    """A generous straight-line radius for `mode` over `max_minutes`, used both to
    size the RentCast query and to cap how many candidates get a paid routing call."""
    speed = MODE_RADIUS_SPEED_MPH.get(mode, MODE_RADIUS_SPEED_MPH["drive"])
    return speed * (max_minutes / 60)


def candidates_within_radius(
    listings: list[dict[str, Any]],
    origin: tuple[float, float],
    radius_miles: float,
) -> list[dict[str, Any]]:
    """Cheap straight-line pre-filter: keep listings whose great-circle distance to
    `origin` is within `radius_miles`. Skips listings missing coordinates."""
    kept = []
    for listing in listings:
        if listing.get("lat") is None or listing.get("lng") is None:
            continue
        if distance_miles(origin, (listing["lat"], listing["lng"])) <= radius_miles:
            kept.append(listing)
    return kept
