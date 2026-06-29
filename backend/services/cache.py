from __future__ import annotations

import json
import os
from typing import Any

import config

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LOCATIONS_PATH = os.path.join(DATA_DIR, "locations.json")
LISTINGS_CACHE_PATH = os.path.join(DATA_DIR, "listings_cache.json")


def load_locations() -> list[dict[str, Any]]:
    if not os.path.exists(LOCATIONS_PATH):
        raise FileNotFoundError(
            f"{LOCATIONS_PATH} does not exist yet -- run scripts/seed_locations.py first"
        )
    with open(LOCATIONS_PATH, "r") as f:
        return json.load(f)["locations"]


def load_listings_cache() -> dict[str, Any]:
    if not os.path.exists(LISTINGS_CACHE_PATH):
        try:
            locations = load_locations()
        except FileNotFoundError:
            locations = []
        return {
            "last_refreshed_at": None,
            "requests_used_total": 0,
            "quota_estimate_remaining": config.STARTING_QUOTA,
            "locations": locations,
            "listings": {},
        }
    with open(LISTINGS_CACHE_PATH, "r") as f:
        return json.load(f)


def save_listings_cache(cache: dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_path = f"{LISTINGS_CACHE_PATH}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(cache, f, indent=2)
    os.replace(tmp_path, LISTINGS_CACHE_PATH)


def merge_listing(
    cache_listings: dict[str, Any],
    listing: dict[str, Any],
    location_id: str,
    location_label: str,
    walk_minutes: float,
) -> None:
    listing_id = listing["id"]
    tag = {"id": location_id, "label": location_label, "walk_minutes": walk_minutes}
    # walk_minutes is meaningful per-origin-location, so it lives in near_locations,
    # not as a single top-level field on a listing that can be near several locations.
    listing_fields = {k: v for k, v in listing.items() if k != "walk_minutes"}

    existing = cache_listings.get(listing_id)
    if existing is None:
        cache_listings[listing_id] = {**listing_fields, "near_locations": [tag]}
        return

    if not any(loc["id"] == location_id for loc in existing["near_locations"]):
        existing["near_locations"].append(tag)
