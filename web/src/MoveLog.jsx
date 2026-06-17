import { useEffect, useRef } from 'react'

const SEAT_COLOR = ['#d23b3b', '#3b6fd2']

// moves: [{ seat, label, player }]
export default function MoveLog({ moves }) {
  const ref = useRef(null)
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [moves.length])

  return (
    <div className="movelog">
      <div className="movelog-title">Moves</div>
      <div className="movelog-list" ref={ref}>
        {moves.length === 0 && <div className="muted small">No moves yet.</div>}
        {moves.map((m, i) => (
          <div className="movelog-row" key={i} title={m.player}>
            <span className="movelog-n">{i + 1}.</span>
            <span className="movelog-dot" style={{ background: SEAT_COLOR[m.seat] ?? '#888' }} />
            <span className="movelog-label">{m.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
