import { useEffect, useState } from 'react'

// Generic renderer + move input. Draws ANY game from its RenderSpec and derives
// interaction from the legal-move list. A move is a ">"-separated PATH of cell
// ids (cell ids themselves use "," — e.g. "2,1>2,3"). So:
//   * placement games  -> single-cell moves -> one click.
//   * from-to games    -> "from>to" moves   -> click source, then target.
// The component tracks a selection prefix and only offers legal continuations.

const OWNER_FILL = ['#d23b3b', '#3b6fd2']
const OWNER_STROKE = ['#7a1414', '#173a7a']
const colors = (o) => ({ fill: OWNER_FILL[o] ?? '#aaa', stroke: OWNER_STROKE[o] ?? '#555' })

function squareCells(b) {
  const cells = []
  for (let r = 0; r < b.height; r++) for (let c = 0; c < b.width; c++) cells.push({ id: `${c},${r}`, x: c, y: r })
  return cells
}
const SQRT3 = Math.sqrt(3)
function hexCells(b) {
  const s = b.size, cells = []
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
  // Reset selection whenever the position/turn changes.
  useEffect(() => setSel([]), [JSON.stringify(legalMoves), disabled])

  if (!spec) return null
  const board = spec.board
  const paths = (legalMoves || []).map((m) => m.split('>'))

  // legal next cells given the current selection prefix
  const nextCells = new Set()
  for (const p of paths) if (p.length > sel.length && eqPrefix(p, sel)) nextCells.add(p[sel.length])
  const selSet = new Set(sel)
  const sources = new Set(paths.map((p) => p[0])) // cells a move can start from
  const firstStep = sel.length === 0

  function click(cellId) {
    if (disabled) return
    const cand = [...sel, cellId]
    const complete = paths.some((p) => p.length === cand.length && eqPrefix(p, cand))
    const extends_ = paths.some((p) => p.length > cand.length && eqPrefix(p, cand))
    if (complete) { onMove(cand.join('>')); setSel([]) }
    else if (extends_) setSel(cand)
    else if (sel.length && sources.has(cellId)) setSel([cellId]) // switch to another piece
    else setSel([])                                              // deselect
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
  const m = R * 1.6
  const vb = `${Math.min(...xs) - m} ${Math.min(...ys) - m} ${Math.max(...xs) - Math.min(...xs) + 2 * m} ${Math.max(...ys) - Math.min(...ys) + 2 * m}`

  return (
    <svg viewBox={vb} style={{ width: '100%', maxWidth: 540, height: 'auto', touchAction: 'manipulation' }}>
      {cells.map((c) => {
        const cx = px(c.x), cy = px(c.y)
        const piece = pieces[c.id]
        const selected = selSet.has(c.id)
        // destination of the currently-selected piece (green)
        const isTarget = !firstStep && nextCells.has(c.id) && !disabled && !selected
        // a move can START here (pick a piece, or place on an empty cell) — amber
        const isSource = sources.has(c.id) && !disabled && !selected && !isTarget
        const clickable = selected || isTarget || isSource

        const fill = selected ? '#6b5520'
          : isTarget ? '#2f4030'
          : hl[c.id] === 'last-move' ? '#3a3228' : '#2a2620'
        const stroke = selected ? '#e7c87a'
          : isTarget ? '#5cba6b'
          : isSource && piece ? '#7a6a3a'   // subtle: this piece is movable
          : '#4a4238'
        return (
          <g key={c.id} onClick={clickable ? () => click(c.id) : undefined} style={{ cursor: clickable ? 'pointer' : 'default' }}>
            {isHex
              ? <polygon points={hexPoly(cx, cy, R)} fill={fill} stroke={stroke} strokeWidth={selected || isTarget ? 2.5 : 1.5} />
              : <rect x={cx - R} y={cy - R} width={2 * R} height={2 * R} fill={fill} stroke={stroke} strokeWidth={selected || isTarget ? 2.5 : 1.5} />}

            {/* capture target: green ring around the enemy piece */}
            {isTarget && piece && <circle cx={cx} cy={cy} r={R * 0.9} fill="none" stroke="#5cba6b" strokeWidth="3" />}

            {piece && (piece.label
              ? <text x={cx} y={cy} textAnchor="middle" dominantBaseline="central" fontSize={R * 1.1} fontWeight="bold" fill={colors(piece.owner).fill}>{piece.label}</text>
              : <circle cx={cx} cy={cy} r={R * 0.66} fill={colors(piece.owner).fill} stroke={colors(piece.owner).stroke} strokeWidth="2" />)}

            {/* empty destination of selected piece: green dot */}
            {isTarget && !piece && <circle cx={cx} cy={cy} r={R * 0.3} fill="#5cba6b" opacity="0.85" />}
            {/* legal placement on an empty cell (no selection step): amber dot */}
            {isSource && !piece && <circle cx={cx} cy={cy} r={R * 0.18} fill="#c9a96e" opacity="0.7" />}
          </g>
        )
      })}
    </svg>
  )
}
