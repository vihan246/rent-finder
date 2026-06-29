# Rent Finder

A webapp where a user describes what they want in natural language, Claude
decides which tools to call, and the backend executes the real API calls
(RentCast for listings). See `RentalFinder_ClaudeCode_PLAN.md` for the full
build plan.

Status: Phase 0 (scaffold) and Phase 1 (RentCast data layer) are done.
Phase 2 (Claude tool-use loop) is next.

## Setup

### Backend

```
cd backend
python3.11 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env   # then fill in RENTCAST_API_KEY (and ANTHROPIC_API_KEY for Phase 2)
./venv/bin/uvicorn main:app --reload --port 8000
```

### Frontend

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — you should see a green dot once the backend is running.

## Getting a RentCast key

1. Sign up at https://rentcast.io.
2. Dashboard → API key.
3. Check the free-tier request cap and current rental-listings coverage for
   the area you care about — that's the Phase 1 checkpoint in the plan.
4. Put the key in `backend/.env` as `RENTCAST_API_KEY=...`.

## Testing the data layer (Phase 1)

With the backend running and `RENTCAST_API_KEY` set in `backend/.env`:

```
curl "http://localhost:8000/debug/listings?lat=37.7765&lng=-122.3946&max_rent=3200&min_beds=0&max_beds=1&max_walk_minutes=10"
```

This should return normalized listings near 4th & King Caltrain, filtered to
a 10-minute straight-line walk. Without a key set, the endpoint returns a
502 with a clear "RENTCAST_API_KEY is not set" message instead of crashing.

Note: the exact RentCast query-parameter and response-field names in
`backend/services/rentcast.py` were written from documented API knowledge,
not a live fetch of their current docs (no web access was available while
building this). The normalizer is defensive about missing/renamed fields, and
price/bedroom-range filtering happens client-side after the API call rather
than relying on unconfirmed server-side filters — but it's worth diffing
against https://developers.rentcast.io once you have a real key and see a
live response, especially if `/debug/listings` comes back with unexpectedly
empty `rent`/`beds`/`address` fields.

## Hard rules

- All secrets live in `.env` (gitignored), loaded server-side only.
- The backend is the only thing that calls Anthropic or RentCast — the
  frontend only talks to this backend.
- No scraping of Zillow/Redfin/Apartments.com/Craigslist — licensed APIs only.
