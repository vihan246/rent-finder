from __future__ import annotations

import httpx

import config

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


class GeocodeError(Exception):
    pass


async def geocode_address(address: str) -> tuple[float, float]:
    """Looks up (lat, lng) for a free-text address via Nominatim (OpenStreetMap).

    Free and keyless, but Nominatim's usage policy requires a descriptive
    User-Agent and no more than ~1 request/second -- callers looping over
    multiple addresses must space out their own calls.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                NOMINATIM_URL,
                params={"q": address, "format": "json", "limit": 1},
                headers={"User-Agent": config.GEOCODE_USER_AGENT},
            )
    except httpx.HTTPError as exc:
        raise GeocodeError(f"Geocode request failed: {exc}") from exc

    if response.status_code != 200:
        raise GeocodeError(f"Nominatim returned {response.status_code}: {response.text[:300]}")

    try:
        results = response.json()
    except ValueError as exc:
        raise GeocodeError("Nominatim returned a non-JSON response") from exc

    if not isinstance(results, list) or not results:
        raise GeocodeError(f"No geocode results for address: {address!r}")

    try:
        lat = float(results[0]["lat"])
        lng = float(results[0]["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise GeocodeError(f"Unexpected Nominatim result shape: {results[0]!r}") from exc

    return lat, lng
