import { useEffect, useState } from 'react'
import { api } from './api'
import Board from './Board'
import { SEAT_FILL } from './colors'

// Step-through replay of a finished (or ongoing) match. Fetches one render frame
// per ply from the server and scrubs through them with first/prev/next/last + a
// slider. The Board is reused in disabled mode — no move input, just display.
export default function Replay({ id, go }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [i, setI] = useState(0)

  useEffect(() => {
    api.matchReplay(id)
      .then((d) => { setData(d); setI(d.frames.length - 1) }) // open on the final position
      .catch((e) => setError(String(e.message || e)))
  }, [id])

  // Arrow keys scrub.
  useEffect(() => {
    if (!data) return
    const onKey = (e) => {
      if (e.key === 'ArrowLeft') setI((x) => Math.max(0, x - 1))
      if (e.key === 'ArrowRight') setI((x) => Math.min(data.frames.length - 1, x + 1))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [data])

  if (error) return <div className="play"><p className="error">{error}</p><Back go={go} /></div>
  if (!data) return <p>Loading…</p>

  const n = data.frames.length
  const f = data.frames[i]
  const last = n - 1
  const result = data.status === 'finished'
    ? (data.winner == null ? 'Draw' : `${data.players[data.winner]?.name} wins`)
    : 'In progress'

  return (
    <div className="play replay">
      <div className="match-head">
        <div className="game-name">{data.game_name} · replay</div>
        <div className="vs">
          {data.players.map((p, s) => (
            <span key={s} className="seat-chip">
              <span className="seat-dot" style={{ background: SEAT_FILL[s] }} />
              {p.name}{p.type === 'bot' ? ' 🤖' : ''}
            </span>
          ))}
          <span className="muted small">· {result}</span>
        </div>
      </div>

      <div className="replay-status">
        Move {i} / {last}
        {f.mover && <> — <strong style={{ color: SEAT_FILL[data.players.findIndex((p) => p.name === f.mover)] }}>{f.mover}</strong>: {f.label}</>}
        {i === 0 && <> — starting position</>}
      </div>

      <div className="board-col">
        <Board spec={f.render} legalMoves={[]} onMove={() => {}} disabled={true} currentPlayer={-1} />
        {f.caption && <div className="caption">{f.caption}</div>}
      </div>

      <div className="replay-controls">
        <button onClick={() => setI(0)} disabled={i === 0}>⏮</button>
        <button onClick={() => setI((x) => Math.max(0, x - 1))} disabled={i === 0}>◀</button>
        <input type="range" min={0} max={last} value={i} onChange={(e) => setI(Number(e.target.value))} />
        <button onClick={() => setI((x) => Math.min(last, x + 1))} disabled={i === last}>▶</button>
        <button onClick={() => setI(last)} disabled={i === last}>⏭</button>
      </div>

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
