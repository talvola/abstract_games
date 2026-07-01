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

// Relevance of a game to a search query. Higher = better; 0 = no match.
// Ranks name matches (exact > prefix > word-prefix > substring) above tag,
// category, and description matches, so typing an exact game name ("Tak")
// surfaces that game at the very top instead of burying it among games that
// merely contain the letters (e.g. "s-tak-ing", "at-tak") in a description.
export function relevance(g, query) {
  if (!query) return 1
  const name = (g.name || '').toLowerCase()
  const tags = (g.tags || []).map((t) => t.toLowerCase())
  const category = (g.category || '').toLowerCase()
  const desc = (g.description || '').toLowerCase()
  if (name === query) return 1000
  if (name.startsWith(query)) return 900
  if (name.split(/\s+/).some((w) => w.startsWith(query))) return 800
  if (name.includes(query)) return 700
  if (tags.some((t) => t === query)) return 600
  if (tags.some((t) => t.startsWith(query))) return 500
  if (tags.some((t) => t.includes(query))) return 400
  if (category.includes(query)) return 250
  if (desc.includes(query)) return 100
  return 0
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
  const inCat = (g) => !cat || (g.category || 'Other') === cat
  const matches = games.filter((g) => inCat(g) && relevance(g, query) > 0)
  // When searching, show one flat list ranked by relevance (best match first),
  // so an exact-name hit is at the top. When browsing, keep category grouping.
  const ranked = query
    ? [...matches].sort((a, b) => relevance(b, query) - relevance(a, query) || a.name.localeCompare(b.name))
    : null
  const groups = query ? [['', ranked]] : groupByCategory(matches)

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
        {matches.length === 0 && <div className="muted small">No games match “{q}”.</div>}
        {groups.map(([cat, list]) => (
          <div key={cat || '_results'} className="cat-group">
            {cat && <div className="cat-label">{cat}</div>}
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
