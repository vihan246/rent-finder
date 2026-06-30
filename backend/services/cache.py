from __future__ import annotations

import json
import os
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LISTINGS_CACHE_PATH = os.path.join(DATA_DIR, "listings_cache.json")
QUOTA_PATH = os.path.join(DATA_DIR, "quota.json")


def load_quota() -> dict[str, int]:
    """Cumulative, self-tracked usage counters that persist across /search calls."""
    if not os.path.exists(QUOTA_PATH):
        return {"rentcast_used": 0, "routing_used": 0}
    with open(QUOTA_PATH, "r") as f:
        data = json.load(f)
    return {
        "rentcast_used": int(data.get("rentcast_used", 0)),
        "routing_used": int(data.get("routing_used", 0)),
    }


def save_quota(quota: dict[str, int]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_path = f"{QUOTA_PATH}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(quota, f, indent=2)
    os.replace(tmp_path, QUOTA_PATH)


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
    commute_minutes: float,
    mode: str,
) -> None:
    """ANY-match merge: a listing reachable from several tether locations (or the same
    location via several commute modes) is stored once, accumulating one near_locations
    tag per (location, mode) it qualifies under, keeping the smallest minutes seen."""
    listing_id = listing["id"]
    tag = {
        "id": location_id,
        "label": location_label,
        "commute_minutes": commute_minutes,
        "mode": mode,
    }
    # commute_minutes is per-origin-location, so it lives in near_locations, not as a
    # single top-level field on a listing that can be near several locations.
    listing_fields = {k: v for k, v in listing.items() if k != "commute_minutes"}

    existing = cache_listings.get(listing_id)
    if existing is None:
        cache_listings[listing_id] = {**listing_fields, "near_locations": [tag]}
        return

    for loc in existing["near_locations"]:
        if loc["id"] == location_id and loc["mode"] == mode:
            if commute_minutes < loc["commute_minutes"]:
                loc["commute_minutes"] = commute_minutes
            return
    existing["near_locations"].append(tag)
