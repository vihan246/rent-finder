"""
Export the local listings cache to a static JSON file the frontend can ship as a
public, read-only snapshot (no backend, no API key, no quota exposure).

Run from backend/ with the venv active, then re-run the frontend build/deploy:
    ./venv/bin/python scripts/export_static.py
    cd ../frontend && npm run build   # picks up the new public/listings.json
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


def main() -> None:
    cache = load_listings_cache()

    # Deliberately omit requests_used_total / quota_estimate_remaining -- that's
    # account-level info about your own RentCast usage, not relevant to a viewer.
    snapshot = {
        "last_refreshed_at": cache["last_refreshed_at"],
        "locations": cache["locations"],
        "listings": list(cache["listings"].values()),
    }

    output_path = os.path.abspath(OUTPUT_PATH)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    print(f"Wrote {len(snapshot['listings'])} listings to {output_path}")


if __name__ == "__main__":
    main()
