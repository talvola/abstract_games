import { useEffect, useRef, useState } from 'react'
import { api } from './api'
import Board from './Board'
import MoveLog from './MoveLog'
import { SEAT_FILL } from './colors'
import GameOptions, { defaultOptions } from './GameOptions'
import GamePicker from './GamePicker'
import RulesModal from './RulesModal'
import { defaultGameUid } from './featured'

// Anonymous, no-account play using the stateless endpoints. Hotseat or vs the
// MCTS bot; game state lives in the browser — and, so a refresh or a stray tap
// on Back doesn't lose it, in localStorage too (one game at a time).
const SAVE_KEY = 'agp.quickplay.v1'

function loadSaved() {
  try {
    const m = JSON.parse(localStorage.getItem(SAVE_KEY) || 'null')
    return m && m.uid && m.state && m.view ? m : null
  } catch { return null }
}
function save(m) {
  try { m ? localStorage.setItem(SAVE_KEY, JSON.stringify(m)) : localStorage.removeItem(SAVE_KEY) } catch { /* private mode etc. */ }
}

export default function QuickPlay({ games, go }) {
  const [match, setMatch] = useState(null)
  useEffect(() => { if (match) save(match) }, [match])
  if (!match) return <Menu games={games} go={go} onStart={setMatch} />
  return <Play match={match} setMatch={setMatch} onExit={() => { save(null); setMatch(null) }} go={go} />
}

function Menu({ games, go, onStart }) {
  const [uid, setUid] = useState(defaultGameUid(games))
  const [mode, setMode] = useState('hotseat') // hotseat | bot
  const [opts, setOpts] = useState({})
  const [saved, setSaved] = useState(loadSaved)
  const game = games.find((g) => g.uid === uid)
  const freeform = !!game?.freeform
  useEffect(() => setOpts(defaultOptions(game?.options)), [uid]) // eslint-disable-line
  useEffect(() => { if (freeform) setMode('hotseat') }, [freeform])

  const resumable = saved && !saved.view.terminal && games.some((g) => g.uid === saved.uid)

  return (
    <div className="menu">
      {resumable && (
        <div className="resume-box">
          <span>
            Unfinished game: <strong>{saved.name}</strong> {saved.mode === 'bot' ? 'vs the computer' : 'pass-and-play'}
            {saved.log?.length ? ` · ${saved.log.length} move${saved.log.length === 1 ? '' : 's'}` : ''}
          </span>
          <span className="resume-actions">
            <button className="start" onClick={() => onStart(saved)}>Resume</button>
            <button onClick={() => { save(null); setSaved(null) }}>Discard</button>
          </span>
        </div>
      )}
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
          <button className={mode === 'hotseat' ? 'on' : ''} onClick={() => setMode('hotseat')}>Pass-and-play (hotseat)</button>
          <button className={mode === 'bot' ? 'on' : ''} onClick={() => setMode('bot')} disabled={freeform}>vs Computer</button>
        </div>
      </div>
      {freeform && <div className="muted small">Unenforced board — honor system, no computer opponent.</div>}

      <button
        className="start"
        onClick={async () => {
          const r = await api.newGame(uid, opts)
          onStart({ uid, name: game.name, mode, botSeat: mode === 'bot' ? 1 : null, state: r.state, view: r.view, log: [] })
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
  const [rules, setRules] = useState(false)
  const log = match.log || []
  const withMove = (m, r) => ({ ...m, state: r.state, view: r.view, log: [...(m.log || []), { seat: r.mover, label: r.label }] })

  async function applyMove(move) {
    if (busy.current || view.terminal) return
    busy.current = true
    try {
      const r = await api.move(uid, match.state, move)
      setMatch((m) => withMove(m, r))
    } finally {
      busy.current = false
    }
  }

  // Bot driver: in bot mode the human is seat 0 and every other seat is a bot,
  // so the bot plays whenever it isn't seat 0's turn (chains through 2..N too).
  useEffect(() => {
    if (match.mode !== 'bot' || view.terminal || view.current_player === 0) return
    let cancelled = false
    ;(async () => {
      const b = await api.bot(uid, match.state, 300)
      if (cancelled) return
      const r = await api.move(uid, match.state, b.move)
      if (cancelled) return
      setMatch((m) => withMove(m, r))
    })()
    return () => { cancelled = true }
  }, [match.state, view.current_player, view.terminal]) // eslint-disable-line

  // Ask before leaving the page mid-game (the game is also saved, but the
  // prompt stops an accidental swipe-back from feeling like a loss).
  useEffect(() => {
    if (view.terminal) return
    const warn = (e) => { e.preventDefault(); e.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [view.terminal])

  const cp = view.current_player
  const thinking = match.mode === 'bot' && !view.terminal && cp !== 0
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
      <div className="match-head">
        <div className="game-name">{match.name}</div>
      </div>
      <div className="vs">
        {Array.from({ length: view.num_players || 2 }, (_, i) => i).map((i) => (
          <span key={i} className={`seat-chip ${i === cp && !view.terminal ? 'active-seat' : ''}`}>
            <span className="seat-dot" style={{ background: SEAT_FILL[i] }} />
            {seat(match, i)}
          </span>
        ))}
      </div>
      <div className="status" style={{ borderColor: view.terminal ? '#c9a96e' : '#888' }}>{status}</div>
      <div className="play-area">
        <div className="board-col">
          <Board spec={view.render} legalMoves={myTurn ? view.legal_moves : []} onMove={applyMove} disabled={!myTurn} freeform={view.freeform} currentPlayer={view.current_player} />
          {view.render.caption && <div className="caption">{view.render.caption}</div>}
        </div>
        <MoveLog moves={log} paired={!!view.render.seat_names} />
      </div>
      <div className="controls">
        <button onClick={onExit}>← New game</button>
        <button onClick={() => setRules(true)}>Rules</button>
      </div>
      {rules && <RulesModal uid={uid} name={match.name} onClose={() => setRules(false)} />}
    </div>
  )
}

// Seat label: games may name their seats (chess: White/Black) via
// render.seat_names; otherwise Player 1/2. Bot mode keeps You/Computer.
function seat(match, idx) {
  const names = match.view?.render?.seat_names
  const colour = names?.[idx]
  if (match.mode === 'bot') return (idx === 0 ? 'You' : 'Computer') + (colour ? ` (${colour})` : '')
  return colour || `Player ${idx + 1}`
}
