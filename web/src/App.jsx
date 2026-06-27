import { useEffect, useState } from 'react'
import { api } from './api'
import Auth from './Auth'
import Lobby from './Lobby'
import QuickPlay from './QuickPlay'
import MatchPlay from './MatchPlay'
import Leaderboard from './Leaderboard'
import Profile from './Profile'

export default function App() {
  const [me, setMe] = useState(undefined) // undefined = loading, null = anonymous
  const [games, setGames] = useState(null)
  const [screen, setScreen] = useState({ name: 'home' })

  useEffect(() => {
    api.me().then(setMe).catch(() => setMe(null))
    api.listGames().then((d) => setGames(d.games)).catch(() => setGames([]))
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
        <div className="tagline">a generic platform · phase 3</div>
      </header>
      <main>
        {!games && <p>Loading…</p>}
        {games && screen.name === 'home' && (
          <Home me={me} setMe={setMe} games={games} go={go} refreshGames={refreshGames} />
        )}
        {games && screen.name === 'quickplay' && <QuickPlay games={games} go={go} />}
        {games && screen.name === 'leaderboard' && <Leaderboard games={games} uid={screen.uid} go={go} />}
        {screen.name === 'profile' && <Profile id={screen.id} go={go} />}
        {screen.name === 'match' && <MatchPlay id={screen.id} me={me} go={go} />}
      </main>
    </div>
  )
}

function Home({ me, setMe, games, go, refreshGames }) {
  return (
    <div className="home">
      <Auth me={me} setMe={setMe} />

      <div className="quick-launch">
        <button className="start" onClick={() => go({ name: 'quickplay' })}>
          Quick play — no account
        </button>
        <div className="muted small">Hotseat or vs the computer, right now.</div>
        <button className="link" onClick={() => go({ name: 'leaderboard' })}>🏆 Leaderboards</button>
      </div>

      {me ? (
        <Lobby me={me} games={games} go={go} refreshGames={refreshGames} />
      ) : (
        <p className="muted">
          Sign in to play correspondence games against other people and track ongoing matches.
        </p>
      )}
    </div>
  )
}
