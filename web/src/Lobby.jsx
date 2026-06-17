import { useEffect, useState } from 'react'
import { api } from './api'

export default function Lobby({ me, games, go, refreshGames }) {
  const [seeks, setSeeks] = useState([])
  const [matches, setMatches] = useState([])
  const [error, setError] = useState('')

  async function refresh() {
    try {
      const [s, m] = await Promise.all([api.seeks(), api.myMatches()])
      setSeeks(s.seeks)
      setMatches(m.matches)
    } catch (e) {
      setError(String(e.message || e))
    }
  }

  useEffect(() => {
    refresh()
    const t = setInterval(refresh, 6000) // pick up opponents' moves / new challenges
    return () => clearInterval(t)
  }, [])

  return (
    <div className="lobby">
      {error && <div className="error small">{error}</div>}
      <NewChallenge games={games} go={go} onCreated={refresh} />

      <section>
        <h2>Open challenges</h2>
        {seeks.length === 0 && <div className="muted small">No open challenges.</div>}
        {seeks.map((s) => (
          <div className="seek-row" key={s.id}>
            <span>
              <strong>{s.creator_name}</strong> · {s.game_name}
              {s.options?.size ? ` (size ${s.options.size})` : ''}
            </span>
            {s.mine ? (
              <button
                onClick={async () => {
                  await api.cancelSeek(s.id)
                  refresh()
                }}
              >
                Cancel
              </button>
            ) : (
              <button
                className="accent"
                onClick={async () => {
                  const r = await api.acceptSeek(s.id)
                  go({ name: 'match', id: r.match_id })
                }}
              >
                Accept
              </button>
            )}
          </div>
        ))}
      </section>

      <section>
        <h2>Your games</h2>
        {matches.length === 0 && <div className="muted small">No games yet.</div>}
        {matches.map((m) => (
          <button className="match-row" key={m.id} onClick={() => go({ name: 'match', id: m.id })}>
            <span>
              {m.game_name} · vs <strong>{m.opponent}</strong>
            </span>
            <span className={`badge ${badgeClass(m)}`}>{badgeText(m)}</span>
          </button>
        ))}
      </section>

      <AddGame onUploaded={() => { refreshGames(); refresh() }} />
    </div>
  )
}

function AddGame({ onUploaded }) {
  const [file, setFile] = useState(null)
  const [msg, setMsg] = useState('')
  const [ok, setOk] = useState(false)
  const [busy, setBusy] = useState(false)

  async function upload() {
    if (!file) return
    setBusy(true); setOk(false); setMsg('Validating & registering…')
    try {
      const d = await api.uploadGame(file)
      setOk(true)
      setMsg(`Added “${d.name}” (v${d.version}). It's now playable below.`)
      setFile(null)
      onUploaded()
    } catch (e) {
      setMsg(String(e.message || e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="add-game">
      <h2>Add a game</h2>
      <div className="muted small">
        Upload a game package (.zip) built with the dev kit. It's validated and
        registered on the spot — no redeploy.{' '}
        <a href="/api/devkit" download>Download the dev kit ↓</a>
      </div>
      <div className="upload-row">
        <input type="file" accept=".zip" onChange={(e) => setFile(e.target.files[0] || null)} />
        <button className="start" onClick={upload} disabled={!file || busy}>Upload</button>
      </div>
      {msg && <pre className={`upload-msg ${ok ? 'good' : msg && !busy ? 'bad' : ''}`}>{msg}</pre>}
    </section>
  )
}

function badgeText(m) {
  if (m.status === 'finished') {
    if (m.winner == null) return 'Draw'
    return m.winner_is_me ? 'You won' : 'You lost'
  }
  return m.my_turn ? 'Your turn' : 'Waiting'
}
function badgeClass(m) {
  if (m.status === 'finished') return m.winner_is_me ? 'win' : 'done'
  return m.my_turn ? 'turn' : 'wait'
}

function NewChallenge({ games, go, onCreated }) {
  const [uid, setUid] = useState(games[0]?.uid)
  const [size, setSize] = useState(null)
  const [opponent, setOpponent] = useState('human') // human | computer
  const [seat, setSeat] = useState('random')
  const [difficulty, setDifficulty] = useState(300)
  const [busy, setBusy] = useState(false)

  const game = games.find((g) => g.uid === uid)
  const sizeOpt = game?.options?.size
  useEffect(() => setSize(sizeOpt ? sizeOpt.default : null), [uid]) // eslint-disable-line

  async function create() {
    setBusy(true)
    try {
      const options = size ? { size } : {}
      if (opponent === 'computer') {
        const r = await api.newBotMatch(uid, options, seat === 'random' ? 'random' : seat, difficulty)
        go({ name: 'match', id: r.match_id })
      } else {
        await api.createSeek(uid, options, seat)
        onCreated()
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="new-challenge">
      <h2>New game</h2>
      <div className="form-grid">
        <label>Game</label>
        <select value={uid} onChange={(e) => setUid(e.target.value)}>
          {games.map((g) => (
            <option key={g.uid} value={g.uid}>{g.name}</option>
          ))}
        </select>

        {sizeOpt && (
          <>
            <label>Board size</label>
            <select value={size ?? ''} onChange={(e) => setSize(Number(e.target.value))}>
              {sizeOpt.choices.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </>
        )}

        <label>Opponent</label>
        <select value={opponent} onChange={(e) => setOpponent(e.target.value)}>
          <option value="human">Open challenge (another person)</option>
          <option value="computer">Computer</option>
        </select>

        <label>You play</label>
        <select value={seat} onChange={(e) => setSeat(e.target.value)}>
          <option value="first">First</option>
          <option value="second">Second</option>
          <option value="random">Random</option>
        </select>

        {opponent === 'computer' && (
          <>
            <label>Difficulty</label>
            <select value={difficulty} onChange={(e) => setDifficulty(Number(e.target.value))}>
              <option value={80}>Easy</option>
              <option value={300}>Medium</option>
              <option value={1200}>Hard</option>
            </select>
          </>
        )}
      </div>
      <button className="start" onClick={create} disabled={busy}>
        {opponent === 'computer' ? 'Start game' : 'Post challenge'}
      </button>
    </section>
  )
}
