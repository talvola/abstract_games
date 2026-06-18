import { useEffect, useRef, useState } from 'react'
import { api } from './api'
import Board from './Board'
import MoveLog from './MoveLog'
import { SEAT_FILL } from './colors'
import GameOptions, { defaultOptions } from './GameOptions'
import GamePicker from './GamePicker'
import RulesModal from './RulesModal'

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
  const [opts, setOpts] = useState({})
  const game = games.find((g) => g.uid === uid)
  useEffect(() => setOpts(defaultOptions(game?.options)), [uid]) // eslint-disable-line

  return (
    <div className="menu">
      <label>Game</label>
      <GamePicker games={games} value={uid} onChange={setUid} />

      {game?.options && Object.keys(game.options).length > 0 && (
        <div className="form-grid">
          <GameOptions options={game.options} values={opts} onChange={(k, v) => setOpts((o) => ({ ...o, [k]: v }))} />
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
          const r = await api.newGame(uid, opts)
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
  const [log, setLog] = useState([])
  const [rules, setRules] = useState(false)
  const addLog = (r) => setLog((prev) => [...prev, { seat: r.mover, label: r.label }])

  async function applyMove(move) {
    if (busy.current || view.terminal) return
    busy.current = true
    try {
      const r = await api.move(uid, match.state, move)
      addLog(r)
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
      if (cancelled) return
      addLog(r)
      setMatch((m) => ({ ...m, state: r.state, view: r.view }))
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
      <div className="vs">
        {[0, 1].map((i) => (
          <span key={i} className={`seat-chip ${i === cp && !view.terminal ? 'active-seat' : ''}`}>
            <span className="seat-dot" style={{ background: SEAT_FILL[i] }} />
            {seat(match, i)}
          </span>
        ))}
      </div>
      <div className="status" style={{ borderColor: view.terminal ? '#c9a96e' : '#888' }}>{status}</div>
      <div className="play-area">
        <div className="board-col">
          <Board spec={view.render} legalMoves={myTurn ? view.legal_moves : []} onMove={applyMove} disabled={!myTurn} />
          {view.render.caption && <div className="caption">{view.render.caption}</div>}
        </div>
        <MoveLog moves={log} />
      </div>
      <div className="controls">
        <button onClick={onExit}>← New game</button>
        <button onClick={() => setRules(true)}>Rules</button>
      </div>
      {rules && <RulesModal uid={uid} name={match.name} onClose={() => setRules(false)} />}
    </div>
  )
}

function seat(match, idx) {
  if (match.mode === 'bot') return idx === match.botSeat ? 'Computer' : 'You'
  return `Player ${idx + 1}`
}
