import { useEffect, useRef, useState } from 'react'
import { api } from './api'

// Match chat thread. Polls alongside the match; only players (canPost) get the
// input. Self-contained — drop into the match screen. Signed-in viewers can
// report or block the author of anyone else's message (the server then hides
// that author's messages from them; unblock lives in the Account panel).
export default function Chat({ matchId, meId, canPost }) {
  const [msgs, setMsgs] = useState([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [reported, setReported] = useState(() => new Set())
  const [modError, setModError] = useState('')
  const endRef = useRef(null)

  const load = () => api.matchMessages(matchId).then((d) => setMsgs(d.messages)).catch(() => {})
  useEffect(() => {
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [matchId])

  useEffect(() => { endRef.current?.scrollIntoView({ block: 'nearest' }) }, [msgs.length])

  async function report(m) {
    const reason = window.prompt(`Report this message from ${m.name}? Add a short reason (optional):`, '')
    if (reason === null) return
    setModError('')
    try {
      await api.reportMessage(m.id, reason.trim())
      setReported((r) => new Set(r).add(m.id))
    } catch (err) {
      setModError(String(err.message || err))
    }
  }

  async function block(m) {
    if (!window.confirm(`Block ${m.name}? You won't see their chat messages or open challenges. You can unblock them from your Account panel.`)) return
    setModError('')
    try {
      await api.blockUser(m.user_id)
      await load()
    } catch (err) {
      setModError(String(err.message || err))
    }
  }

  async function send(e) {
    e.preventDefault()
    const body = text.trim()
    if (!body || busy) return
    setBusy(true)
    try {
      await api.postMessage(matchId, body)
      setText('')
      await load()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="chat">
      <div className="chat-title">Chat</div>
      <div className="chat-log">
        {msgs.length === 0 && <div className="muted small">No messages yet.</div>}
        {msgs.map((m, i) => (
          <div key={m.id ?? i} className={`chat-msg ${m.user_id === meId ? 'mine' : ''}`}>
            <span className="chat-name">{m.name}:</span> <span className="chat-body">{m.body}</span>
            {meId != null && m.user_id !== meId && m.id != null && (
              <span className="chat-actions">
                {reported.has(m.id)
                  ? <span className="muted">Reported — thanks</span>
                  : <button type="button" className="link" onClick={() => report(m)}>Report</button>}
                <button type="button" className="link" onClick={() => block(m)}>Block</button>
              </span>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>
      {modError && <div className="error small">{modError}</div>}
      {canPost ? (
        <form className="chat-input" onSubmit={send}>
          <input value={text} maxLength={1000} placeholder="Say something…"
            onChange={(e) => setText(e.target.value)} />
          <button type="submit" disabled={busy || !text.trim()}>Send</button>
        </form>
      ) : (
        <div className="muted small">Sign in as a player to chat.</div>
      )}
    </div>
  )
}
