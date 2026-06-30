from __future__ import annotations

from typing import Any

import httpx

import config
from services.filters import apply_rent_bed_filters

RENTCAST_BASE_URL = "https://api.rentcast.io/v1"
LISTINGS_PATH = "/listings/rental/long-term"

# RentCast caps a single response at 500 and sorts by recency, not distance -- so a
# bounded query silently drops nearby listings. We paginate with offset to get the
# complete set within the radius. MAX_PAGES is a safety cap (500 * 10 = 5000 listings).
PAGE_SIZE = 500
MAX_PAGES = 10


class RentCastError(Exception):
    pass


def _normalize_listing(raw: dict[str, Any]) -> dict[str, Any]:
    raw_agent = raw.get("listingAgent")
    agent = (
        {
            "name": raw_agent.get("name"),
            "phone": raw_agent.get("phone"),
            "email": raw_agent.get("email"),
            "website": raw_agent.get("website"),
        }
        if isinstance(raw_agent, dict)
        else None
    )
    return {
        "id": raw.get("id") or raw.get("mlsNumber"),
        "address": raw.get("formattedAddress") or raw.get("addressLine1"),
        "lat": raw.get("latitude"),
        "lng": raw.get("longitude"),
        "rent": raw.get("price"),
        "beds": raw.get("bedrooms"),
        "baths": raw.get("bathrooms"),
        "sqft": raw.get("squareFootage"),
        "property_type": raw.get("propertyType"),
        "listed_date": raw.get("listedDate"),
        "url": raw.get("url") or raw.get("listingUrl"),
        "agent": agent,
    }


async def search_listings(
    *,
    latitude: float,
    longitude: float,
    radius_miles: float = 5.0,
    min_rent: float | None = None,
    max_rent: float | None = None,
    min_beds: float | None = None,
    max_beds: float | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    if not config.RENTCAST_API_KEY:
        raise RentCastError("RENTCAST_API_KEY is not set")

    params: dict[str, Any] = {
        "latitude": latitude,
        "longitude": longitude,
        "radius": radius_miles,
        "status": "Active",
        "limit": limit,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{RENTCAST_BASE_URL}{LISTINGS_PATH}",
                params=params,
                headers={"X-Api-Key": config.RENTCAST_API_KEY, "Accept": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise RentCastError(f"RentCast request failed: {exc}") from exc

    if response.status_code != 200:
        raise RentCastError(
            f"RentCast returned {response.status_code}: {response.text[:300]}"
        )

    try:
        raw_listings = response.json()
    except ValueError as exc:
        raise RentCastError("RentCast returned a non-JSON response") from exc

    if not isinstance(raw_listings, list):
        raise RentCastError(f"Unexpected RentCast response shape: {type(raw_listings)}")

    listings = [_normalize_listing(raw) for raw in raw_listings]

    # RentCast's documented server-side filters for price/bedroom *ranges* aren't
    # confirmed, so we filter on the normalized fields here to guarantee correctness.
    return apply_rent_bed_filters(
        listings, min_rent=min_rent, max_rent=max_rent, min_beds=min_beds, max_beds=max_beds
    )


async def search_all_listings(
    *,
    latitude: float,
    longitude: float,
    radius_miles: float,
    min_rent: float | None = None,
    max_rent: float | None = None,
    min_beds: float | None = None,
    max_beds: float | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Every active listing within `radius_miles`, paginated past RentCast's 500/response
    cap via offset, then normalized and rent/bed filtered. Returns the complete pool so a
    wide-radius criterion never starves the nearby listings a narrow one needs, plus the
    number of RentCast requests made (for quota tracking)."""
    if not config.RENTCAST_API_KEY:
        raise RentCastError("RENTCAST_API_KEY is not set")

    raw_all: list[dict[str, Any]] = []
    total: int | None = None
    offset = 0
    requests_made = 0

    async with httpx.AsyncClient(timeout=20.0) as client:
        for _ in range(MAX_PAGES):
            params: dict[str, Any] = {
                "latitude": latitude,
                "longitude": longitude,
                "radius": radius_miles,
                "status": "Active",
                "limit": PAGE_SIZE,
                "offset": offset,
            }
            if offset == 0:
                params["includeTotalCount"] = "true"

            try:
                response = await client.get(
                    f"{RENTCAST_BASE_URL}{LISTINGS_PATH}",
                    params=params,
                    headers={"X-Api-Key": config.RENTCAST_API_KEY, "Accept": "application/json"},
                )
            except httpx.HTTPError as exc:
                raise RentCastError(f"RentCast request failed: {exc}") from exc

            requests_made += 1
            if response.status_code != 200:
                raise RentCastError(
                    f"RentCast returned {response.status_code}: {response.text[:300]}"
                )

            try:
                batch = response.json()
            except ValueError as exc:
                raise RentCastError("RentCast returned a non-JSON response") from exc
            if not isinstance(batch, list):
                raise RentCastError(f"Unexpected RentCast response shape: {type(batch)}")

            raw_all.extend(batch)
            if offset == 0:
                count_header = response.headers.get("X-Total-Count")
                total = int(count_header) if count_header and count_header.isdigit() else None
            offset += len(batch)

            if len(batch) < PAGE_SIZE:
                break
            if total is not None and offset >= total:
                break

    listings = [_normalize_listing(raw) for raw in raw_all]
    filtered = apply_rent_bed_filters(
        listings, min_rent=min_rent, max_rent=max_rent, min_beds=min_beds, max_beds=max_beds
    )
    return filtered, requests_made
