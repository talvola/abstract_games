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
const CHOICE_NAMES = { ...PIECE_NAMES, M: 'Marshall', C: 'Cardinal', red: 'Red', blue: 'Blue', '+': 'Promote' }
const PROMO_LETTERS = new Set(['Q', 'R', 'N', 'B', 'M', 'C', '+'])

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
// A drop move places a reserved piece: "L@c,r" (e.g. "N@4,3"). Handled via the
// reserve tray, so it is neither a cell path nor an action button.
const DROP_RE = /^([A-Za-z])@(-?\d+,-?\d+)$/
const isDropMove = (m) => DROP_RE.test(m)
// Non-cell legal moves render as action buttons (e.g. pie-rule "swap", "pass").
const ACTION_LABELS = {
  swap: 'Swap (pie rule)', pass: 'Pass', end: 'End turn', resign: 'Resign',
  'offer-draw': 'Offer draw', 'accept-draw': 'Accept draw', 'decline-draw': 'Decline draw',
}

function squareCells(b) {
  // Draw row 0 at the BOTTOM so the first player (whose pieces start on the low
  // rows) sits at the bottom, as is traditional for chess. Display only — cell
  // ids stay "col,row", so move generation and click-to-move are unaffected.
  const cells = []
  for (let r = 0; r < b.height; r++) for (let c = 0; c < b.width; c++) cells.push({ id: `${c},${r}`, x: c, y: b.height - 1 - r })
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

export default function Board({ spec, legalMoves, onMove, disabled, freeform, currentPlayer }) {
  const [sel, setSel] = useState([])
  const [promo, setPromo] = useState(null) // { cells, options: [{choice, move}] }
  const [drop, setDrop] = useState(null)   // selected reserve piece letter (for a drop)
  useEffect(() => { setSel([]); setPromo(null); setDrop(null) }, [JSON.stringify(legalMoves), disabled, freeform])

  if (!spec) return null
  const board = spec.board
  const cellMoves = (legalMoves || []).filter(isCellMove)
  const dropMoves = (legalMoves || []).filter(isDropMove)
  const actions = (legalMoves || []).filter((m) => !isCellMove(m) && !isDropMove(m))
  const moves = cellMoves.map((m) => ({ raw: m, ...parseMove(m) }))
  const paths = moves.map((m) => m.cells)

  // Cells the currently-selected reserve piece may be dropped on.
  const dropTargets = new Set()
  if (drop) for (const m of dropMoves) { const x = m.match(DROP_RE); if (x[1] === drop) dropTargets.add(x[2]) }

  const nextCells = new Set()
  for (const p of paths) if (p.length > sel.length && eqPrefix(p, sel)) nextCells.add(p[sel.length])
  const selSet = new Set(sel)
  const sources = new Set(paths.map((p) => p[0]))
  const firstStep = sel.length === 0

  function click(cellId) {
    if (disabled || promo) return
    if (freeform) {                                  // honor-system: any piece -> any square
      if (sel.length === 0) { if (pieces[cellId]) setSel([cellId]); return }
      if (sel[0] === cellId) { setSel([]); return }  // click source again to cancel
      onMove(`${sel[0]}>${cellId}`); setSel([])
      return
    }
    if (drop) {                                      // a reserve piece is armed
      if (dropTargets.has(cellId)) { onMove(`${drop}@${cellId}`); setDrop(null); setSel([]); return }
      setDrop(null)                                  // clicked off-target: cancel, fall through
    }
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

  // Map a point in the board's own coordinate space to pixels, the same way cell
  // centres are mapped — so optional cosmetic lines line up with the cells.
  const toPx = isPoly
    ? (x, y) => [x, y]
    : isHex
      ? (x, y) => [px(SQRT3 * (x + y / 2)), px(1.5 * y)]
      : (x, y) => [px(x), px(board.height - 1 - y)]
  const tints = board.tints || {}                  // {cellId: colour} terrain fills
  const cellR = shapes.length ? shapes[0].r : R
  // Cosmetic connecting lines (alquerque/Morris/board diagrams); drawn under cells.
  const boardLines = (board.lines || []).map((seg, i) => {
    const [x1, y1] = toPx(seg[0][0], seg[0][1])
    const [x2, y2] = toPx(seg[1][0], seg[1][1])
    return <line key={`bl${i}`} x1={x1} y1={y1} x2={x2} y2={y2}
      stroke={seg[2] || '#6b6052'} strokeWidth={cellR * 0.09} strokeLinecap="round" />
  })

  const allx = [], ally = []
  shapes.forEach((s) => s.poly.split(' ').forEach((p) => {
    const [x, y] = p.split(',').map(Number); allx.push(x); ally.push(y)
  }))
  // Margin proportional to the board extent (not an absolute pixel pad) so it
  // works for both pixel-space boards and small-coordinate polygon boards (Morris).
  const spanX = Math.max(...allx) - Math.min(...allx)
  const spanY = Math.max(...ally) - Math.min(...ally)
  const mrg = Math.max(spanX, spanY) * 0.04 + cellR * 0.5
  const vb = `${Math.min(...allx) - mrg} ${Math.min(...ally) - mrg} ${spanX + 2 * mrg} ${spanY + 2 * mrg}`

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

  // Off-board reserve trays (drop games, e.g. Crazyhouse). seat 1 above, seat 0
  // below — matching the board's orientation (seat 0 sits at the bottom). Only
  // the side to move may arm a drop.
  const reserve = spec.reserve
  function tray(seat, where) {
    if (!reserve) return null
    const hand = reserve[String(seat)] || {}
    const entries = Object.entries(hand).filter(([, n]) => n > 0)
    const active = !disabled && currentPlayer === seat
    const c = colors(seat)
    return (
      <div className={`reserve-tray ${where}`}>
        <span className="reserve-label">P{seat + 1}</span>
        {entries.length === 0 && <span className="reserve-empty">empty</span>}
        {entries.map(([letter, n]) => (
          <button key={letter} disabled={!active}
            className={`reserve-chip${active ? ' active' : ''}${drop === letter && active ? ' selected' : ''}`}
            onClick={active ? () => { setDrop(drop === letter ? null : letter); setSel([]); setPromo(null) } : undefined}>
            <span style={{ color: c.fill }}>{letter}</span>
            {n > 1 && <span className="reserve-count">×{n}</span>}
          </button>
        ))}
      </div>
    )
  }

  // Stacking games (e.g. Lasca): a piece carries `stack` = owners bottom→top.
  // Draw it as a side-view tower of owner-coloured bands, top band emphasised,
  // with a height badge and any top-piece label (e.g. "O" for an officer).
  function stackGlyph(s, piece) {
    const owners = piece.stack
    const n = owners.length
    const bh = s.r * 0.42
    let step = s.r * 0.52
    const maxTotal = s.r * 1.7
    if (n > 1 && bh + (n - 1) * step > maxTotal) step = (maxTotal - bh) / (n - 1)
    const total = bh + (n - 1) * step
    const w = s.r * 1.25
    const bottomY = s.cy + total / 2 - bh / 2
    const topY = bottomY - (n - 1) * step
    return (
      <g>
        {owners.map((o, i) => {
          const col = colors(o)
          const top = i === n - 1
          return <rect key={i} x={s.cx - w / 2} y={bottomY - i * step - bh / 2}
            width={w} height={bh} rx={bh * 0.35} fill={col.fill}
            stroke={top ? '#f0e4c0' : col.stroke} strokeWidth={top ? s.r * 0.09 : s.r * 0.05} />
        })}
        {piece.label && <text x={s.cx} y={topY} textAnchor="middle" dominantBaseline="central"
          fontSize={bh * 0.95} fontWeight="bold" fill="#1a1712">{piece.label}</text>}
        {n > 1 && <text x={s.cx + w / 2 + s.r * 0.22} y={topY} textAnchor="middle"
          dominantBaseline="central" fontSize={s.r * 0.5} fontWeight="bold" fill="#d8c89a">{n}</text>}
      </g>
    )
  }

  return (
    <div className="board-wrap">
      {tray(1, 'top')}
      <svg viewBox={vb} style={{ width: '100%', maxWidth: 540, height: 'auto', touchAction: 'manipulation' }}>
        {edgeLines}
        {boardLines}
        {shapes.map((s) => {
          const piece = pieces[s.id]
          const selected = selSet.has(s.id)
          const freeMode = freeform && !disabled
          // Enforced games decorate legal targets/sources; freeform keeps every
          // cell clickable but only highlights the selected source (no 64 dots).
          const isDropTarget = !!drop && dropTargets.has(s.id) && !disabled
          const isTarget = (!freeMode && !firstStep && nextCells.has(s.id) && !disabled && !selected) || isDropTarget
          const isSource = freeMode
            ? sel.length === 0 && !!piece
            : sources.has(s.id) && !disabled && !selected && !isTarget
          const freeTarget = freeMode && sel.length === 1 && !selected
          const clickable = selected || isTarget || isSource || freeTarget
          const isGoal = hl[s.id] === 'goal'
          const baseFill = tints[s.id] || (s.parity ? '#332e27' : '#2a2620')
          const fill = selected ? '#6b5520' : isTarget ? '#2f4030'
            : hl[s.id] === 'last-move' ? '#3a3228' : baseFill
          const stroke = selected ? '#e7c87a' : isTarget ? '#5cba6b'
            : isGoal ? '#c9a96e' : isSource && piece ? '#7a6a3a' : '#4a4238'
          const sw = (selected || isTarget || isGoal ? 0.14 : 0.07) * s.r
          return (
            <g key={s.id} data-cell={s.id} onClick={clickable ? () => click(s.id) : undefined} style={{ cursor: clickable ? 'pointer' : 'default' }}>
              <polygon points={s.poly} fill={fill} stroke={stroke} strokeWidth={sw} />
              {isTarget && piece && <circle cx={s.cx} cy={s.cy} r={s.r * 0.9} fill="none" stroke="#5cba6b" strokeWidth={s.r * 0.1} />}
              {piece && (piece.stack
                ? stackGlyph(s, piece)
                : piece.label
                  ? <text x={s.cx} y={s.cy} textAnchor="middle" dominantBaseline="central" fontSize={s.r * 1.0} fontWeight="bold" fill={colors(piece.owner).fill}>{piece.label}</text>
                  : <circle cx={s.cx} cy={s.cy} r={s.r * 0.6} fill={colors(piece.owner).fill} stroke={colors(piece.owner).stroke} strokeWidth={s.r * 0.07} />)}
              {isTarget && !piece && <circle cx={s.cx} cy={s.cy} r={s.r * 0.3} fill="#5cba6b" opacity="0.85" />}
              {isSource && !piece && <circle cx={s.cx} cy={s.cy} r={s.r * 0.18} fill="#c9a96e" opacity="0.7" />}
            </g>
          )
        })}
      </svg>
      {tray(0, 'bottom')}

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
          <div className="promo-title">{promo.options.some((o) => PROMO_LETTERS.has(o.choice)) ? 'Promote to' : 'Choose'}</div>
          <div className="promo-options">
            {promo.options.map((o) => (
              <button key={o.choice ?? 'none'} onClick={() => { onMove(o.move); setPromo(null); setSel([]) }}>
                {o.choice == null ? 'No promotion' : (CHOICE_NAMES[o.choice] || o.choice)}
              </button>
            ))}
            <button className="promo-cancel" onClick={() => { setPromo(null); setSel([]) }}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  )
}
