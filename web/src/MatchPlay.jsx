import { useEffect, useRef, useState } from 'react'
import { api } from './api'
import Board from './Board'

// Correspondence match screen. Polls while waiting so an opponent's (or bot's)
// move appears without a manual refresh.
export default function MatchPlay({ id, me, go }) {
  const [m, setM] = useState(null)
  const [error, setError] = useState('')
  const busy = useRef(false)

  function load() {
    return api.getMatch(id).then(setM).catch((e) => setError(String(e.message || e)))
  }

  useEffect(() => {
    load()
  }, [id])

  useEffect(() => {
    if (!m || m.terminal || m.my_turn) return
    const t = setInterval(load, 3000)
    return () => clearInterval(t)
  }, [m?.my_turn, m?.terminal, id]) // eslint-disable-line

  async function play(move) {
    if (busy.current || !m.my_turn) return
    busy.current = true
    try {
      const r = await api.matchMove(id, move)
      setM(r)
    } catch (e) {
      setError(String(e.message || e))
    } finally {
      busy.current = false
    }
  }

  if (error) return <div className="play"><p className="error">{error}</p><Back go={go} /></div>
  if (!m) return <p>Loading…</p>

  const opponent =
    m.my_seat != null ? m.players[1 - m.my_seat]?.name : m.players.map((p) => p.name).join(' vs ')
  let status, color
  if (m.terminal) {
    if (m.winner == null) { status = 'Draw'; color = '#c9a96e' }
    else if (m.winner === m.my_seat) { status = 'You win'; color = '#5cba6b' }
    else { status = m.my_seat == null ? `${m.players[m.winner]?.name} wins` : 'You lost'; color = '#e86050' }
  } else if (m.my_turn) {
    status = 'Your turn'; color = '#5cba6b'
  } else {
    status = `Waiting for ${opponent}`; color = '#8a7a62'
  }

  return (
    <div className="play">
      <div className="match-head">
        <div className="game-name">{m.game_name}</div>
        <div className="vs">
          {m.players.map((p, i) => (
            <span key={i} className={i === m.current_player && !m.terminal ? 'active-seat' : ''}>
              {p.name}{p.type === 'bot' ? ' 🤖' : ''}{m.my_seat === i ? ' (you)' : ''}
              {i === 0 ? '  ·  ' : ''}
            </span>
          ))}
        </div>
      </div>

      <div className="status" style={{ borderColor: color, color }}>{status}</div>

      <Board
        spec={m.render}
        legalMoves={m.my_turn ? m.legal_moves : []}
        onMove={play}
        disabled={!m.my_turn}
      />
      {m.render.caption && <div className="caption">{m.render.caption}</div>}

      <div className="controls">
        <button onClick={() => go({ name: 'home' })}>← Lobby</button>
        {!m.terminal && m.my_seat != null && (
          <button
            className="danger"
            onClick={async () => {
              if (!window.confirm('Resign this game? Your opponent wins.')) return
              try { setM(await api.resignMatch(id)) } catch (e) { setError(String(e.message || e)) }
            }}
          >
            Resign
          </button>
        )}
      </div>
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
