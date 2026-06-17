import { useEffect, useRef, useState } from 'react'
import { api } from './api'
import Board from './Board'

const PLAYER_NAMES = ['Player 1', 'Player 2']
const PLAYER_COLOR = ['#d23b3b', '#3b6fd2']

export default function App() {
  const [games, setGames] = useState(null)
  const [match, setMatch] = useState(null) // { uid, name, mode, botSeat, state, view }
  const [error, setError] = useState('')
  const [thinking, setThinking] = useState(false)

  useEffect(() => {
    api.listGames().then((d) => setGames(d.games)).catch((e) => setError(String(e)))
  }, [])

  if (error) return <Shell><p className="error">{error}</p></Shell>
  if (!games) return <Shell><p>Loading…</p></Shell>
  if (!match)
    return (
      <Shell>
        <Menu
          games={games}
          onStart={async (cfg) => {
            try {
              const r = await api.newGame(cfg.uid, cfg.options)
              setMatch({ ...cfg, state: r.state, view: r.view })
            } catch (e) {
              setError(String(e))
            }
          }}
        />
      </Shell>
    )

  return (
    <Shell>
      <Play
        match={match}
        setMatch={setMatch}
        thinking={thinking}
        setThinking={setThinking}
        onExit={() => setMatch(null)}
      />
    </Shell>
  )
}

function Shell({ children }) {
  return (
    <div className="app">
      <header>
        <h1>ABSTRACT GAMES</h1>
        <div className="tagline">a generic platform · phase 1</div>
      </header>
      <main>{children}</main>
    </div>
  )
}

function Menu({ games, onStart }) {
  const [uid, setUid] = useState(games[0]?.uid)
  const [mode, setMode] = useState('hotseat') // hotseat | bot
  const [size, setSize] = useState(null)

  const game = games.find((g) => g.uid === uid)
  const sizeOpt = game?.options?.size

  useEffect(() => {
    setSize(sizeOpt ? sizeOpt.default : null)
  }, [uid]) // eslint-disable-line

  return (
    <div className="menu">
      <label>Game</label>
      <div className="game-list">
        {games.map((g) => (
          <button
            key={g.uid}
            className={`game-card ${g.uid === uid ? 'active' : ''}`}
            onClick={() => setUid(g.uid)}
          >
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
            {sizeOpt.choices.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      )}

      <div className="row">
        <label>Opponent</label>
        <div className="seg">
          <button className={mode === 'hotseat' ? 'on' : ''} onClick={() => setMode('hotseat')}>
            Two players (hotseat)
          </button>
          <button className={mode === 'bot' ? 'on' : ''} onClick={() => setMode('bot')}>
            vs Computer
          </button>
        </div>
      </div>

      <button
        className="start"
        onClick={() =>
          onStart({
            uid,
            name: game.name,
            mode,
            botSeat: mode === 'bot' ? 1 : null,
            options: size ? { size } : {},
          })
        }
      >
        Start
      </button>

      {game?.bgg_url && (
        <a className="bgg" href={game.bgg_url} target="_blank" rel="noreferrer">
          rules / info on BoardGameGeek ↗
        </a>
      )}
    </div>
  )
}

function Play({ match, setMatch, thinking, setThinking, onExit }) {
  const { uid, view } = match
  const busyRef = useRef(false)

  async function applyMove(move) {
    if (busyRef.current || view.terminal) return
    busyRef.current = true
    try {
      const r = await api.move(uid, match.state, move)
      setMatch((m) => ({ ...m, state: r.state, view: r.view }))
    } finally {
      busyRef.current = false
    }
  }

  // Bot driver: whenever it's the bot's turn, play it. Loops naturally through
  // multi-move turns (e.g. Oust capture chains) since current_player stays put.
  useEffect(() => {
    if (match.mode !== 'bot' || view.terminal) return
    if (view.current_player !== match.botSeat) return
    let cancelled = false
    setThinking(true)
    ;(async () => {
      try {
        const b = await api.bot(uid, match.state, 300)
        if (cancelled) return
        const r = await api.move(uid, match.state, b.move)
        if (cancelled) return
        setMatch((m) => ({ ...m, state: r.state, view: r.view }))
      } finally {
        if (!cancelled) setThinking(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [match.state, view.current_player, view.terminal]) // eslint-disable-line

  const cp = view.current_player
  const myTurn =
    !view.terminal && (match.mode !== 'bot' || cp !== match.botSeat) && !thinking

  let status
  if (view.terminal) {
    const r = view.returns
    const best = Math.max(...r)
    const winners = r.map((v, i) => (v === best ? i : -1)).filter((i) => i >= 0)
    status =
      winners.length === 1 && best > 0
        ? `${seatLabel(match, winners[0])} wins`
        : 'Draw'
  } else {
    status = `${seatLabel(match, cp)} to move${thinking ? ' (thinking…)' : ''}`
  }

  return (
    <div className="play">
      <div className="status" style={{ borderColor: view.terminal ? '#c9a96e' : PLAYER_COLOR[cp] }}>
        {status}
      </div>

      <Board
        spec={view.render}
        legalMoves={myTurn ? view.legal_moves : []}
        onCellClick={applyMove}
        disabled={!myTurn}
      />

      {view.render.caption && <div className="caption">{view.render.caption}</div>}

      <div className="controls">
        <button onClick={onExit}>← New game</button>
      </div>
    </div>
  )
}

function seatLabel(match, seat) {
  if (match.mode === 'bot') return seat === match.botSeat ? 'Computer' : 'You'
  return PLAYER_NAMES[seat]
}
