import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
RENTCAST_API_KEY = os.getenv("RENTCAST_API_KEY", "")
ORS_API_KEY = os.getenv("ORS_API_KEY", "")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://localhost:5173")

# Self-tracked RentCast free-tier budget for the saved-locations cache (Phase 2).
# Not derived from any RentCast response header -- just a starting point we
# decrement locally every time POST /listings/refresh runs.
STARTING_QUOTA = int(os.getenv("RENTCAST_STARTING_QUOTA", "46"))

GEOCODE_USER_AGENT = os.getenv(
    "GEOCODE_USER_AGENT", "rent-finder-app/1.0 (personal project; one-time geocoding)"
)
