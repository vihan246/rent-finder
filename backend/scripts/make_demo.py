"""
One-command demo generator (static-demo branch only).

Geocodes a set of addresses, runs a real /search with the owner's keys, freezes the
result into the static snapshot, builds the frontend, and deploys it to Vercel. The
single Vercel URL is overwritten each run (no per-person snapshots).

Run from backend/ with the venv active and RENTCAST_API_KEY + GOOGLE_ROUTES_API_KEY
set in backend/.env:

    ./venv/bin/python scripts/make_demo.py \
        --address "Ferry Building, San Francisco, CA" \
        --address "1 Market St, San Francisco, CA" \
        --mode transit --minutes 15 --transit rail \
        --max-rent 5000 --min-beds 1

    # stop before deploying (just build the snapshot locally):
    ./venv/bin/python scripts/make_demo.py --address "..." --mode walk --minutes 10 --no-deploy
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from services.geocode import GeocodeError, geocode_address  # noqa: E402
from services.search import run_search  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from export_static import export_static  # noqa: E402

FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "frontend")
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate and deploy a rent-finder demo snapshot.")
    p.add_argument("--address", action="append", required=True, help="Tether address (repeatable).")
    p.add_argument("--mode", choices=["walk", "transit", "drive"], required=True)
    p.add_argument("--minutes", type=float, required=True, help="Max commute minutes.")
    p.add_argument(
        "--transit", choices=["rail", "bus"], default="bus",
        help="Transit sub-filter: rail/MUNI-only or include buses (transit mode only).",
    )
    p.add_argument("--min-rent", type=float)
    p.add_argument("--max-rent", type=float)
    p.add_argument("--min-beds", type=float)
    p.add_argument("--max-beds", type=float)
    p.add_argument("--no-build", action="store_true", help="Skip the local npm build.")
    p.add_argument("--no-deploy", action="store_true", help="Skip the Vercel deploy.")
    return p.parse_args()


async def geocode_all(addresses: list[str]) -> list[dict]:
    locations = []
    for i, address in enumerate(addresses):
        try:
            lat, lng = await geocode_address(address)
        except GeocodeError as exc:
            sys.exit(f"FAILED to geocode {address!r}: {exc}")
        locations.append({"id": f"loc_{i + 1}", "label": address, "lat": lat, "lng": lng})
        print(f"Geocoded {address!r} -> ({lat}, {lng})")
        if i < len(addresses) - 1:
            await asyncio.sleep(1.0)  # Nominatim ~1 req/sec usage policy
    return locations


async def main() -> None:
    args = parse_args()
    if not config.RENTCAST_API_KEY or not config.GOOGLE_ROUTES_API_KEY:
        sys.exit("RENTCAST_API_KEY and GOOGLE_ROUTES_API_KEY must be set in backend/.env")

    locations = await geocode_all(args.address)
    commute = {"mode": args.mode, "max_minutes": args.minutes}
    if args.mode == "transit":
        commute["transit_modes"] = args.transit
    filters = {
        "min_rent": args.min_rent,
        "max_rent": args.max_rent,
        "min_beds": args.min_beds,
        "max_beds": args.max_beds,
    }

    print(f"\nSearching ({args.mode}, <= {args.minutes} min)…")
    result = await run_search(locations, commute, filters)
    print(
        f"Found {result['count']} listings "
        f"(RentCast requests: {result['rentcast_requests_used']}, "
        f"routing elements: {result['routing_elements_used']})"
    )

    export_static()

    if not args.no_build:
        print("\nBuilding frontend…")
        subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, check=True)

    if not args.no_deploy:
        print("\nDeploying to Vercel…")
        subprocess.run(["vercel", "--prod", "--yes"], cwd=FRONTEND_DIR, check=True)
        print("\nDeployed. Share the Vercel URL above.")
    else:
        print("\nSkipped deploy. Snapshot is in frontend/public/listings.json.")


if __name__ == "__main__":
    asyncio.run(main())
