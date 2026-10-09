import { useEffect, useRef } from 'react'
import { seatDotStyle } from './colors'

// moves: [{ seat, label, player }]
// paired: chess-style "1. e4 a5" rows (two plies per numbered turn). Only for
// games that opt in via render.seat_names, and only while the log strictly
// alternates seat 0, 1, 0, 1 — a game where one side makes several plies in a
// row (backgammon dice, a mill's removal, Arimaa steps) falls back to one
// numbered row per ply rather than mis-pairing them.
export default function MoveLog({ moves, paired = false, seatColors }) {
  const ref = useRef(null)
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [moves.length])

  const alternates = moves.every((m, i) => m.seat === i % 2)
  const rows = paired && alternates
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
                <span className="movelog-dot" style={seatDotStyle(m.seat, seatColors)} />
                <span className="movelog-label">{m.label}</span>
              </span>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
