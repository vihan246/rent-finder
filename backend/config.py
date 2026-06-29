import os

from dotenv import load_dotenv

load_dotenv()

RENTCAST_API_KEY = os.getenv("RENTCAST_API_KEY", "")
# Google Routes API key (enable the "Routes API" in Google Cloud). Used for real
# walk/drive/transit travel times in services/routing.py.
GOOGLE_ROUTES_API_KEY = os.getenv("GOOGLE_ROUTES_API_KEY", "")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://localhost:5173")

# Self-tracked free-tier budgets. Neither is derived from a provider response
# header -- they're starting points decremented locally on each POST /search so a
# fork can't silently burn through its free tier.
STARTING_QUOTA = int(os.getenv("RENTCAST_STARTING_QUOTA", "46"))
ROUTING_STARTING_QUOTA = int(os.getenv("ROUTING_STARTING_QUOTA", "1000"))

GEOCODE_USER_AGENT = os.getenv(
    "GEOCODE_USER_AGENT", "rent-finder-app/1.0 (personal project; one-time geocoding)"
)
