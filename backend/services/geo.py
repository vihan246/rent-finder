import math
from typing import Any

EARTH_RADIUS_MILES = 3958.8


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


def filter_within_walk(
    listings: list[dict[str, Any]],
    origin: tuple[float, float],
    max_minutes: float,
    walk_speed_mph: float = 3.0,
) -> list[dict[str, Any]]:
    max_miles = walk_speed_mph * (max_minutes / 60)
    kept = []
    for listing in listings:
        if listing.get("lat") is None or listing.get("lng") is None:
            continue
        d = distance_miles(origin, (listing["lat"], listing["lng"]))
        if d <= max_miles:
            kept.append({**listing, "walk_minutes": round(d / walk_speed_mph * 60, 1)})
    return kept
