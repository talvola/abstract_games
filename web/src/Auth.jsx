import { useState } from 'react'
import { api } from './api'

// Sign-in box (login / register / forgot password) and, once signed in, the
// identity line with an inline account panel (display name, password).
export default function Auth({ me, setMe }) {
  const [mode, setMode] = useState('login') // login | register | forgot
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [busy, setBusy] = useState(false)
  const [account, setAccount] = useState(false)

  if (me === undefined) return null
  if (me) {
    return (
      <div className="auth-wrap">
        <div className="auth signed-in">
          <span>
            Signed in as <strong>{me.display_name}</strong>
          </span>
          <span className="auth-actions">
            <button onClick={() => setAccount((a) => !a)}>{account ? 'Close' : 'Account'}</button>
            <button
              onClick={async () => {
                await api.logout()
                setMe(null)
              }}
            >
              Log out
            </button>
          </span>
        </div>
        {account && <AccountPanel me={me} setMe={setMe} onDone={() => setAccount(false)} />}
      </div>
    )
  }

  async function submit(e) {
    e.preventDefault()
    setError(''); setInfo('')
    setBusy(true)
    try {
      if (mode === 'forgot') {
        await api.forgotPassword(email)
        setInfo('If that address has an account, a reset link is on its way. Check your inbox (and spam) — the link works for one hour.')
      } else {
        const user = mode === 'register'
          ? await api.register(email, name, password)
          : await api.login(email, password)
        setMe(user)
      }
    } catch (err) {
      setError(String(err.message || err))
    } finally {
      setBusy(false)
    }
  }

  const pick = (m) => { setMode(m); setError(''); setInfo('') }

  return (
    <form className="auth" onSubmit={submit}>
      <div className="seg">
        <button type="button" className={mode === 'login' ? 'on' : ''} onClick={() => pick('login')}>
          Log in
        </button>
        <button type="button" className={mode === 'register' ? 'on' : ''} onClick={() => pick('register')}>
          Register
        </button>
      </div>
      <input type="email" placeholder="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      {mode === 'register' && (
        <input placeholder="display name" autoComplete="nickname" value={name} onChange={(e) => setName(e.target.value)} required />
      )}
      {mode !== 'forgot' && (
        <input
          type="password"
          placeholder="password (6+ chars)"
          autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      )}
      {mode === 'forgot' && (
        <div className="muted small">Enter your account's email and we'll send a link to choose a new password.</div>
      )}
      <button className="start" type="submit" disabled={busy}>
        {mode === 'register' ? 'Create account' : mode === 'forgot' ? 'Send reset link' : 'Log in'}
      </button>
      <div className="auth-links">
        {mode === 'login' && <button type="button" className="link" onClick={() => pick('forgot')}>Forgot password?</button>}
        {mode === 'forgot' && <button type="button" className="link" onClick={() => pick('login')}>← Back to log in</button>}
      </div>
      {info && <div className="muted small">{info}</div>}
      {error && <div className="error small">{error}</div>}
    </form>
  )
}

function AccountPanel({ me, setMe, onDone }) {
  const [name, setName] = useState(me.display_name)
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function save(e) {
    e.preventDefault()
    setMsg(''); setError(''); setBusy(true)
    try {
      const fields = {}
      if (name.trim() !== me.display_name) fields.display_name = name
      if (next) { fields.new_password = next; fields.current_password = current }
      if (Object.keys(fields).length === 0) { setMsg('Nothing to change.'); return }
      const user = await api.updateAccount(fields)
      setMe(user)
      setCurrent(''); setNext('')
      setMsg('Saved.')
    } catch (err) {
      setError(String(err.message || err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="auth account-panel" onSubmit={save}>
      <div className="cat-label">Account</div>
      <div className="muted small">Email: {me.email}</div>
      <label className="small muted">Display name</label>
      <input value={name} onChange={(e) => setName(e.target.value)} maxLength={64} required />
      <label className="small muted">Change password</label>
      <input type="password" placeholder="current password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
      <input type="password" placeholder="new password (6+ chars)" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
      <div className="challenge-actions">
        <button className="start" type="submit" disabled={busy}>Save</button>
        <button type="button" onClick={onDone}>Done</button>
      </div>
      {msg && <div className="muted small">{msg}</div>}
      {error && <div className="error small">{error}</div>}
    </form>
  )
}

// #/reset/<token> — landing screen for the emailed reset link.
export function ResetPassword({ token, setMe, go }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError(''); setBusy(true)
    try {
      const user = await api.resetPassword(token, password)
      setMe(user)
      go({ name: 'home' })
    } catch (err) {
      setError(String(err.message || err))
      setBusy(false)
    }
  }

  return (
    <div className="challenge">
      <form className="auth" onSubmit={submit}>
        <div className="cat-label">Choose a new password</div>
        <input type="password" placeholder="new password (6+ chars)" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} required autoFocus />
        <button className="start" type="submit" disabled={busy}>Set password and sign in</button>
        {error && <div className="error small">{error}</div>}
      </form>
      <div className="controls">
        <button onClick={() => go({ name: 'home' })}>← Home</button>
      </div>
    </div>
  )
}
