from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

import config

ROUTE_MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"

# Google Routes travelMode values for the three commute modes we expose.
TRAVEL_MODE = {"walk": "WALK", "drive": "DRIVE", "transit": "TRANSIT"}

# Google's TransitTravelMode enum. MUNI Metro / streetcars are LIGHT_RAIL, BART is
# SUBWAY/RAIL -- so "rail only" is everything except BUS, and "bus" adds BUS back in.
RAIL_TRANSIT_MODES = ["SUBWAY", "TRAIN", "LIGHT_RAIL", "RAIL"]

# computeRouteMatrix caps elements (origins x destinations) per request: 100 for
# TRANSIT, 625 otherwise. We always query against a single destination (the anchor),
# so these double as the max number of origins (listings) per request.
TRANSIT_MAX_ELEMENTS = 100
DEFAULT_MAX_ELEMENTS = 625

# Cap concurrent matrix requests so a big pool doesn't open hundreds of sockets at once.
MAX_CONCURRENCY = 8


class RoutingError(Exception):
    pass


LatLng = tuple[float, float]


def _allowed_transit_modes(transit_modes: Optional[str]) -> list[str]:
    # transit_modes: "rail" -> rail only; anything else (e.g. "bus") -> include buses.
    if transit_modes == "rail":
        return list(RAIL_TRANSIT_MODES)
    return RAIL_TRANSIT_MODES + ["BUS"]


def _waypoint(point: LatLng) -> dict[str, Any]:
    lat, lng = point
    return {"waypoint": {"location": {"latLng": {"latitude": lat, "longitude": lng}}}}


def _duration_to_minutes(duration: Any) -> Optional[float]:
    # Routes durations look like "1234s". Be defensive about missing/odd values.
    if not isinstance(duration, str) or not duration.endswith("s"):
        return None
    try:
        return round(float(duration[:-1]) / 60, 1)
    except ValueError:
        return None


def _next_weekday_departure() -> str:
    """A fixed near-future weekday 9am Pacific (as RFC3339 UTC). Transit times depend on
    departure time / schedules, so pinning one makes results deterministic and rail-vs-bus
    comparable instead of drifting with the real-time clock between requests."""
    # Pacific is UTC-7 (PDT) for most of the year; exactness here doesn't matter, we just
    # need a stable, future weekday morning. 9am PDT == 16:00 UTC.
    now = datetime.now(timezone.utc)
    target = now.replace(hour=16, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    while target.weekday() >= 5:  # skip Sat/Sun
        target += timedelta(days=1)
    return target.isoformat().replace("+00:00", "Z")


async def travel_minutes_matrix(
    origins: list[LatLng],
    destinations: list[LatLng],
    *,
    mode: str,
    transit_modes: Optional[str] = None,
) -> list[list[Optional[float]]]:
    """Travel time in minutes from each origin to each destination for `mode`, via
    Google's computeRouteMatrix (transit included). Returns a len(origins) x
    len(destinations) grid; an entry is None when no route exists.

    Origins are chunked to the per-request element limit (100 for transit, 625 otherwise)
    and the chunks are issued concurrently.
    """
    if mode not in TRAVEL_MODE:
        raise RoutingError(f"Unsupported commute mode: {mode!r}")
    if not config.GOOGLE_ROUTES_API_KEY:
        raise RoutingError("GOOGLE_ROUTES_API_KEY is not set")
    if not origins or not destinations:
        return [[None] * len(destinations) for _ in origins]

    max_elements = TRANSIT_MAX_ELEMENTS if mode == "transit" else DEFAULT_MAX_ELEMENTS
    chunk_size = max(1, max_elements // len(destinations))
    chunks = [(i, origins[i : i + chunk_size]) for i in range(0, len(origins), chunk_size)]

    grid: list[list[Optional[float]]] = [[None] * len(destinations) for _ in origins]
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async with httpx.AsyncClient(timeout=60.0) as client:

        async def run_chunk(start: int, chunk_origins: list[LatLng]) -> None:
            async with semaphore:
                elements = await _matrix_request(
                    client, chunk_origins, destinations, mode, transit_modes
                )
            for el in elements:
                i = el.get("originIndex")
                j = el.get("destinationIndex")
                if i is None or j is None:
                    continue
                if el.get("condition") == "ROUTE_EXISTS":
                    grid[start + i][j] = _duration_to_minutes(el.get("duration"))

        await asyncio.gather(*(run_chunk(start, ch) for start, ch in chunks))

    return grid


async def _matrix_request(
    client: httpx.AsyncClient,
    origins: list[LatLng],
    destinations: list[LatLng],
    mode: str,
    transit_modes: Optional[str],
) -> list[dict[str, Any]]:
    body: dict[str, Any] = {
        "origins": [_waypoint(o) for o in origins],
        "destinations": [_waypoint(d) for d in destinations],
        "travelMode": TRAVEL_MODE[mode],
    }
    if mode == "transit":
        body["transitPreferences"] = {"allowedTravelModes": _allowed_transit_modes(transit_modes)}
        body["departureTime"] = _next_weekday_departure()

    headers = {
        "X-Goog-Api-Key": config.GOOGLE_ROUTES_API_KEY,
        "X-Goog-FieldMask": "originIndex,destinationIndex,duration,condition",
        "Content-Type": "application/json",
    }

    try:
        response = await client.post(ROUTE_MATRIX_URL, json=body, headers=headers)
    except httpx.HTTPError as exc:
        raise RoutingError(f"Google Routes request failed: {exc}") from exc

    if response.status_code != 200:
        raise RoutingError(
            f"Google Routes returned {response.status_code}: {response.text[:300]}"
        )

    try:
        elements = response.json()
    except ValueError as exc:
        raise RoutingError("Google Routes returned a non-JSON response") from exc

    if not isinstance(elements, list):
        raise RoutingError(f"Unexpected route matrix shape: {type(elements)}")
    return elements
