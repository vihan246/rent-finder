import { useEffect, useRef, useState } from 'react'
import { geocodeSearch } from '../api'

// Debounced address autocomplete. Selecting a suggestion calls onAdd; chosen
// locations render as removable chips driven by the parent's `locations` array.
function LocationSearch({ locations, onAdd, onRemove }) {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState(null)
  const seq = useRef(0)

  useEffect(() => {
    const q = query.trim()
    const id = ++seq.current
    const handle = setTimeout(() => {
      if (id !== seq.current) return
      if (q.length < 3) {
        setSuggestions([])
        setSearching(false)
        return
      }
      setSearching(true)
      geocodeSearch(q)
        .then((res) => {
          if (id !== seq.current) return // a newer query superseded this one
          setSuggestions(res.suggestions ?? [])
          setError(null)
        })
        .catch((err) => {
          if (id === seq.current) setError(err.message)
        })
        .finally(() => {
          if (id === seq.current) setSearching(false)
        })
    }, 400)
    return () => clearTimeout(handle)
  }, [query])

  const handlePick = (suggestion) => {
    onAdd(suggestion)
    setQuery('')
    setSuggestions([])
  }

  return (
    <div className="location-search">
      <label className="location-search-label">
        Add a place you want to live near
        <input
          type="text"
          value={query}
          placeholder="Search an address, station, or landmark…"
          onChange={(e) => setQuery(e.target.value)}
        />
      </label>

      {searching && <p className="location-search-hint">Searching…</p>}
      {error && <p className="error-text">{error}</p>}

      {suggestions.length > 0 && (
        <ul className="location-suggestions">
          {suggestions.map((s) => (
            <li key={`${s.lat},${s.lng}`}>
              <button type="button" onClick={() => handlePick(s)}>
                {s.label}
              </button>
            </li>
          ))}
        </ul>
      )}

      {locations.length > 0 && (
        <ul className="location-chips">
          {locations.map((loc) => (
            <li key={loc.id} className="location-chip">
              <span>📍 {loc.label}</span>
              <button
                type="button"
                aria-label={`Remove ${loc.label}`}
                onClick={() => onRemove(loc.id)}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default LocationSearch
