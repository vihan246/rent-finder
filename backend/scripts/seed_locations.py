"""
One-time script: geocode the saved address list into backend/data/locations.json.

Run from backend/ with the venv active:
    ./venv/bin/python scripts/seed_locations.py

Costs zero RentCast quota (Nominatim only, free and keyless). Safe to re-run if you
change an address -- it re-geocodes everything and overwrites locations.json.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.geocode import GeocodeError, geocode_address  # noqa: E402

# Fill in your real ~10 addresses here. "max_walk_minutes" defaults to 10 for all;
# override per-location if one should use a different radius.
ADDRESSES = [
    {"id": "loc_1", "label": "Example Location", "address": "1600 Amphitheatre Parkway, Mountain View, CA"},
]

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LOCATIONS_PATH = os.path.join(DATA_DIR, "locations.json")

DEFAULT_MAX_WALK_MINUTES = 10


async def main() -> None:
    locations = []
    for entry in ADDRESSES:
        try:
            lat, lng = await geocode_address(entry["address"])
        except GeocodeError as exc:
            print(f"FAILED to geocode {entry['label']!r} ({entry['address']!r}): {exc}")
            continue

        locations.append(
            {
                "id": entry["id"],
                "label": entry["label"],
                "address": entry["address"],
                "lat": lat,
                "lng": lng,
                "max_walk_minutes": entry.get("max_walk_minutes", DEFAULT_MAX_WALK_MINUTES),
                "geocoded_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        print(f"Geocoded {entry['label']!r} -> ({lat}, {lng})")
        await asyncio.sleep(1.0)  # respect Nominatim's ~1 request/second usage policy

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LOCATIONS_PATH, "w") as f:
        json.dump({"locations": locations}, f, indent=2)

    print(f"\nWrote {len(locations)} locations to {LOCATIONS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
