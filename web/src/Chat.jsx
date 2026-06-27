import { useEffect, useRef, useState } from 'react'
import { api } from './api'

// Match chat thread. Polls alongside the match; only players (canPost) get the
// input. Self-contained — drop into the match screen.
export default function Chat({ matchId, meId, canPost }) {
  const [msgs, setMsgs] = useState([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef(null)

  const load = () => api.matchMessages(matchId).then((d) => setMsgs(d.messages)).catch(() => {})
  useEffect(() => {
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [matchId])

  useEffect(() => { endRef.current?.scrollIntoView({ block: 'nearest' }) }, [msgs.length])

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
          <div key={i} className={`chat-msg ${m.user_id === meId ? 'mine' : ''}`}>
            <span className="chat-name">{m.name}:</span> <span className="chat-body">{m.body}</span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
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
