// One commute setting applied to the whole search: a mode, a max-minutes budget,
// and -- for transit only -- whether to allow buses or restrict to rail/MUNI.
const MODES = [
  { value: 'walk', label: 'Walk' },
  { value: 'transit', label: 'Transit' },
  { value: 'drive', label: 'Drive' },
]

function CommutePanel({ commute, onChange }) {
  const set = (patch) => onChange({ ...commute, ...patch })

  return (
    <div className="commute-panel">
      <div className="commute-modes">
        {MODES.map((m) => (
          <label key={m.value} className={commute.mode === m.value ? 'active' : ''}>
            <input
              type="radio"
              name="commute-mode"
              value={m.value}
              checked={commute.mode === m.value}
              onChange={() => set({ mode: m.value })}
            />
            {m.label}
          </label>
        ))}
      </div>

      <label className="commute-minutes">
        Within
        <input
          type="number"
          min="1"
          max="120"
          value={commute.maxMinutes}
          onChange={(e) => set({ maxMinutes: e.target.value })}
        />
        min
      </label>

      {commute.mode === 'transit' && (
        <div className="commute-transit-modes">
          <label className={commute.transitModes === 'rail' ? 'active' : ''}>
            <input
              type="radio"
              name="transit-modes"
              value="rail"
              checked={commute.transitModes === 'rail'}
              onChange={() => set({ transitModes: 'rail' })}
            />
            Rail / MUNI only
          </label>
          <label className={commute.transitModes !== 'rail' ? 'active' : ''}>
            <input
              type="radio"
              name="transit-modes"
              value="bus"
              checked={commute.transitModes !== 'rail'}
              onChange={() => set({ transitModes: 'bus' })}
            />
            Include buses
          </label>
        </div>
      )}
    </div>
  )
}

export default CommutePanel
