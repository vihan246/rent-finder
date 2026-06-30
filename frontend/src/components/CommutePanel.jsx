// A list of OR'd commute criteria. Each row is a mode + max-minutes budget (plus a
// rail-vs-bus sub-toggle for transit); a listing qualifies if it satisfies any row.
const MODES = [
  { value: 'walk', label: 'Walk' },
  { value: 'transit', label: 'Transit' },
  { value: 'drive', label: 'Drive' },
]

const NEW_CRITERION = { mode: 'walk', maxMinutes: 15, transitModes: 'rail' }

function CommutePanel({ criteria, onChange }) {
  const update = (index, patch) =>
    onChange(criteria.map((c, i) => (i === index ? { ...c, ...patch } : c)))
  const remove = (index) => onChange(criteria.filter((_, i) => i !== index))
  const add = () => onChange([...criteria, { ...NEW_CRITERION }])

  return (
    <div className="commute-panel">
      {criteria.map((c, i) => (
        <div key={i} className="commute-row">
          <div className="commute-modes">
            {MODES.map((m) => (
              <label key={m.value} className={c.mode === m.value ? 'active' : ''}>
                <input
                  type="radio"
                  name={`commute-mode-${i}`}
                  value={m.value}
                  checked={c.mode === m.value}
                  onChange={() => update(i, { mode: m.value })}
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
              value={c.maxMinutes}
              onChange={(e) => update(i, { maxMinutes: e.target.value })}
            />
            min
          </label>

          {c.mode === 'transit' && (
            <div className="commute-transit-modes">
              <label className={c.transitModes === 'rail' ? 'active' : ''}>
                <input
                  type="radio"
                  name={`transit-modes-${i}`}
                  value="rail"
                  checked={c.transitModes === 'rail'}
                  onChange={() => update(i, { transitModes: 'rail' })}
                />
                Rail / MUNI only
              </label>
              <label className={c.transitModes !== 'rail' ? 'active' : ''}>
                <input
                  type="radio"
                  name={`transit-modes-${i}`}
                  value="bus"
                  checked={c.transitModes !== 'rail'}
                  onChange={() => update(i, { transitModes: 'bus' })}
                />
                Include buses
              </label>
            </div>
          )}

          {criteria.length > 1 && (
            <button
              type="button"
              className="commute-remove"
              aria-label="Remove this commute option"
              onClick={() => remove(i)}
            >
              ✕
            </button>
          )}

          {i < criteria.length - 1 && <span className="commute-or">OR</span>}
        </div>
      ))}

      <button type="button" className="commute-add" onClick={add}>
        + Add commute option
      </button>
    </div>
  )
}

export default CommutePanel
