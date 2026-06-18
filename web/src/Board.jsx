import { useEffect, useState } from 'react'
import { SEAT_FILL, SEAT_STROKE } from './colors'

// Generic renderer + move input. Draws ANY game from its RenderSpec and derives
// interaction from the legal-move list. A move is a ">"-separated PATH of cell
// ids (cells use "," so they never clash with ">"), optionally followed by a
// "=CHOICE" suffix for a move that needs a pick (e.g. pawn promotion "2,4>2,5=Q").
//   * placement games -> single-cell moves -> one click.
//   * from-to games    -> "from>to"        -> click source, then target.
//   * choice moves     -> a picker appears when a destination has >1 option.

const colors = (o) => ({ fill: SEAT_FILL[o] ?? '#aaa', stroke: SEAT_STROKE[o] ?? '#555' })
const PIECE_NAMES = { Q: 'Queen', R: 'Rook', N: 'Knight', B: 'Bishop', K: 'King', P: 'Pawn' }
// Friendly labels for any "=choice" suffix (chess promotion pieces, stone colours, …).
const CHOICE_NAMES = { ...PIECE_NAMES, red: 'Red', blue: 'Blue' }

// "2,4>2,5=Q" -> { cells: ["2,4","2,5"], choice: "Q" }
function parseMove(m) {
  const eq = m.indexOf('=')
  const pathPart = eq >= 0 ? m.slice(0, eq) : m
  return { cells: pathPart.split('>'), choice: eq >= 0 ? m.slice(eq + 1) : null }
}
const sameCells = (a, b) => a.length === b.length && a.every((c, i) => c === b[i])

// A move is a cell path if every ">"-segment (minus any "=choice") is a cell id.
const CELL_RE = /^-?\d+,-?\d+$/
const isCellMove = (m) => m.split('>').every((seg) => CELL_RE.test(seg.split('=')[0]))
// Non-cell legal moves render as action buttons (e.g. pie-rule "swap", "pass").
const ACTION_LABELS = { swap: 'Swap (pie rule)', pass: 'Pass', end: 'End turn' }

function squareCells(b) {
  const cells = []
  for (let r = 0; r < b.height; r++) for (let c = 0; c < b.width; c++) cells.push({ id: `${c},${r}`, x: c, y: r })
  return cells
}
const SQRT3 = Math.sqrt(3)
function hexCells(b) {
  const cells = []
  if (b.shape === 'rhombus') {
    for (let r = 0; r < b.height; r++) for (let c = 0; c < b.width; c++)
      cells.push({ id: `${c},${r}`, x: SQRT3 * (c + r / 2), y: 1.5 * r })
    return cells
  }
  const s = b.size
  for (let q = -(s - 1); q <= s - 1; q++) for (let r = -(s - 1); r <= s - 1; r++)
    if (Math.abs(q + r) <= s - 1) cells.push({ id: `${q},${r}`, x: SQRT3 * q + (SQRT3 / 2) * r, y: 1.5 * r })
  return cells
}
function hexPoly(cx, cy, s) {
  return Array.from({ length: 6 }, (_, i) => {
    const a = (Math.PI / 180) * (60 * i - 30)
    return `${cx + s * Math.cos(a)},${cy + s * Math.sin(a)}`
  }).join(' ')
}
const eqPrefix = (path, sel) => sel.every((c, i) => path[i] === c)

