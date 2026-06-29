from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
from services.cache import load_quota, save_quota
from services.geocode import GeocodeError, search_addresses
from services.rentcast import RentCastError
from services.routing import RoutingError
from services.search import run_search

app = FastAPI(title="Rent Finder")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.ALLOWED_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TetherLocation(BaseModel):
    id: Optional[str] = None
    label: Optional[str] = None
    lat: float
    lng: float


class Commute(BaseModel):
    mode: str = Field(pattern="^(walk|transit|drive)$")
    max_minutes: float = Field(gt=0, le=120)
    # "rail" => rail/subway/light-rail only; "bus" (or null) => include buses. Only
    # meaningful when mode == "transit".
    transit_modes: Optional[str] = None


class SearchFilters(BaseModel):
    min_rent: Optional[float] = None
    max_rent: Optional[float] = None
    min_beds: Optional[float] = None
    max_beds: Optional[float] = None


class SearchRequest(BaseModel):
    locations: list[TetherLocation] = Field(min_length=1)
    commute: Commute
    filters: SearchFilters = SearchFilters()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/geocode/search")
async def geocode_search(q: str = Query(..., min_length=1), limit: int = Query(5, ge=1, le=10)):
    try:
        suggestions = await search_addresses(q, limit=limit)
    except GeocodeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"suggestions": suggestions}


def _quota_snapshot(quota: dict[str, int]) -> dict[str, Any]:
    return {
        "rentcast_remaining": config.STARTING_QUOTA - quota["rentcast_used"],
        "routing_remaining": config.ROUTING_STARTING_QUOTA - quota["routing_used"],
    }


@app.post("/search")
async def search(req: SearchRequest):
    """The only path that spends RentCast + Google Routes quota. Triggered exclusively
    by an explicit user action (the frontend's 'Generate listings' button)."""
    if not config.RENTCAST_API_KEY:
        raise HTTPException(status_code=400, detail="RENTCAST_API_KEY is not set")
    if not config.GOOGLE_ROUTES_API_KEY:
        raise HTTPException(status_code=400, detail="GOOGLE_ROUTES_API_KEY is not set")

    quota = load_quota()
    if quota["rentcast_used"] >= config.STARTING_QUOTA:
        raise HTTPException(status_code=429, detail="RentCast quota estimate exhausted")
    if quota["routing_used"] >= config.ROUTING_STARTING_QUOTA:
        raise HTTPException(status_code=429, detail="Routing quota estimate exhausted")

    try:
        result = await run_search(
            [loc.model_dump() for loc in req.locations],
            req.commute.model_dump(),
            req.filters.model_dump(),
        )
    except RentCastError as exc:
        raise HTTPException(status_code=502, detail=f"RentCast error: {exc}") from exc
    except RoutingError as exc:
        raise HTTPException(status_code=502, detail=f"Routing error: {exc}") from exc

    quota["rentcast_used"] += result["rentcast_requests_used"]
    quota["routing_used"] += result["routing_elements_used"]
    save_quota(quota)

    return {**result, **_quota_snapshot(quota)}
