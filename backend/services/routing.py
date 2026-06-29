from __future__ import annotations

from typing import Any, Optional

import httpx

import config

ROUTE_MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
COMPUTE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

# Google Routes travelMode values for the three commute modes we expose.
TRAVEL_MODE = {"walk": "WALK", "drive": "DRIVE", "transit": "TRANSIT"}

# Google's TransitTravelMode enum. MUNI Metro / streetcars are LIGHT_RAIL, BART is
# SUBWAY/RAIL -- so "rail only" is everything except BUS, and "bus" adds BUS back in.
RAIL_TRANSIT_MODES = ["SUBWAY", "TRAIN", "LIGHT_RAIL", "RAIL"]


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


async def travel_minutes_matrix(
    origins: list[LatLng],
    destinations: list[LatLng],
    *,
    mode: str,
    transit_modes: Optional[str] = None,
) -> list[list[Optional[float]]]:
    """Travel time in minutes from each origin to each destination for `mode`.

    Returns a len(origins) x len(destinations) grid; an entry is None when no
    route exists (e.g. no transit connection within the provider's search window).

    walk/drive use one computeRouteMatrix call. transit isn't supported by the
    matrix endpoint, so it falls back to one computeRoutes call per origin/destination
    pair -- callers should pre-filter candidates to keep that bounded.
    """
    if mode not in TRAVEL_MODE:
        raise RoutingError(f"Unsupported commute mode: {mode!r}")
    if not config.GOOGLE_ROUTES_API_KEY:
        raise RoutingError("GOOGLE_ROUTES_API_KEY is not set")
    if not origins or not destinations:
        return [[None] * len(destinations) for _ in origins]

    if mode == "transit":
        return await _transit_matrix(origins, destinations, transit_modes)
    return await _walk_drive_matrix(origins, destinations, mode)


async def _walk_drive_matrix(
    origins: list[LatLng], destinations: list[LatLng], mode: str
) -> list[list[Optional[float]]]:
    body = {
        "origins": [_waypoint(o) for o in origins],
        "destinations": [_waypoint(d) for d in destinations],
        "travelMode": TRAVEL_MODE[mode],
    }
    headers = {
        "X-Goog-Api-Key": config.GOOGLE_ROUTES_API_KEY,
        "X-Goog-FieldMask": "originIndex,destinationIndex,duration,condition",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
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

    grid: list[list[Optional[float]]] = [[None] * len(destinations) for _ in origins]
    for el in elements:
        i = el.get("originIndex")
        j = el.get("destinationIndex")
        if i is None or j is None:
            continue
        # condition ROUTE_NOT_FOUND (or missing) => unreachable for this pair.
        if el.get("condition") == "ROUTE_EXISTS":
            grid[i][j] = _duration_to_minutes(el.get("duration"))
    return grid


async def _transit_matrix(
    origins: list[LatLng],
    destinations: list[LatLng],
    transit_modes: Optional[str],
) -> list[list[Optional[float]]]:
    allowed = _allowed_transit_modes(transit_modes)
    headers = {
        "X-Goog-Api-Key": config.GOOGLE_ROUTES_API_KEY,
        "X-Goog-FieldMask": "routes.duration",
        "Content-Type": "application/json",
    }

    grid: list[list[Optional[float]]] = [[None] * len(destinations) for _ in origins]
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, origin in enumerate(origins):
            for j, dest in enumerate(destinations):
                body = {
                    "origin": {"location": {"latLng": {"latitude": origin[0], "longitude": origin[1]}}},
                    "destination": {"location": {"latLng": {"latitude": dest[0], "longitude": dest[1]}}},
                    "travelMode": "TRANSIT",
                    "transitPreferences": {"allowedTravelModes": allowed},
                }
                try:
                    response = await client.post(COMPUTE_ROUTES_URL, json=body, headers=headers)
                except httpx.HTTPError as exc:
                    raise RoutingError(f"Google Routes request failed: {exc}") from exc

                if response.status_code != 200:
                    raise RoutingError(
                        f"Google Routes returned {response.status_code}: {response.text[:300]}"
                    )

                try:
                    payload = response.json()
                except ValueError as exc:
                    raise RoutingError("Google Routes returned a non-JSON response") from exc

                routes = payload.get("routes") if isinstance(payload, dict) else None
                if routes:
                    grid[i][j] = _duration_to_minutes(routes[0].get("duration"))
    return grid
