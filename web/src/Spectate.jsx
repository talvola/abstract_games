import { useEffect, useState } from 'react'
import { api } from './api'

// Browse human-vs-human games to watch — live games first, then recently
// finished. Clicking opens the match; MatchPlay renders spectator mode (disabled
// board, live polling, read-only chat) for non-players automatically.
export default function Spectate({ go }) {
  const [matches, setMatches] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const load = () => api.publicMatches().then((d) => setMatches(d.matches)).catch((e) => setError(String(e.message || e)))
    load()
    const t = setInterval(load, 8000)
    return () => clearInterval(t)
  }, [])

  if (error) return <div className="play"><p className="error">{error}</p><Back go={go} /></div>
  if (!matches) return <p>Loading…</p>

  const live = matches.filter((m) => m.status === 'active')
  const done = matches.filter((m) => m.status !== 'active')

  const row = (m) => {
    const vs = m.players.map((p) => p.rating ? `${p.name} (${p.rating})` : p.name).join(' vs ')
    return (
      <button key={m.id} className="match-open spectate-row" onClick={() => go({ name: 'match', id: m.id })}>
        <span>{m.game_name} · {vs}</span>
        <span className={`badge ${m.status === 'active' ? 'turn' : 'done'}`}>
          {m.status === 'active' ? '● live' : (m.winner == null ? 'draw' : `${m.players[m.winner]?.name} won`)}
        </span>
      </button>
    )
  }

  return (
    <div className="spectate">
      <h2>Watch games</h2>
      {matches.length === 0 && <div className="muted small">No public games yet — start one to get the ladder going.</div>}
      {live.length > 0 && <><div className="cat-label">Live now</div>{live.map(row)}</>}
      {done.length > 0 && <><div className="cat-label">Recently finished</div>{done.map(row)}</>}
      <Back go={go} />
    </div>
  )
}

function Back({ go }) {
  return (
    <div className="controls">
      <button onClick={() => go({ name: 'home' })}>← Lobby</button>
    </div>
  )
}
