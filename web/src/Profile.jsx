import { useEffect, useState } from 'react'
import { api } from './api'

// Public player profile: per-game Glicko-2 ratings + win/loss/draw records,
// best games first. A provisional rating (high RD, <~ a handful of games) shows
// a "?" so it reads as not-yet-settled. Each game row links to its leaderboard.
export default function Profile({ id, go }) {
  const [p, setP] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.userProfile(id).then(setP).catch((e) => setError(String(e.message || e)))
  }, [id])

  if (error) return <div className="play"><p className="error">{error}</p><Back go={go} /></div>
  if (!p) return <p>Loading…</p>

  return (
    <div className="profile">
      <h2>{p.display_name}</h2>
      {p.ratings.length === 0 && <div className="muted small">No rated games yet.</div>}
      {p.ratings.length > 0 && (
        <table className="rating-table">
          <thead>
            <tr><th>Game</th><th>Rating</th><th>W</th><th>L</th><th>D</th></tr>
          </thead>
          <tbody>
            {p.ratings.map((r) => (
              <tr key={r.game_uid}>
                <td><a onClick={() => go({ name: 'leaderboard', uid: r.game_uid })}>{r.game_name}</a></td>
                <td className="rating-cell">{r.rating}{r.provisional ? '?' : ''}</td>
                <td>{r.wins}</td><td>{r.losses}</td><td>{r.draws}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
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
