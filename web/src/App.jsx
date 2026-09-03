import { useEffect, useState } from 'react'
import { api } from './api'
import Auth from './Auth'
import Lobby from './Lobby'
import QuickPlay from './QuickPlay'
import MatchPlay from './MatchPlay'
import Leaderboard from './Leaderboard'
import Profile from './Profile'
import Replay from './Replay'
import Spectate from './Spectate'

export default function App() {
  const [me, setMe] = useState(undefined) // undefined = loading, null = anonymous
  const [games, setGames] = useState(null)
  const [config, setConfig] = useState({ move_deadline_days: 7, email: false })
  const [screen, setScreen] = useState({ name: 'home' })

  useEffect(() => {
    api.me().then(setMe).catch(() => setMe(null))
    api.listGames().then((d) => { setGames(d.games); setConfig((c) => ({ ...c, ...d })) }).catch(() => setGames([]))
    const deep = new URLSearchParams(window.location.search).get('match')
    if (deep) setScreen({ name: 'match', id: deep })
  }, [])

  const go = (s) => setScreen(s)
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
        {!games && <p>Loading…</p>}
        {games && screen.name === 'home' && (
          <Home me={me} setMe={setMe} games={games} go={go} refreshGames={refreshGames} config={config} />
        )}
        {games && screen.name === 'quickplay' && <QuickPlay games={games} go={go} />}
        {games && screen.name === 'leaderboard' && <Leaderboard games={games} uid={screen.uid} go={go} />}
        {screen.name === 'spectate' && <Spectate go={go} />}
        {screen.name === 'profile' && <Profile id={screen.id} go={go} />}
        {screen.name === 'replay' && <Replay id={screen.id} go={go} />}
        {screen.name === 'match' && <MatchPlay id={screen.id} me={me} go={go} />}
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
