import { useMemo, useState } from 'react'
import { searchListings } from './api'
import { applyRentBedFilters } from './filters'
import { buildAnchorLetters } from './anchors'
import CommutePanel from './components/CommutePanel'
import ListingCard from './components/ListingCard'
import ListingsMap from './components/ListingsMap'
import LocationSearch from './components/LocationSearch'

const DEFAULT_COMMUTE = { mode: 'walk', maxMinutes: 10, transitModes: 'rail' }
const DEFAULT_FILTERS = { minRent: '', maxRent: '', minBeds: '', maxBeds: '' }

function toNumberOrUndefined(value) {
  if (value === '' || value == null) return undefined
  const n = Number(value)
  return Number.isNaN(n) ? undefined : n
}

function ListingsView() {
  const [locations, setLocations] = useState([])
  const [commute, setCommute] = useState(DEFAULT_COMMUTE)
  const [filters, setFilters] = useState(DEFAULT_FILTERS)

  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const addLocation = (suggestion) => {
    const id = `${suggestion.lat},${suggestion.lng}`
    setLocations((prev) =>
      prev.some((l) => l.id === id) ? prev : [...prev, { ...suggestion, id }]
    )
  }
  const removeLocation = (id) =>
    setLocations((prev) => prev.filter((l) => l.id !== id))

  const handleFilterChange = (field) => (e) =>
    setFilters((prev) => ({ ...prev, [field]: e.target.value }))

  const handleSubmit = () => {
    if (locations.length === 0 || loading) return
    setLoading(true)
    const payload = {
      locations: locations.map(({ id, label, lat, lng }) => ({ id, label, lat, lng })),
      commute: {
        mode: commute.mode,
        max_minutes: Number(commute.maxMinutes) || 10,
        ...(commute.mode === 'transit' ? { transit_modes: commute.transitModes } : {}),
      },
      filters: {
        min_rent: toNumberOrUndefined(filters.minRent) ?? null,
        max_rent: toNumberOrUndefined(filters.maxRent) ?? null,
        min_beds: toNumberOrUndefined(filters.minBeds) ?? null,
        max_beds: toNumberOrUndefined(filters.maxBeds) ?? null,
      },
    }
    searchListings(payload)
      .then((res) => {
        setResult(res)
        setError(null)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  // Rent/bed inputs narrow the already-fetched results client-side, so tweaking them
  // doesn't re-spend quota -- only "Generate listings" hits the backend.
  const visibleListings = useMemo(() => {
    if (!result) return []
    return applyRentBedFilters(result.listings ?? [], {
      minRent: toNumberOrUndefined(filters.minRent),
      maxRent: toNumberOrUndefined(filters.maxRent),
      minBeds: toNumberOrUndefined(filters.minBeds),
      maxBeds: toNumberOrUndefined(filters.maxBeds),
    })
  }, [result, filters])

  const resultLocations = result?.locations ?? locations
  const anchorLetters = useMemo(() => buildAnchorLetters(resultLocations), [resultLocations])

  return (
    <div className="listings-view">
      <LocationSearch
        locations={locations}
        onAdd={addLocation}
        onRemove={removeLocation}
      />

      <CommutePanel commute={commute} onChange={setCommute} />

      <div className="filters">
        <label>
          Min rent
          <input type="number" value={filters.minRent} onChange={handleFilterChange('minRent')} />
        </label>
        <label>
          Max rent
          <input type="number" value={filters.maxRent} onChange={handleFilterChange('maxRent')} />
        </label>
        <label>
          Min beds
          <input type="number" value={filters.minBeds} onChange={handleFilterChange('minBeds')} />
        </label>
        <label>
          Max beds
          <input type="number" value={filters.maxBeds} onChange={handleFilterChange('maxBeds')} />
        </label>
      </div>

      <div className="search-bar">
        <button
          type="button"
          className="generate-button"
          onClick={handleSubmit}
          disabled={locations.length === 0 || loading}
        >
          {loading ? 'Generating…' : 'Generate listings'}
        </button>
        {result && (
          <span className="search-meta">
            {visibleListings.length} listing{visibleListings.length === 1 ? '' : 's'}
            {result.routing_remaining != null
              ? ` · ~${result.routing_remaining} routing / ${result.rentcast_remaining} RentCast left`
              : ''}
          </span>
        )}
      </div>

      {error && <p className="error-text">Error: {error}</p>}

      {!result && !loading && !error && (
        <p className="empty-state">
          Add one or more places above, pick a commute mode and time, then
          “Generate listings”.
        </p>
      )}

      {result && (
        <>
          {resultLocations.length > 0 && (
            <ol className="anchor-legend">
              {resultLocations.map((loc) => (
                <li key={loc.id}>
                  <span className="anchor-letter">{anchorLetters[loc.id]}</span>
                  <span className="anchor-label" title={loc.label}>
                    {loc.label}
                  </span>
                </li>
              ))}
            </ol>
          )}
          <ListingsMap
            listings={visibleListings}
            locations={resultLocations}
            anchorLetters={anchorLetters}
          />
          <div className="listing-cards">
            {visibleListings.length === 0 ? (
              <p>No listings match within this commute and these filters.</p>
            ) : (
              visibleListings.map((listing) => (
                <ListingCard key={listing.id} listing={listing} anchorLetters={anchorLetters} />
              ))
            )}
          </div>
        </>
      )}
    </div>
  )
}

export default ListingsView
