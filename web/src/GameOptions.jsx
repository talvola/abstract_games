import { Fragment } from 'react'

// Renders a labelled <select> for each option a game's manifest declares, e.g.
//   "size": { "choices": [7,9,11], "default": 11 }
//   "sim_connection": { "choices": ["draw","win"], "default": "draw",
//                       "label": "Simultaneous connection",
//                       "labels": { "draw": "Draw", "win": "Win for mover" } }
// Emits <label>+<select> pairs (no wrapper) so it slots into a .form-grid.

export function defaultOptions(options) {
  const v = {}
  for (const [k, opt] of Object.entries(options || {})) v[k] = opt.default
  return v
}

export default function GameOptions({ options, values, onChange }) {
  return Object.entries(options || {}).map(([key, opt]) => (
    <Fragment key={key}>
      <label>{opt.label || key}</label>
      <select
        value={String(values[key] ?? opt.default)}
        onChange={(e) => onChange(key, opt.choices.find((c) => String(c) === e.target.value))}
      >
        {opt.choices.map((c) => (
          <option key={String(c)} value={String(c)}>{opt.labels?.[c] ?? c}</option>
        ))}
      </select>
    </Fragment>
  ))
}
