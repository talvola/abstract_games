import { useEffect, useRef, useState } from 'react'
import { api } from './api'
import Board from './Board'

// Anonymous, no-account play using the stateless endpoints. Hotseat or vs the
// MCTS bot; game state lives in the browser.
export default function QuickPlay({ games, go }) {
  const [match, setMatch] = useState(null)
  if (!match) return <Menu games={games} go={go} onStart={setMatch} />
  return <Play match={match} setMatch={setMatch} onExit={() => setMatch(null)} go={go} />
}

function Menu({ games, go, onStart }) {
  const [uid, setUid] = useState(games[0]?.uid)
  const [mode, setMode] = useState('hotseat') // hotseat | bot
  const [size, setSize] = useState(null)
  const game = games.find((g) => g.uid === uid)
  const sizeOpt = game?.options?.size
  useEffect(() => setSize(sizeOpt ? sizeOpt.default : null), [uid]) // eslint-disable-line

  return (
    <div className="menu">
      <label>Game</label>
      <div className="game-list">
        {games.map((g) => (
          <button key={g.uid} className={`game-card ${g.uid === uid ? 'active' : ''}`} onClick={() => setUid(g.uid)}>
            <div className="game-name">{g.name}</div>
            <div className="game-desc">{g.description}</div>
            <div className="game-tags">{g.tags.join(' · ')}</div>
          </button>
        ))}
      </div>

      {sizeOpt && (
        <div className="row">
          <label>Board size</label>
          <select value={size ?? ''} onChange={(e) => setSize(Number(e.target.value))}>
            {sizeOpt.choices.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      )}

      <div className="row">
        <label>Opponent</label>
        <div className="seg">
          <button className={mode === 'hotseat' ? 'on' : ''} onClick={() => setMode('hotseat')}>Two players (hotseat)</button>
          <button className={mode === 'bot' ? 'on' : ''} onClick={() => setMode('bot')}>vs Computer</button>
        </div>
      </div>

      <button
        className="start"
        onClick={async () => {
          const r = await api.newGame(uid, size ? { size } : {})
          onStart({ uid, name: game.name, mode, botSeat: mode === 'bot' ? 1 : null, state: r.state, view: r.view })
        }}
      >
        Start
      </button>
      <button className="link" onClick={() => go({ name: 'home' })}>← back</button>
    </div>
  )
}

function Play({ match, setMatch, onExit }) {
  const { uid, view } = match
  const busy = useRef(false)

  async function applyMove(move) {
    if (busy.current || view.terminal) return
    busy.current = true
    try {
      const r = await api.move(uid, match.state, move)
      setMatch((m) => ({ ...m, state: r.state, view: r.view }))
    } finally {
      busy.current = false
    }
  }

  // Bot driver (loops through multi-move turns like Oust capture chains).
  useEffect(() => {
    if (match.mode !== 'bot' || view.terminal || view.current_player !== match.botSeat) return
    let cancelled = false
    ;(async () => {
      const b = await api.bot(uid, match.state, 300)
      if (cancelled) return
      const r = await api.move(uid, match.state, b.move)
      if (!cancelled) setMatch((m) => ({ ...m, state: r.state, view: r.view }))
    })()
    return () => { cancelled = true }
  }, [match.state, view.current_player, view.terminal]) // eslint-disable-line

  const cp = view.current_player
  const thinking = match.mode === 'bot' && !view.terminal && cp === match.botSeat
  const myTurn = !view.terminal && !thinking

  let status
  if (view.terminal) {
    const best = Math.max(...view.returns)
    const winners = view.returns.map((v, i) => (v === best ? i : -1)).filter((i) => i >= 0)
    status = winners.length === 1 && best > 0 ? `${seat(match, winners[0])} wins` : 'Draw'
  } else {
    status = `${seat(match, cp)} to move${thinking ? ' (thinking…)' : ''}`
  }

  return (
    <div className="play">
      <div className="status" style={{ borderColor: view.terminal ? '#c9a96e' : '#888' }}>{status}</div>
      <Board spec={view.render} legalMoves={myTurn ? view.legal_moves : []} onCellClick={applyMove} disabled={!myTurn} />
      {view.render.caption && <div className="caption">{view.render.caption}</div>}
      <div className="controls">
        <button onClick={onExit}>← New game</button>
      </div>
    </div>
  )
}

function seat(match, idx) {
  if (match.mode === 'bot') return idx === match.botSeat ? 'Computer' : 'You'
  return `Player ${idx + 1}`
}
