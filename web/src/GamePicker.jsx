import { useState } from 'react'
import RulesModal from './RulesModal'

// Group games by category, stable order, "Other" last.
export function groupByCategory(games) {
  const map = new Map()
  for (const g of games) {
    const c = g.category || 'Other'
    if (!map.has(c)) map.set(c, [])
    map.get(c).push(g)
  }
  return [...map.entries()].sort((a, b) =>
    a[0] === 'Other' ? 1 : b[0] === 'Other' ? -1 : a[0].localeCompare(b[0]),
  )
}

// Scalable game selector: a search box + category-grouped cards (replaces the
// dropdown, which doesn't scale to hundreds of games). Each card has a "Rules"
// button that opens the game's local rules. Self-contained — parents only pass
// the current selection and an onChange.
export default function GamePicker({ games, value, onChange }) {
  const [q, setQ] = useState('')
  const [cat, setCat] = useState(null)
  const [rules, setRules] = useState(null)

  const cats = groupByCategory(games).map(([c]) => c)
  const query = q.trim().toLowerCase()
  const hay = (g) => [g.name, g.category, g.description, (g.tags || []).join(' ')].join(' ').toLowerCase()
  const filtered = games.filter(
    (g) => (!query || hay(g).includes(query)) && (!cat || (g.category || 'Other') === cat),
  )

  return (
    <div className="game-picker">
      <input
        className="game-search"
        type="search"
        placeholder={`Search ${games.length} games…`}
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {cats.length > 1 && (
        <div className="cat-chips">
          <button type="button" className={`cat-chip ${!cat ? 'on' : ''}`} onClick={() => setCat(null)}>All</button>
          {cats.map((c) => (
            <button type="button" key={c} className={`cat-chip ${cat === c ? 'on' : ''}`}
              onClick={() => setCat(cat === c ? null : c)}>{c}</button>
          ))}
        </div>
      )}
      <div className="game-list">
        {filtered.length === 0 && <div className="muted small">No games match “{q}”.</div>}
        {groupByCategory(filtered).map(([cat, list]) => (
          <div key={cat} className="cat-group">
            <div className="cat-label">{cat}</div>
            {list.map((g) => (
              <div key={g.uid} className={`game-card ${g.uid === value ? 'active' : ''}`}>
                <button className="game-card-main" onClick={() => onChange(g.uid)}>
                  <div className="game-name">
                    {g.name}{g.source === 'uploaded' ? ` · by ${g.uploader || 'community'}` : ''}
                  </div>
                  <div className="game-desc">{g.description}</div>
                  {g.tags?.length > 0 && <div className="game-tags">{g.tags.join(' · ')}</div>}
                </button>
                {g.has_rules && (
                  <button className="game-rules-btn" title="How to play" onClick={() => setRules(g)}>Rules</button>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>
      {rules && <RulesModal uid={rules.uid} name={rules.name} onClose={() => setRules(null)} />}
    </div>
  )
}
