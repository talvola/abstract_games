import { useState } from 'react'
import { api } from './api'

export default function Auth({ me, setMe }) {
  const [mode, setMode] = useState('login') // login | register
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (me === undefined) return null
  if (me) {
    return (
      <div className="auth signed-in">
        <span>
          Signed in as <strong>{me.display_name}</strong>
        </span>
        <button
          onClick={async () => {
            await api.logout()
            setMe(null)
          }}
        >
          Log out
        </button>
      </div>
    )
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const user =
        mode === 'register'
          ? await api.register(email, name, password)
          : await api.login(email, password)
      setMe(user)
    } catch (err) {
      setError(String(err.message || err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="auth" onSubmit={submit}>
      <div className="seg">
        <button type="button" className={mode === 'login' ? 'on' : ''} onClick={() => setMode('login')}>
          Log in
        </button>
        <button type="button" className={mode === 'register' ? 'on' : ''} onClick={() => setMode('register')}>
          Register
        </button>
      </div>
      <input type="email" placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      {mode === 'register' && (
        <input placeholder="display name" value={name} onChange={(e) => setName(e.target.value)} required />
      )}
      <input
        type="password"
        placeholder="password (6+ chars)"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <button className="start" type="submit" disabled={busy}>
        {mode === 'register' ? 'Create account' : 'Log in'}
      </button>
      {error && <div className="error small">{error}</div>}
    </form>
  )
}
