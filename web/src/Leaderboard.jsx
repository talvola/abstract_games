import { useEffect, useState } from 'react'
import { api } from './api'

// Per-game leaderboard. A game has its own ladder (skill doesn't transfer across
// 205 games), so pick a game and see its top rated players. Provisional ratings
// (high RD) rank last and show a "?". Names link to the player's profile. Uses a
// compact dropdown (not the full game-browser) since this is a chooser, not a launcher.
export default function Leaderboard({ games, uid: initialUid, go }) {
  const [uid, setUid] = useState(initialUid || games[0]?.uid)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!uid) return
    setData(null); setError('')
    api.leaderboard(uid).then(setData).catch((e) => setError(String(e.message || e)))
  }, [uid])

  const sorted = [...games].sort((a, b) => a.name.localeCompare(b.name))

  return (
    <div className="leaderboard">
      <h2>Leaderboards</h2>
      <select className="lb-select" value={uid} onChange={(e) => setUid(e.target.value)}>
        {sorted.map((g) => <option key={g.uid} value={g.uid}>{g.name}</option>)}
      </select>
      {error && <div className="error small">{error}</div>}
      {!data && !error && <p>Loading…</p>}
      {data && data.entries.length === 0 && (
        <div className="muted small">No rated games of {data.game_name} yet — play a ranked match to start the ladder.</div>
      )}
      {data && data.entries.length > 0 && (
        <table className="rating-table">
          <thead>
            <tr><th>#</th><th>Player</th><th>Rating</th><th>Games</th><th>W</th><th>L</th><th>D</th></tr>
          </thead>
          <tbody>
            {data.entries.map((e, i) => (
              <tr key={e.user_id}>
                <td>{i + 1}</td>
                <td><a onClick={() => go({ name: 'profile', id: e.user_id })}>{e.name}</a></td>
                <td className="rating-cell">{e.rating}{e.provisional ? '?' : ''}</td>
                <td>{e.games}</td><td>{e.wins}</td><td>{e.losses}</td><td>{e.draws}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="controls">
        <button onClick={() => go({ name: 'home' })}>← Lobby</button>
      </div>
    </div>
  )
}
