from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import config
from services.cache import load_listings_cache, load_locations, merge_listing, save_listings_cache
from services.filters import apply_rent_bed_filters
from services.geo import filter_within_walk
from services.rentcast import RentCastError, search_listings

app = FastAPI(title="Rent Finder")

# A 10-minute walk at ~3mph is ~0.5mi; query RentCast with a bit of margin around
# each saved location, then trim to the real walk-time cutoff with filter_within_walk.
REFRESH_RADIUS_MILES = 1.0

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.ALLOWED_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug/listings")
async def debug_listings(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_miles: float = Query(5.0),
    max_walk_minutes: Optional[float] = Query(None),
    min_rent: Optional[float] = Query(None),
    max_rent: Optional[float] = Query(None),
    min_beds: Optional[float] = Query(None),
    max_beds: Optional[float] = Query(None),
    limit: int = Query(50),
):
    try:
        listings = await search_listings(
            latitude=lat,
            longitude=lng,
            radius_miles=radius_miles,
            min_rent=min_rent,
            max_rent=max_rent,
            min_beds=min_beds,
            max_beds=max_beds,
            limit=limit,
        )
    except RentCastError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if max_walk_minutes is not None:
        listings = filter_within_walk(listings, (lat, lng), max_walk_minutes)

    return {"count": len(listings), "listings": listings}


@app.get("/locations")
async def get_locations():
    try:
        locations = load_locations()
    except FileNotFoundError:
        return {"locations": []}
    return {"locations": locations}


@app.get("/listings/cached")
async def get_cached_listings(
    min_rent: Optional[float] = Query(None),
    max_rent: Optional[float] = Query(None),
    min_beds: Optional[float] = Query(None),
    max_beds: Optional[float] = Query(None),
):
    """Reads the on-disk cache only. Never calls RentCast -- safe to call on every
    page load and every filter change."""
    cache = load_listings_cache()
    all_listings = list(cache["listings"].values())
    filtered = apply_rent_bed_filters(
        all_listings, min_rent=min_rent, max_rent=max_rent, min_beds=min_beds, max_beds=max_beds
    )
    return {
        "last_refreshed_at": cache["last_refreshed_at"],
        "quota_estimate_remaining": cache["quota_estimate_remaining"],
        "locations": cache["locations"],
        "count": len(filtered),
        "listings": filtered,
    }


@app.post("/listings/refresh")
async def refresh_listings():
    """The only code path that calls RentCast for the saved locations. Triggered
    exclusively by an explicit user action (the frontend's Refresh button), never
    automatically."""
    try:
        locations = load_locations()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    new_listings: dict = {}
    location_summaries = []
    errors = []

    for loc in locations:
        try:
            raw = await search_listings(
                latitude=loc["lat"],
                longitude=loc["lng"],
                radius_miles=REFRESH_RADIUS_MILES,
                limit=100,
            )
        except RentCastError as exc:
            errors.append({"location_id": loc["id"], "error": str(exc)})
            location_summaries.append({**loc, "raw_listing_ids": []})
            continue

        walked = filter_within_walk(
            raw, (loc["lat"], loc["lng"]), loc.get("max_walk_minutes", 10)
        )
        for listing in walked:
            merge_listing(new_listings, listing, loc["id"], loc["label"], listing["walk_minutes"])
        location_summaries.append({**loc, "raw_listing_ids": [l["id"] for l in walked]})

    prior = load_listings_cache()
    prior_ids = set(prior.get("listings", {}).keys())
    new_ids = set(new_listings.keys()) - prior_ids
    for listing_id in new_ids:
        new_listings[listing_id]["is_new"] = True

    requests_used_total = prior.get("requests_used_total", 0) + len(locations)

    cache = {
        "last_refreshed_at": datetime.now(timezone.utc).isoformat(),
        "requests_used_total": requests_used_total,
        "quota_estimate_remaining": config.STARTING_QUOTA - requests_used_total,
        "locations": location_summaries,
        "listings": new_listings,
    }
    save_listings_cache(cache)

    return {
        **cache,
        "errors": errors,
        "count": len(new_listings),
        "new_count": len(new_ids),
        "listings": list(new_listings.values()),
    }
