import { useEffect, useState } from 'react'
import { api } from './api'
import Auth, { ResetPassword } from './Auth'
import Lobby from './Lobby'
import QuickPlay from './QuickPlay'
import MatchPlay from './MatchPlay'
import Leaderboard from './Leaderboard'
import Profile from './Profile'
import Replay from './Replay'
import Spectate from './Spectate'
import Challenge from './Challenge'

// Hash routing: every screen has a URL, so refresh and the Back button keep
// your place and any screen can be linked. `go()` only sets the hash; the
// hashchange listener is the single place that changes `screen`.
const HASH_OF = {
  home: () => '#/',
  quickplay: () => '#/play',
  leaderboard: (s) => (s.uid ? `#/leaderboard/${s.uid}` : '#/leaderboard'),
  spectate: () => '#/watch',
  profile: (s) => `#/user/${s.id}`,
  replay: (s) => `#/replay/${s.id}`,
  match: (s) => `#/match/${s.id}`,
  challenge: (s) => `#/challenge/${s.id}`,
  reset: (s) => `#/reset/${s.token}`,
}
export function parseHash(hash) {
  const p = (hash || '').replace(/^#\/?/, '').split('/').filter(Boolean)
  switch (p[0]) {
    case 'play': return { name: 'quickplay' }
    case 'leaderboard': return { name: 'leaderboard', uid: p[1] }
    case 'watch': return { name: 'spectate' }
    case 'user': return p[1] ? { name: 'profile', id: p[1] } : { name: 'home' }
    case 'replay': return p[1] ? { name: 'replay', id: p[1] } : { name: 'home' }
    case 'match': return p[1] ? { name: 'match', id: p[1] } : { name: 'home' }
    case 'challenge': return p[1] ? { name: 'challenge', id: p[1] } : { name: 'home' }
    case 'reset': return p[1] ? { name: 'reset', token: p[1] } : { name: 'home' }
    default: return { name: 'home' }
  }
}
function initialScreen() {
  // Legacy deep link used in notification emails: /?match=<id> → #/match/<id>
  const deep = new URLSearchParams(window.location.search).get('match')
  if (deep) {
    window.history.replaceState(null, '', `${window.location.pathname}#/match/${deep}`)
  }
  return parseHash(window.location.hash)
}

export default function App() {
  const [me, setMe] = useState(undefined) // undefined = loading, null = anonymous
  const [games, setGames] = useState(null)
  const [config, setConfig] = useState({ move_deadline_days: 7, email: false })
  const [screen, setScreen] = useState(initialScreen)
  const [slow, setSlow] = useState(false) // first load taking long (server waking up)

  useEffect(() => {
    api.me().then(setMe).catch(() => setMe(null))
    // The hosted instance sleeps when idle and takes ~a minute to wake (it
    // loads 400+ game modules), during which requests fail or hang. Keep
    // retrying with backoff rather than giving up, and tell the visitor why.
    let cancelled = false
    const slowTimer = setTimeout(() => setSlow(true), 3000)
    ;(async () => {
      for (let attempt = 0, delay = 1500; !cancelled; attempt++, delay = Math.min(delay * 1.6, 8000)) {
        try {
          const d = await api.listGames()
          if (cancelled) return
          setGames(d.games); setConfig((c) => ({ ...c, ...d }))
          return
        } catch {
          if (attempt >= 30) { if (!cancelled) setGames([]); return } // ~3 min: give up
          await new Promise((r) => setTimeout(r, delay))
        }
      }
    })()
    const onHash = () => setScreen(parseHash(window.location.hash))
    window.addEventListener('hashchange', onHash)
    return () => { cancelled = true; clearTimeout(slowTimer); window.removeEventListener('hashchange', onHash) }
  }, [])

  const go = (s) => {
    const h = (HASH_OF[s.name] || HASH_OF.home)(s)
    if (window.location.hash === h) setScreen(s) // same URL: no hashchange event
    else window.location.hash = h
  }
  const refreshGames = () => api.listGames().then((d) => setGames(d.games)).catch(() => {})

  return (
    <div className="app">
      <header>
        <h1 onClick={() => go({ name: 'home' })} style={{ cursor: 'pointer' }}>
          ABSTRACT GAMES
        </h1>
        <div className="tagline">classic &amp; modern board games · vs the computer or a friend</div>
      </header>
      <main>
        {!games && (
          <div className="loading">
            <p>Loading…</p>
            {slow && (
              <p className="muted small">
                Waking up the server — this takes about a minute after the site has been idle.
                Hang on, the page will continue by itself.
              </p>
            )}
          </div>
        )}
        {games && games.length === 0 && screen.name === 'home' && (
          <p className="error small">Couldn’t reach the server. Please reload in a moment.</p>
        )}
        {games && screen.name === 'home' && (
          <Home me={me} setMe={setMe} games={games} go={go} refreshGames={refreshGames} config={config} />
        )}
        {games && screen.name === 'quickplay' && <QuickPlay games={games} go={go} />}
        {games && screen.name === 'leaderboard' && <Leaderboard games={games} uid={screen.uid} go={go} />}
        {screen.name === 'spectate' && <Spectate go={go} />}
        {screen.name === 'profile' && <Profile id={screen.id} go={go} />}
        {screen.name === 'replay' && <Replay id={screen.id} go={go} />}
        {screen.name === 'match' && <MatchPlay id={screen.id} me={me} go={go} />}
        {screen.name === 'reset' && <ResetPassword token={screen.token} setMe={setMe} go={go} />}
        {games && screen.name === 'challenge' && <Challenge id={screen.id} me={me} setMe={setMe} games={games} go={go} config={config} />}
      </main>
    </div>
  )
}

function Home({ me, setMe, games, go, refreshGames, config }) {
  return (
    <div className="home">
      {!me && (
        <div className="hero">
          <p className="hero-tagline">
            Play <strong>{games.length}</strong> abstract board games — Chess, Go, Hive, Arimaa, and {games.length - 4} more.
          </p>
          <div className="hero-points">
            <span>Instant games vs the computer</span>
            <span>Turn-based games vs people{config.email ? ', by email' : ''}</span>
            <span>Free — no account needed to start</span>
          </div>
        </div>
      )}

      <Auth me={me} setMe={setMe} />

      <div className="quick-launch">
        <button className="start" onClick={() => go({ name: 'quickplay' })}>
          {me ? 'Quick play' : 'Quick play — no account'}
        </button>
        <div className="muted small">Pass-and-play on one screen, or vs the computer. Nothing is saved or rated.</div>
        <button className="link" onClick={() => go({ name: 'leaderboard' })}>Leaderboards</button>
        <button className="link" onClick={() => go({ name: 'spectate' })}>Watch games</button>
      </div>

      {me ? (
        <Lobby me={me} games={games} go={go} refreshGames={refreshGames} config={config} />
      ) : (
        <p className="muted">
          Sign in to play turn-based games against other people and track ongoing matches.
        </p>
      )}

      <HowItWorks config={config} open={!me} />
    </div>
  )
}

// The three-sentence explanation a first-time visitor needs. Collapsed once
// you're signed in (you've read it), open for anonymous visitors.
function HowItWorks({ config, open }) {
  const days = config.move_deadline_days
  return (
    <details className="how-it-works" open={open}>
      <summary>How it works</summary>
      <ol>
        <li>
          <strong>Quick play</strong> starts a game right now, on this screen: pass the device
          between two people, or play the computer. Pick any game, no account.
        </li>
        <li>
          <strong>Turn-based games vs people</strong> need a free account. Post an open challenge (or
          accept someone else's) and the game runs at your own pace over days or weeks.
          {config.email
            ? ' You get an email whenever it is your move.'
            : ' Check back here to see when it is your move.'}{' '}
          Each move has a <strong>{days}-day clock</strong>; miss it and the game is forfeited, so
          resign instead if you need to drop a game.
        </li>
        <li>
          <strong>Ratings</strong> are kept per game (Glicko-2). Only human-vs-human games count;
          games vs the computer are never rated. Leaderboards and profiles are public.
        </li>
        <li>
          Every game has a <strong>Rules</strong> button with the rules exactly as this site plays them.
        </li>
      </ol>
    </details>
  )
}
