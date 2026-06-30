"""
Export the last search's listings cache to a static JSON file the frontend can ship
as a public, read-only snapshot (no backend, no API key, no quota exposure).

Run from backend/ with the venv active (usually invoked by scripts/make_demo.py):
    ./venv/bin/python scripts/export_static.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.cache import load_listings_cache  # noqa: E402

OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..",
    "frontend",
    "public",
    "listings.json",
)


def export_static() -> str:
    cache = load_listings_cache()

    listings = cache["listings"]
    # run_search stores listings as a dict keyed by id; tolerate a list too.
    listings = list(listings.values()) if isinstance(listings, dict) else listings

    snapshot = {
        "last_refreshed_at": cache.get("last_refreshed_at"),
        "criteria": cache.get("criteria"),
        "locations": cache.get("locations", []),
        "listings": listings,
    }

    output_path = os.path.abspath(OUTPUT_PATH)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    print(f"Wrote {len(snapshot['listings'])} listings to {output_path}")
    return output_path


if __name__ == "__main__":
    export_static()
