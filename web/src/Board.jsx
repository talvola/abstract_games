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

// "2,4>2,5=Q" -> { cells: ["2,4","2,5"], choice: "Q" }
function parseMove(m) {
  const eq = m.indexOf('=')
  const pathPart = eq >= 0 ? m.slice(0, eq) : m
  return { cells: pathPart.split('>'), choice: eq >= 0 ? m.slice(eq + 1) : null }
}
const sameCells = (a, b) => a.length === b.length && a.every((c, i) => c === b[i])

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
  const moves = (legalMoves || []).map((m) => ({ raw: m, ...parseMove(m) }))
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
  const cells = isHex ? hexCells(board) : squareCells(board)
  const pieces = {}
  for (const p of spec.pieces || []) pieces[p.cell] = p
  const hl = {}
  for (const h of spec.highlights || []) hl[h.cell] = h.kind

  const R = 30
  const px = (v) => v * (isHex ? R : R * 2.2)
  const xs = cells.map((c) => px(c.x)), ys = cells.map((c) => px(c.y))
  const m = R * 1.9
  const vb = `${Math.min(...xs) - m} ${Math.min(...ys) - m} ${Math.max(...xs) - Math.min(...xs) + 2 * m} ${Math.max(...ys) - Math.min(...ys) + 2 * m}`

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
        {cells.map((c) => {
          const cx = px(c.x), cy = px(c.y)
          const piece = pieces[c.id]
          const selected = selSet.has(c.id)
          const isTarget = !firstStep && nextCells.has(c.id) && !disabled && !selected
          const isSource = sources.has(c.id) && !disabled && !selected && !isTarget
          const clickable = selected || isTarget || isSource

          const baseFill = isHex ? '#2a2620' : (c.x + c.y) % 2 === 0 ? '#2a2620' : '#332e27'
          const fill = selected ? '#6b5520' : isTarget ? '#2f4030'
            : hl[c.id] === 'last-move' ? '#3a3228' : baseFill
          const stroke = selected ? '#e7c87a' : isTarget ? '#5cba6b'
            : isSource && piece ? '#7a6a3a' : '#4a4238'
          return (
            <g key={c.id} onClick={clickable ? () => click(c.id) : undefined} style={{ cursor: clickable ? 'pointer' : 'default' }}>
              {isHex
                ? <polygon points={hexPoly(cx, cy, R)} fill={fill} stroke={stroke} strokeWidth={selected || isTarget ? 2.5 : 1.5} />
                : <rect x={cx - R} y={cy - R} width={2 * R} height={2 * R} fill={fill} stroke={stroke} strokeWidth={selected || isTarget ? 2.5 : 1.5} />}
              {isTarget && piece && <circle cx={cx} cy={cy} r={R * 0.9} fill="none" stroke="#5cba6b" strokeWidth="3" />}
              {piece && (piece.label
                ? <text x={cx} y={cy} textAnchor="middle" dominantBaseline="central" fontSize={R * 1.1} fontWeight="bold" fill={colors(piece.owner).fill}>{piece.label}</text>
                : <circle cx={cx} cy={cy} r={R * 0.66} fill={colors(piece.owner).fill} stroke={colors(piece.owner).stroke} strokeWidth="2" />)}
              {isTarget && !piece && <circle cx={cx} cy={cy} r={R * 0.3} fill="#5cba6b" opacity="0.85" />}
              {isSource && !piece && <circle cx={cx} cy={cy} r={R * 0.18} fill="#c9a96e" opacity="0.7" />}
            </g>
          )
        })}
      </svg>

      {promo && (
        <div className="promo-picker">
          <div className="promo-title">Promote to</div>
          <div className="promo-options">
            {promo.options.map((o) => (
              <button key={o.choice} onClick={() => { onMove(o.move); setPromo(null); setSel([]) }}>
                {PIECE_NAMES[o.choice] || o.choice}
              </button>
            ))}
            <button className="promo-cancel" onClick={() => { setPromo(null); setSel([]) }}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  )
}
