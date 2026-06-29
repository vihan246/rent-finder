# Rent Finder

Find rental listings near the places **you** care about. Add one or more tether
locations (your office, a partner's office, the gym, family), choose a commute mode
— **walk**, **transit** (rail/MUNI-only or include buses), or **drive** — and a time
budget, then generate listings that fall within that commute of any of your locations.

- **Listings:** [RentCast](https://rentcast.io)
- **Travel times:** [Google Routes API](https://developers.google.com/maps/documentation/routes)
  (real walk/drive/transit times; transit can be restricted to rail vs. include buses)
- **Address autocomplete:** Nominatim / OpenStreetMap (keyless)
- **Frontend:** React + Vite + Leaflet · **Backend:** FastAPI

## How it works

```
search an address (autocomplete) → add tether locations → pick commute mode + minutes
  → "Generate listings" → POST /search
      for each location: RentCast nearby rentals → straight-line pre-filter
        → Google Routes travel time in your mode → keep those within the time budget
      → listings shown if reachable from ANY location, tagged "N min <mode> from <label>"
```

`/search` is the only call that spends RentCast / Google Routes quota, and it only
fires from the "Generate listings" button. Both budgets are self-tracked locally
(`RENTCAST_STARTING_QUOTA`, `ROUTING_STARTING_QUOTA`) so a fork can't silently burn
through a free tier.

## Getting API keys

1. **RentCast** — sign up at https://rentcast.io, create an API key, and check the
   free-tier request cap and rental coverage for your area.
2. **Google Routes** — in [Google Cloud](https://console.cloud.google.com/), create a
   project, **enable the "Routes API"**, and create an API key. (Routes billing is
   per-element; the app pre-filters candidates by straight-line distance to keep
   per-search calls modest.)

## Setup

### Backend

```
cd backend
python3.11 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in RENTCAST_API_KEY and GOOGLE_ROUTES_API_KEY
./venv/bin/uvicorn main:app --reload --port 8000
```

### Frontend

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — you should see a green dot once the backend is running,
then add locations, pick a commute, and generate listings.

## Endpoints

- `GET /health` — liveness check.
- `GET /geocode/search?q=` — keyless address autocomplete (Nominatim).
- `POST /search` — body `{ locations: [{label,lat,lng}], commute: {mode, max_minutes,
  transit_modes}, filters: {min_rent,max_rent,min_beds,max_beds} }`. Returns matching
  listings plus remaining quota estimates. `mode` ∈ `walk|transit|drive`;
  `transit_modes` is `"rail"` (rail/subway/light-rail only) or `"bus"` (include buses).

## Hard rules

- All secrets live in `.env` (gitignored), loaded server-side only.
- The backend is the only thing that calls RentCast or Google Routes — the frontend
  only talks to this backend.
- No scraping of Zillow/Redfin/Apartments.com/Craigslist — licensed APIs only.
