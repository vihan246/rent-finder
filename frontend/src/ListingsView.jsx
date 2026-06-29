import { useEffect, useState } from 'react'
import { IS_STATIC_MODE, getCachedListings, getStaticListings } from './api'
import ListingCard from './components/ListingCard'
import ListingsMap from './components/ListingsMap'
import RefreshButton from './components/RefreshButton'

const fetchListings = IS_STATIC_MODE ? getStaticListings : getCachedListings

const DEFAULT_FILTERS = { minRent: '', maxRent: '', minBeds: '', maxBeds: '' }

function toNumberOrUndefined(value) {
  if (value === '' || value == null) return undefined
  const n = Number(value)
  return Number.isNaN(n) ? undefined : n
}

function ListingsView() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  // Client-side toggle over the already-fetched listings -- the backend's
  // /listings/cached has no is_new param, so we filter on the `is_new` flag here.
  const [onlyNew, setOnlyNew] = useState(false)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // In static mode this reads the bundled public/listings.json; otherwise it hits
  // the local cache (GET /listings/cached). Neither ever calls RentCast -- safe to
  // run on every mount and every filter change, including StrictMode's double-invoke.
  useEffect(() => {
    const handle = setTimeout(() => {
      setLoading(true)
      fetchListings({
        minRent: toNumberOrUndefined(filters.minRent),
        maxRent: toNumberOrUndefined(filters.maxRent),
        minBeds: toNumberOrUndefined(filters.minBeds),
        maxBeds: toNumberOrUndefined(filters.maxBeds),
      })
        .then((res) => {
          setData(res)
          setError(null)
        })
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false))
    }, 300)
    return () => clearTimeout(handle)
  }, [filters])

  const handleFilterChange = (field) => (e) => {
    setFilters((prev) => ({ ...prev, [field]: e.target.value }))
  }

  const allListings = data?.listings ?? []
  const listings = onlyNew ? allListings.filter((l) => l.is_new) : allListings
  const locations = data?.locations ?? []

  return (
    <div className="listings-view">
      <div className="status-bar">
        <span>
          {data?.last_refreshed_at
            ? `Last refreshed: ${new Date(data.last_refreshed_at).toLocaleString()}`
            : 'Never refreshed yet'}
          {data?.new_count > 0 ? ` · ${data.new_count} new` : ''}
        </span>
        {!IS_STATIC_MODE && (
          <>
            <span>
              {data?.quota_estimate_remaining != null
                ? `~${data.quota_estimate_remaining} RentCast requests remaining`
                : ''}
            </span>
            <RefreshButton
              locationCount={locations.length}
              quotaRemaining={data?.quota_estimate_remaining ?? null}
              onRefreshed={setData}
            />
          </>
        )}
      </div>

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
        <label className="filter-checkbox">
          <input
            type="checkbox"
            checked={onlyNew}
            onChange={(e) => setOnlyNew(e.target.checked)}
          />
          New only
        </label>
      </div>

      {error && <p className="error-text">Error: {error}</p>}
      {loading && <p>Loading…</p>}

      {!loading && !error && (
        <>
          <ListingsMap listings={listings} locations={locations} />
          <div className="listing-cards">
            {listings.length === 0 ? (
              <p>
                {IS_STATIC_MODE
                  ? 'No listings match these filters.'
                  : 'No listings yet. Click "Refresh All" to fetch real results.'}
              </p>
            ) : (
              listings.map((listing) => <ListingCard key={listing.id} listing={listing} />)
            )}
          </div>
        </>
      )}
    </div>
  )
}

export default ListingsView
