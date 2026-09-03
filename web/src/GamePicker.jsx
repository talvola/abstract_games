import { useMemo, useState } from 'react'
import RulesModal from './RulesModal'
import { FEATURED } from './featured'

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

// One-line teaser: the first sentence of the description, clipped on a word
// boundary. The full description shows when the game is selected.
export function blurb(desc, max = 110, name = '') {
  const s = (desc || '').replace(/\s+/g, ' ').trim()
  let first = s.split(/(?<=[.!?])\s/)[0] || s
  // Most descriptions open with the game's own name ("Go (Weiqi/Baduk) with…",
  // "Backgammon: the classic…"); the row already shows the name, so drop it.
  // Only when an explicit separator follows (":" "—" ","), so "Go (Weiqi) with
  // full territory scoring…" keeps its sentence instead of becoming a fragment.
  if (name && first.toLowerCase().startsWith(name.toLowerCase())) {
    const m = first.slice(name.length).match(/^\s*(?:\([^)]*\))?\s*[:,—–-]\s*(.+)$/)
    if (m && m[1].length >= 12) first = m[1][0].toUpperCase() + m[1].slice(1)
  }
  if (first.length <= max) return first
  const cut = first.slice(0, max).replace(/\s+\S*$/, '')
  return cut + '…'
}

const playersOf = (g) => g.players || { min: 2, max: 2 }
export function playersLabel(g) {
  const { min, max } = playersOf(g)
  return min === max ? `${min} players` : `${min}–${max} players`
}

// Scalable game browser: search + facets on top, and — when nobody is
// searching — a short curated "Start here" shelf followed by categories
// collapsed to headers with counts (click to expand), so the first view of 400+
// games is a screenful, not a wall. Rows are one line each; the selected row
// expands in place to the full description. A summary bar at the bottom always
// names the current selection, since the Play/Start button lives below the
// picker. Self-contained — parents pass the selection and an onChange.
export default function GamePicker({ games, value, onChange }) {
  const [q, setQ] = useState('')
  const [cat, setCat] = useState(null)
  const [multi, setMulti] = useState(false) // 3+ players only
  const [open, setOpen] = useState(() => new Set()) // expanded category groups
  const [rules, setRules] = useState(null)

  const query = q.trim().toLowerCase()
  const cats = useMemo(() => groupByCategory(games).map(([c]) => c), [games])
  const hasMulti = useMemo(() => games.some((g) => playersOf(g).max > 2), [games])

  const inCat = (g) => !cat || (g.category || 'Other') === cat
  const inMulti = (g) => !multi || playersOf(g).max > 2
  const matches = games.filter((g) => inCat(g) && inMulti(g) && relevance(g, query) > 0)
  const selected = games.find((g) => g.uid === value)
  const browsing = !query && !cat && !multi

  // Sections: [{key, label, list, collapsible}]
  let sections
  if (query) {
    const ranked = [...matches].sort((a, b) => relevance(b, query) - relevance(a, query) || a.name.localeCompare(b.name))
    sections = [{ key: 'results', label: '', list: ranked, collapsible: false }]
  } else if (browsing) {
    const byUid = new Map(games.map((g) => [g.uid, g]))
    const featured = FEATURED.map((u) => byUid.get(u)).filter(Boolean)
    sections = [
      { key: 'featured', label: 'Start here', list: featured, collapsible: false },
      ...groupByCategory(games).map(([c, list]) => ({ key: c, label: c, list, collapsible: true })),
    ]
  } else {
    sections = groupByCategory(matches).map(([c, list]) => ({ key: c, label: c, list, collapsible: false }))
  }

  const toggleGroup = (key) => setOpen((s) => { const n = new Set(s); n.has(key) ? n.delete(key) : n.add(key); return n })

  const row = (g) => {
    const active = g.uid === value
    return (
      <div key={g.uid} className={`game-row ${active ? 'active' : ''}`}>
        <button type="button" className="game-row-main" onClick={() => onChange(g.uid)} aria-pressed={active}>
          <span className="game-row-line">
            <span className="game-row-name">{g.name}{g.source === 'uploaded' ? ` · by ${g.uploader || 'community'}` : ''}</span>
            {playersOf(g).max > 2 && <span className="game-row-players">{playersLabel(g)}</span>}
            {!active && <span className="game-row-blurb">{blurb(g.description, 110, g.name)}</span>}
          </span>
          {active && (
            <span className="game-row-detail">
              <span className="game-desc">{g.description}</span>
              {g.tags?.length > 0 && <span className="game-tags">{g.tags.join(' · ')}</span>}
            </span>
          )}
        </button>
        {g.has_rules && (
          <button type="button" className="game-rules-btn" title="How to play" onClick={() => setRules(g)}>Rules</button>
        )}
      </div>
    )
  }

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
          {hasMulti && (
            <button type="button" className={`cat-chip players ${multi ? 'on' : ''}`} onClick={() => setMulti(!multi)}>3+ players</button>
          )}
        </div>
      )}
      <div className="game-list">
        {matches.length === 0 && <div className="muted small">No games match “{q}”.</div>}
        {sections.map((sec) => {
          const isOpen = !sec.collapsible || open.has(sec.key)
          return (
            <div key={sec.key} className="cat-group">
              {sec.label && (sec.collapsible ? (
                <button type="button" className={`cat-head ${isOpen ? 'open' : ''}`} onClick={() => toggleGroup(sec.key)} aria-expanded={isOpen}>
                  <span className="cat-chevron">{isOpen ? '▾' : '▸'}</span>
                  <span className="cat-label">{sec.label}</span>
                  <span className="cat-count">{sec.list.length}</span>
                </button>
              ) : (
                <div className="cat-label">{sec.label}</div>
              ))}
              {isOpen && sec.list.map(row)}
            </div>
          )
        })}
      </div>
      {selected && (
        <div className="picker-selected">
          <span className="picker-selected-label">Playing</span>
          <strong>{selected.name}</strong>
          <span className="muted small">{playersLabel(selected)} · {selected.category || 'Other'}</span>
          {selected.has_rules && (
            <button type="button" className="link" onClick={() => setRules(selected)}>Rules</button>
          )}
        </div>
      )}
      {rules && <RulesModal uid={rules.uid} name={rules.name} onClose={() => setRules(null)} />}
    </div>
  )
}
