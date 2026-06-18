import { useEffect, useState } from 'react'
import { api } from './api'
import Markdown from './Markdown'

// Fetches and shows a game's local rules (the rules.md it ships with), plus a
// link to the official rules / source when the manifest provides one.
export default function RulesModal({ uid, name, onClose }) {
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    let live = true
    api.gameRules(uid).then((d) => live && setData(d)).catch((e) => live && setErr(String(e.message || e)))
    return () => { live = false }
  }, [uid])

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal rules-modal" onClick={(e) => e.stopPropagation()}>
        <div className="rules-head">
          <h2>{name || data?.name} — Rules</h2>
          <button className="modal-close" title="Close" onClick={onClose}>✕</button>
        </div>
        {err && <div className="error small">{err}</div>}
        {!data && !err && <p className="muted">Loading…</p>}
        {data && <Markdown text={data.markdown} />}
        {/^https?:\/\//i.test(data?.source_url || '') && (
          <div className="rules-source">
            <a href={data.source_url} target="_blank" rel="noopener noreferrer">Official rules / source ↗</a>
          </div>
        )}
      </div>
    </div>
  )
}