export default function Board({ spec, legalMoves, onMove, disabled }) {
  const [sel, setSel] = useState([])
  const [promo, setPromo] = useState(null) // { cells, options: [{choice, move}] }
  useEffect(() => { setSel([]); setPromo(null) }, [JSON.stringify(legalMoves), disabled])

  if (!spec) return null
  const board = spec.board
  const cellMoves = (legalMoves || []).filter(isCellMove)
  const actions = (legalMoves || []).filter((m) => !isCellMove(m))
  const moves = cellMoves.map((m) => ({ raw: m, ...parseMove(m) }))
  const paths = moves.map((m) => m.cells)

  const nextCells = new Set()
  for (const p of paths) if (p.length > sel.length && eqPrefix(p, sel)) nextCells.add(p[sel.length])
  const selSet = new Set(sel)
  const sources = new Set(paths.map((p) => p[0]))
  const firstStep = sel.length === 0

  function click(cellId) {
    if (disabled || promo) return
    const cand = [...sel, cellId]
    const matches = moves.filter((m) => sameCells(m.cells, cand))
    if (matches.length === 1) { onMove(matches[0].raw); setSel([]); return }
    if (matches.length > 1) {                       // a move that needs a choice (e.g. promotion)
      setPromo({ cells: cand, options: matches.map((m) => ({ choice: m.choice, move: m.raw })) })
      return
    }
    if (paths.some((p) => p.length > cand.length && eqPrefix(p, cand))) setSel(cand)
    else if (sel.length && sources.has(cellId)) setSel([cellId])
    else setSel([])
  }

  const isHex = board.type === 'hex'
  const isPoly = board.type === 'polygons'
  const pieces = {}
  for (const p of spec.pieces || []) pieces[p.cell] = p
  const hl = {}
  for (const h of spec.highlights || []) hl[h.cell] = h.kind

  // Uniform shape model for every board type: {id, cx, cy, poly, r, parity}.
  let R = 30, px = null, shapes
  if (isPoly) {
    shapes = (board.cells || []).map((c) => {
      const pts = c.points
      const cx = pts.reduce((a, p) => a + p[0], 0) / pts.length
      const cy = pts.reduce((a, p) => a + p[1], 0) / pts.length
      const rad = pts.reduce((a, p) => a + Math.hypot(p[0] - cx, p[1] - cy), 0) / pts.length
      let parity = 0
      const m2 = c.id.match(/^(-?\d+),(-?\d+)$/)
      if (m2) parity = (((2 * +m2[2] - +m2[1]) % 3) + 3) % 3 ? 1 : 0
      return { id: c.id, cx, cy, poly: pts.map((p) => p.join(',')).join(' '), r: rad * 0.6, parity }
    })
  } else {
    const cells = isHex ? hexCells(board) : squareCells(board)
    px = (v) => v * (isHex ? R : R * 2.2)
    shapes = cells.map((c) => {
      const cx = px(c.x), cy = px(c.y)
      const poly = isHex ? hexPoly(cx, cy, R)
        : `${cx - R},${cy - R} ${cx + R},${cy - R} ${cx + R},${cy + R} ${cx - R},${cy + R}`
      return { id: c.id, cx, cy, poly, r: R, parity: (c.x + c.y) % 2 }
    })
  }

  const allx = [], ally = []
  shapes.forEach((s) => s.poly.split(' ').forEach((p) => {
    const [x, y] = p.split(',').map(Number); allx.push(x); ally.push(y)
  }))
  const mrg = (Math.max(...allx) - Math.min(...allx)) * 0.05 + 12
  const vb = `${Math.min(...allx) - mrg} ${Math.min(...ally) - mrg} ${Math.max(...allx) - Math.min(...allx) + 2 * mrg} ${Math.max(...ally) - Math.min(...ally) + 2 * mrg}`

  // Coloured edge frame for rhombus connection boards (which sides each seat connects).
  let edgeLines = null
  if (isHex && board.edges && board.shape === 'rhombus') {
    const W = board.width - 1, H = board.height - 1, off = R * 0.95
    const cnr = (c, r) => [px(SQRT3 * (c + r / 2)), px(1.5 * r)]
    const [tl, tr, bl, br] = [cnr(0, 0), cnr(W, 0), cnr(0, H), cnr(W, H)]
    const seg = (a, b, dx, dy, owner) => ({
      x1: a[0] + dx, y1: a[1] + dy, x2: b[0] + dx, y2: b[1] + dy, c: SEAT_FILL[owner],
    })
    const e = board.edges
    edgeLines = [
      seg(tl, tr, 0, -off, e.top), seg(bl, br, 0, off, e.bottom),
      seg(tl, bl, -off, 0, e.left), seg(tr, br, off, 0, e.right),
    ].map((s, i) => (
      <line key={`edge${i}`} x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2}
        stroke={s.c} strokeWidth={R * 0.5} strokeLinecap="round" opacity="0.9" />
    ))
  }

  return (
    <div className="board-wrap">
      <svg viewBox={vb} style={{ width: '100%', maxWidth: 540, height: 'auto', touchAction: 'manipulation' }}>
        {edgeLines}
        {shapes.map((s) => {
          const piece = pieces[s.id]
          const selected = selSet.has(s.id)
          const isTarget = !firstStep && nextCells.has(s.id) && !disabled && !selected
          const isSource = sources.has(s.id) && !disabled && !selected && !isTarget
          const clickable = selected || isTarget || isSource
          const isGoal = hl[s.id] === 'goal'
          const baseFill = s.parity ? '#332e27' : '#2a2620'
          const fill = selected ? '#6b5520' : isTarget ? '#2f4030'
            : hl[s.id] === 'last-move' ? '#3a3228' : baseFill
          const stroke = selected ? '#e7c87a' : isTarget ? '#5cba6b'
            : isGoal ? '#c9a96e' : isSource && piece ? '#7a6a3a' : '#4a4238'
          const sw = (selected || isTarget || isGoal ? 0.14 : 0.07) * s.r
          return (
            <g key={s.id} onClick={clickable ? () => click(s.id) : undefined} style={{ cursor: clickable ? 'pointer' : 'default' }}>
              <polygon points={s.poly} fill={fill} stroke={stroke} strokeWidth={sw} />
              {isTarget && piece && <circle cx={s.cx} cy={s.cy} r={s.r * 0.9} fill="none" stroke="#5cba6b" strokeWidth={s.r * 0.1} />}
              {piece && (piece.label
                ? <text x={s.cx} y={s.cy} textAnchor="middle" dominantBaseline="central" fontSize={s.r * 1.0} fontWeight="bold" fill={colors(piece.owner).fill}>{piece.label}</text>
                : <circle cx={s.cx} cy={s.cy} r={s.r * 0.6} fill={colors(piece.owner).fill} stroke={colors(piece.owner).stroke} strokeWidth={s.r * 0.07} />)}
              {isTarget && !piece && <circle cx={s.cx} cy={s.cy} r={s.r * 0.3} fill="#5cba6b" opacity="0.85" />}
              {isSource && !piece && <circle cx={s.cx} cy={s.cy} r={s.r * 0.18} fill="#c9a96e" opacity="0.7" />}
            </g>
          )
        })}
      </svg>

      {!disabled && actions.length > 0 && (
        <div className="actions-bar">
          {actions.map((a) => (
            <button key={a} className="action-btn" onClick={() => onMove(a)}>
              {ACTION_LABELS[a] || a}
            </button>
          ))}
        </div>
      )}

      {promo && (
        <div className="promo-picker">
          <div className="promo-title">{promo.options.every((o) => PIECE_NAMES[o.choice]) ? 'Promote to' : 'Choose'}</div>
          <div className="promo-options">
            {promo.options.map((o) => (
              <button key={o.choice} onClick={() => { onMove(o.move); setPromo(null); setSel([]) }}>
                {CHOICE_NAMES[o.choice] || o.choice}
              </button>
            ))}
            <button className="promo-cancel" onClick={() => { setPromo(null); setSel([]) }}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  )
}
