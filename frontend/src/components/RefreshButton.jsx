import { useState } from 'react'
import { refreshAll } from '../api'

function RefreshButton({ locationCount, quotaRemaining, onRefreshed }) {
  const [confirming, setConfirming] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)

  const after = quotaRemaining != null ? quotaRemaining - locationCount : null

  const handleConfirm = () => {
    setRefreshing(true)
    setError(null)
    // The only call site for refreshAll() in the whole app -- triggered solely by
    // this explicit click, never by an effect or on mount.
    refreshAll()
      .then((result) => {
        onRefreshed(result)
        setConfirming(false)
      })
      .catch((err) => setError(err.message))
      .finally(() => setRefreshing(false))
  }

  if (!confirming) {
    return (
      <button className="refresh-button" onClick={() => setConfirming(true)}>
        Refresh All
      </button>
    )
  }

  return (
    <div className="refresh-confirm">
      <span>
        Use ~{locationCount} RentCast request{locationCount === 1 ? '' : 's'}
        {quotaRemaining != null ? ` (${quotaRemaining} → ${after} remaining)` : ''}?
      </span>
      <button onClick={handleConfirm} disabled={refreshing}>
        {refreshing ? 'Refreshing…' : 'Confirm'}
      </button>
      <button onClick={() => setConfirming(false)} disabled={refreshing}>
        Cancel
      </button>
      {error && <span className="error-text">{error}</span>}
    </div>
  )
}

export default RefreshButton
