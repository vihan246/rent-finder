import { applyRentBedFilters } from './filters'

export const API_BASE_URL = 'http://localhost:8000'

// Set at build time (frontend/.env.production) for the deployed read-only snapshot:
// no backend, no API key, no Refresh button -- just the static export shipped in
// public/listings.json, filtered in the browser.
export const IS_STATIC_MODE = import.meta.env.VITE_STATIC_MODE === 'true'

async function handleResponse(res) {
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Request failed (${res.status}): ${text}`)
  }
  return res.json()
}

let staticSnapshotPromise = null

function loadStaticSnapshot() {
  if (!staticSnapshotPromise) {
    staticSnapshotPromise = fetch('/listings.json').then(handleResponse)
  }
  return staticSnapshotPromise
}

export async function getStaticListings(filters = {}) {
  const snapshot = await loadStaticSnapshot()
  return {
    last_refreshed_at: snapshot.last_refreshed_at,
    locations: snapshot.locations,
    listings: applyRentBedFilters(snapshot.listings, filters),
  }
}

export function getLocations() {
  return fetch(`${API_BASE_URL}/locations`).then(handleResponse)
}

export function getCachedListings(filters = {}) {
  const params = new URLSearchParams()
  if (filters.minRent != null) params.set('min_rent', filters.minRent)
  if (filters.maxRent != null) params.set('max_rent', filters.maxRent)
  if (filters.minBeds != null) params.set('min_beds', filters.minBeds)
  if (filters.maxBeds != null) params.set('max_beds', filters.maxBeds)
  return fetch(`${API_BASE_URL}/listings/cached?${params}`).then(handleResponse)
}

// Only ever call this from a button's onClick, never from a useEffect -- it spends
// real RentCast quota.
export function refreshAll() {
  return fetch(`${API_BASE_URL}/listings/refresh`, { method: 'POST' }).then(handleResponse)
}
