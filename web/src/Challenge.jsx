import { useEffect, useState } from 'react'
import { api } from './api'
import Auth from './Auth'
import RulesModal from './RulesModal'
import { CopyLink } from './Lobby'
import { playersLabel } from './GamePicker'

// The landing screen for an invite link (#/challenge/<seek id>): "Erik
// challenged you to Hex". Shows the game and who's asking; a signed-in
// visitor accepts in one click, an anonymous one registers or logs in right
// here (the URL doesn't change, so they land back on the Accept button).
export default function Challenge({ id, me, setMe, games, go, config }) {
  const [seek, setSeek] = useState(null)
  const [gone, setGone] = useState('')
  const [rules, setRules] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setGone(''); setSeek(null)
    api.getSeek(id).then(setSeek).catch((e) => setGone(String(e.message || e)))
  }, [id, me?.id])

  if (gone) {
    return (
      <div className="challenge">
        <div className="challenge-card">
          <h2>This challenge is no longer open</h2>
          <p className="muted small">{gone}. It was probably accepted already, or withdrawn.</p>
        </div>
        <div className="controls">
          <button className="start" onClick={() => go({ name: 'home' })}>Go to the lobby</button>
        </div>
      </div>
    )
  }
  if (!seek) return <p>Loading…</p>

  const game = games.find((g) => g.uid === seek.game_uid)
  const optionText = Object.entries(seek.options || {}).map(([k, v]) => `${k} ${v}`).join(', ')
  const seatText = { first: `${seek.creator_name} moves first`, second: 'you move first', random: 'who moves first is random' }[seek.seat_pref] || ''
  const days = config?.move_deadline_days ?? 7

  async function accept() {
    setBusy(true); setError('')
    try {
      const r = await api.acceptSeek(seek.id)
      go({ name: 'match', id: r.match_id })
    } catch (e) {
      setError(String(e.message || e))
      setBusy(false)
    }
  }

  return (
    <div className="challenge">
      <div className="challenge-card">
        <div className="cat-label">{seek.mine ? 'Your open challenge' : 'You’ve been challenged'}</div>
        <h2>{seek.mine ? seek.game_name : `${seek.creator_name} challenges you to ${seek.game_name}`}</h2>
        <div className="challenge-meta">
          {game && <span>{playersLabel(game)}</span>}
          {game?.category && <span>{game.category}</span>}
          {optionText && <span>{optionText}</span>}
          {seatText && <span>{seatText}</span>}
          {seek.creator_rating && <span>{seek.creator_name}: {seek.creator_rating.rating}{seek.creator_rating.provisional ? '?' : ''}</span>}
        </div>
        {game && <span className="game-desc">{game.description}</span>}
        <div className="muted small">
          Turn-based: you each get {days} days per move, and the game is rated.
          {game?.has_rules && <> Never played? <button className="link" onClick={() => setRules(true)}>Read the rules</button>.</>}
        </div>
      </div>

      {seek.mine ? (
        <div className="controls">
          <CopyLink seekId={seek.id} />
          <button onClick={() => go({ name: 'home' })}>← Lobby</button>
        </div>
      ) : me ? (
        <div className="controls">
          <button className="start" onClick={accept} disabled={busy}>Accept — play as {me.display_name}</button>
          <button onClick={() => go({ name: 'home' })}>Not now</button>
        </div>
      ) : (
        <>
          <p className="muted small">Log in or create a free account to accept — it takes ten seconds, no email confirmation.</p>
          <Auth me={me} setMe={setMe} />
        </>
      )}
      {error && <div className="error small">{error}</div>}
      {rules && game && <RulesModal uid={game.uid} name={game.name} onClose={() => setRules(false)} />}
    </div>
  )
}
