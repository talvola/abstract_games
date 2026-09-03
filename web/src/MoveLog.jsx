import { useEffect, useRef } from 'react'
import { SEAT_FILL } from './colors'

// moves: [{ seat, label, player }]
// paired: chess-style "1. e4 a5" rows (two plies per numbered turn). Only for
// games that opt in via render.seat_names — games with multi-move turns
// (Arimaa) or 3+ seats keep one numbered row per ply.
export default function MoveLog({ moves, paired = false }) {
  const ref = useRef(null)
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [moves.length])

  const rows = paired
    ? Array.from({ length: Math.ceil(moves.length / 2) }, (_, i) => moves.slice(2 * i, 2 * i + 2))
    : moves.map((m) => [m])

  return (
    <div className="movelog">
      <div className="movelog-title">Moves</div>
      <div className="movelog-list" ref={ref}>
        {moves.length === 0 && <div className="muted small">No moves yet.</div>}
        {rows.map((row, i) => (
          <div className="movelog-row" key={i}>
            <span className="movelog-n">{i + 1}.</span>
            {row.map((m, j) => (
              <span className="movelog-ply" key={j} title={m.player}>
                <span className="movelog-dot" style={{ background: SEAT_FILL[m.seat] ?? '#888' }} />
                <span className="movelog-label">{m.label}</span>
              </span>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
