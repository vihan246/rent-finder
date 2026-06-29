export const API_BASE_URL = 'http://localhost:8000'

// Static demo build (frontend/.env.production sets VITE_STATIC_MODE=true): no backend,
// no keys, no search -- just the read-only snapshot the owner generated via make_demo.
export const IS_STATIC_MODE = import.meta.env.VITE_STATIC_MODE === 'true'

let staticSnapshotPromise = null

export function getStaticSnapshot() {
  if (!staticSnapshotPromise) {
    staticSnapshotPromise = fetch('/listings.json').then(handleResponse)
  }
  return staticSnapshotPromise
}

async function handleResponse(res) {
  if (!res.ok) {
    let detail
    try {
      const body = await res.json()
      detail = body.detail
    } catch {
      detail = await res.text().catch(() => '')
    }
    throw new Error(detail || `Request failed (${res.status})`)
  }
  return res.json()
}

// Keyless autocomplete (Nominatim, via the backend). Debounce calls from the UI to
// respect Nominatim's ~1 request/second usage policy.
export function geocodeSearch(q) {
  const params = new URLSearchParams({ q })
  return fetch(`${API_BASE_URL}/geocode/search?${params}`).then(handleResponse)
}

// The only call that spends RentCast + Google Routes quota -- invoke it from the
// "Generate listings" button's onClick, never from a useEffect.
export function searchListings(payload) {
  return fetch(`${API_BASE_URL}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).then(handleResponse)
}
