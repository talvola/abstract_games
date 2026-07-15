import { useEffect, useState } from 'react'
import { SEAT_FILL, SEAT_STROKE } from './colors'
import { pieceImageHref } from './pieceImages'

// Generic renderer + move input. Draws ANY game from its RenderSpec and derives
// interaction from the legal-move list. A move is a ">"-separated PATH of cell
// ids (cells use "," so they never clash with ">"), optionally followed by a
// "=CHOICE" suffix for a move that needs a pick (e.g. pawn promotion "2,4>2,5=Q").
//   * placement games -> single-cell moves -> one click.
//   * from-to games    -> "from>to"        -> click source, then target.
//   * choice moves     -> a picker appears when a destination has >1 option.

const colors = (o) => ({ fill: SEAT_FILL[o] ?? '#aaa', stroke: SEAT_STROKE[o] ?? '#555' })
const PIECE_NAMES = { Q: 'Queen', R: 'Rook', N: 'Knight', B: 'Bishop', K: 'King', P: 'Pawn' }
// Real piece glyphs per `spec.pieceset` (opt-in, set by the engine). The chess
// family maps its standard letters to solid Unicode chess silhouettes so they
// render as actual pieces (filled in the seat colour) instead of the bare letter.
// Any letter not in the set (fairy pieces A/C/M/…) falls back to the letter, so
// variants stay correct. Other families can add their own set later.
const PIECE_GLYPHS = {
  chess: { K: '♚', Q: '♛', R: '♜', B: '♝', N: '♞', P: '♟' },
}
const glyphFor = (spec, label) => (label && PIECE_GLYPHS[spec.pieceset]?.[label]) || null
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
// A drop move places a reserved piece: "K@c,r" — the reserve key K is a single
// letter (Crazyhouse piece, e.g. "N@4,3") OR digit (a Gobblet cup size, "4@0,0").
// Handled via the reserve tray, so it is neither a cell path nor an action button.
const DROP_RE = /^([A-Za-z0-9])@(-?\d+,-?\d+)$/
const isDropMove = (m) => DROP_RE.test(m)
// A placement move lays a multi-cell POLYOMINO tile: "KEY:o@c,r" — KEY names the
// tile in `spec.palette`, `o` indexes that tile's orientation list, and "c,r" is
// the ANCHOR cell (the tile covers the anchor plus that orientation's offsets).
// Driven by the palette tray, so it is neither a cell path nor an action button.
// Distinct from DROP_RE (single-cell, no ":o"), which is left untouched.
const PLACE_RE = /^([A-Za-z0-9_]+):(\d+)@(-?\d+,-?\d+)$/
const isPlaceMove = (m) => PLACE_RE.test(m)
// A wall move places a wall in a groove: "Hc,r" / "Vc,r" (Quoridor). Handled by
// clickable slots between the cells, not as a cell path or an action button.
const WALL_RE = /^([HV])(\d+),(\d+)$/
const isWallMove = (m) => WALL_RE.test(m)
// A card move selects/passes a movement card (Onitama): "use:Tiger" / "pass:Tiger".
// Driven by the card strip, not an action button.
const isCardMove = (m) => m.startsWith('use:') || m.startsWith('pass:')
// Non-cell legal moves render as action buttons (e.g. pie-rule "swap", "pass").
const ACTION_LABELS = {
  swap: 'Swap (pie rule)', pass: 'Pass', end: 'End turn', resign: 'Resign', cancel: 'Deselect card',
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
  const [place, setPlace] = useState(null) // armed polyomino {key, orient} (for a placement)
  const [hover, setHover] = useState(null) // cell being hovered (for move preview)
  useEffect(() => { setSel([]); setPromo(null); setDrop(null); setPlace(null) },
    [JSON.stringify(legalMoves), disabled, freeform])

  if (!spec) return null
  const board = spec.board
  // A game may override the "=choice" suffix labels/title (e.g. Tak's F/S/C =
  // Flat/Wall/Capstone, which otherwise collide with chess promotion letters).
  const choiceNames = { ...CHOICE_NAMES, ...(spec.choiceNames || {}) }
  // The set of real board cell ids. A move is a clickable cell path if every
  // ">"-segment is one of these ids — works for numeric "c,r"/"q,r" boards AND
  // for irregular `polygons` boards with LABELLED ids ("c", "f,0,1,1" for Poly-Y,
  // "0".."6" for Tsoro), so those are click-to-place instead of action buttons.
  // Numeric-id games are unaffected (their ids are cells), and non-cell moves
  // (swap/pass/grow/drops/walls/cards — never cell ids) still route correctly.
  const cellIds = new Set(
    (board.type === 'polygons' ? (board.cells || []).map((c) => c.id)
      : (board.type === 'hex' ? hexCells(board) : squareCells(board)).map((c) => c.id)))
  const isCellPath = (m) => m.split('>').every((seg) => cellIds.has(seg.split('=')[0]))
  const cellMoves = (legalMoves || []).filter(isCellPath)
  const dropMoves = (legalMoves || []).filter(isDropMove)
  const wallMoves = (legalMoves || []).filter(isWallMove)
  const placeMoves = (legalMoves || []).filter(isPlaceMove)
  const actions = (legalMoves || []).filter((m) => !isCellPath(m) && !isDropMove(m) && !isWallMove(m)
    && !isCardMove(m) && !isPlaceMove(m))
  const moves = cellMoves.map((m) => ({ raw: m, ...parseMove(m) }))
  const paths = moves.map((m) => m.cells)

  // Cells the currently-selected reserve piece may be dropped on.
  const dropTargets = new Set()
  if (drop) for (const m of dropMoves) { const x = m.match(DROP_RE); if (x[1] === drop) dropTargets.add(x[2]) }

  // --- Polyomino palette (spec.palette) -------------------------------------
  // Which (key, orientation) pairs actually have a legal placement, and where.
  // anchorsFor["KEY:o"] = Set of legal anchor cell ids. Derived from legal_moves
  // alone, so the engine stays the single source of truth (as with drops).
  const anchorsFor = {}
  for (const m of placeMoves) {
    const x = m.match(PLACE_RE)
    const k = `${x[1]}:${x[2]}`
    ;(anchorsFor[k] || (anchorsFor[k] = new Set())).add(x[3])
  }
  // A game with a SHARED pool (Golomb's Pentominoes: both players draw from the
  // same 12 tiles) emits `palette.shared` instead of per-seat lists. It must be
  // explicit — two separate-but-identical hands (Blokus Duo at move 1) are
  // byte-identical, so auto-detecting a shared pool by comparing lists would
  // silently merge two real hands into one.
  const paletteTiles = (seat) => (spec.palette
    ? (spec.palette.shared || spec.palette[String(seat)] || []) : [])
  const paletteFor = (key) => paletteTiles(currentPlayer).find((t) => t.key === key)
  // Orientation indices of `key` that have at least one legal placement.
  const legalOrients = (key) => {
    const tile = paletteFor(key)
    if (!tile) return []
    return (tile.orients || []).map((_, i) => i).filter((i) => anchorsFor[`${key}:${i}`])
  }
  const placeTargets = place ? (anchorsFor[`${place.key}:${place.orient}`] || new Set()) : new Set()
  // The cells the armed tile would cover if dropped on the hovered anchor.
  const placeGhost = new Set()
  if (place && hover && placeTargets.has(hover)) {
    const tile = paletteFor(place.key)
    const offs = tile && tile.orients ? tile.orients[place.orient] || [] : []
    const [hc, hr] = hover.split(',').map(Number)
    for (const [dc, dr] of offs) placeGhost.add(`${hc + dc},${hr + dr}`)
  }

  const nextCells = new Set()
  for (const p of paths) if (p.length > sel.length && eqPrefix(p, sel)) nextCells.add(p[sel.length])
  const selSet = new Set(sel)
  const sources = new Set(paths.map((p) => p[0]))
  const firstStep = sel.length === 0

  // Move preview (e.g. Abalone group moves): when hovering a destination that
  // completes a move, ghost ALL the cells the mover's pieces land on — so a
  // group move reads as the whole set shifting, not just one encoded cell.
  // Driven by spec.moveTargets {moveString: [cellId,…]} (opt-in per game).
  const previewCells = (() => {
    if (disabled || !hover || !spec.moveTargets) return null
    const m = moves.find((mm) => sameCells(mm.cells, [...sel, hover]))
    return m ? spec.moveTargets[m.raw] : null
  })()
  const previewSet = new Set(previewCells || [])

  function click(cellId) {
    if (disabled || promo) return
    if (freeform) {                                  // honor-system: any piece -> any square
      if (sel.length === 0) { if (pieces[cellId]) setSel([cellId]); return }
      if (sel[0] === cellId) { setSel([]); return }  // click source again to cancel
      onMove(`${sel[0]}>${cellId}`); setSel([])
      return
    }
    if (place) {                                     // a palette tile is armed
      if (placeTargets.has(cellId)) {
        onMove(`${place.key}:${place.orient}@${cellId}`); setPlace(null); setSel([]); return
      }
      setPlace(null)                                 // clicked off-target: cancel, fall through
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
      // hw/hh = bounding half-extents (the cell's edge distance from centre), used
      // by the tile/track edge-glyphs so notch/edge-midpoints sit on the cell border.
      const hw = Math.max(...pts.map((p) => Math.abs(p[0] - cx)))
      const hh = Math.max(...pts.map((p) => Math.abs(p[1] - cy)))
      return { id: c.id, cx, cy, poly: pts.map((p) => p.join(',')).join(' '), r: rad * 0.6, hw, hh, parity }
    })
  } else {
    const cells = isHex ? hexCells(board) : squareCells(board)
    px = (v) => v * (isHex ? R : R * 2.2)
    shapes = cells.map((c) => {
      const cx = px(c.x), cy = px(c.y)
      const poly = isHex ? hexPoly(cx, cy, R)
        : `${cx - R},${cy - R} ${cx + R},${cy - R} ${cx + R},${cy + R} ${cx - R},${cy + R}`
      return { id: c.id, cx, cy, poly, r: R, hw: R, hh: R, parity: (c.x + c.y) % 2 }
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
  const levels = board.levels || {}                // {cellId: int 1..4} per-cell build height (Santorini)
  const tiles = board.tiles || {}                  // {cellId: [[a,b]×4]} Tsuro path-tiles (notch pairs 0..7)
  const tracks = board.tracks || {}                // {cellId: [[a,b,colour]]} Trax colour-track tiles (edge-mids 0..3)
  const tokens = board.tokens || []                // [{cell, notch, owner}] markers on tile edge-notches
  const shapeById = {}
  for (const s of shapes) shapeById[s.id] = s
  // The 8 edge-notches of a square tile cell (Tsuro), at the third-points of each
  // side, numbered clockwise from the top-left: 0,1 top; 2,3 right; 4,5 bottom;
  // 6,7 left. Returns the pixel [x,y] of notch i on cell shape s.
  function notchPos(s, i) {
    const cx = s.cx, cy = s.cy, hw = s.hw || s.r, hh = s.hh || s.r, tx = hw / 3, ty = hh / 3
    return [[cx - tx, cy - hh], [cx + tx, cy - hh], [cx + hw, cy - ty], [cx + hw, cy + ty],
      [cx + tx, cy + hh], [cx - tx, cy + hh], [cx - hw, cy + ty], [cx - hw, cy - ty]][i]
  }
  const cellR = shapes.length ? shapes[0].r : R
  // A cosmetic segment is a list of [x,y] points in board-coord space, with an
  // optional trailing colour string. 2 points → straight line; 3 points → the
  // middle point is a quadratic-Bézier control (smooth arcs, e.g. Surakarta's
  // corner loops); more → an open polyline. Pixel points are collected in
  // `decorPx` so the viewBox can grow to include decorations that bulge past the
  // cells (loop arcs, edge tracks). Returns an SVG element + records its extent.
  const decorPx = []
  function decorPath(seg, key, stroke, width) {
    const color = typeof seg[seg.length - 1] === 'string' ? seg[seg.length - 1] : null
    const pts = (color ? seg.slice(0, -1) : seg).map(([x, y]) => toPx(x, y))
    pts.forEach((p) => decorPx.push(p))
    const s = color || stroke
    let d
    if (pts.length === 2) d = `M ${pts[0][0]},${pts[0][1]} L ${pts[1][0]},${pts[1][1]}`
    else if (pts.length === 3) d = `M ${pts[0][0]},${pts[0][1]} Q ${pts[1][0]},${pts[1][1]} ${pts[2][0]},${pts[2][1]}`
    else d = `M ${pts.map((p) => `${p[0]},${p[1]}`).join(' L ')}`
    return <path key={key} d={d} fill="none" stroke={s} strokeWidth={width} strokeLinecap="round" />
  }
  // Cosmetic connecting lines (alquerque/Morris/board diagrams); drawn under cells.
  const boardLines = (board.lines || []).map((seg, i) =>
    decorPath(seg, `bl${i}`, '#6b6052', cellR * 0.09))
  // Overlay lines/arcs drawn OVER the cells (TwixT bridges, Surakarta loops).
  const overlayLines = (board.overlay || []).map((seg, i) =>
    decorPath(seg, `ov${i}`, '#c9a96e', cellR * 0.16))

  // Walls (Quoridor): two-cell segments in the grooves between cells. Placed
  // walls (spec.board.walls) draw solid; legal placements draw as faint clickable
  // "ghost" slots that brighten on hover. Square boards only.
  let wallEls = null
  if (!isHex && !isPoly && (board.walls || wallMoves.length)) {
    const H = board.height
    const seg = (kind, c, r) => kind === 'H'
      ? { x1: px(c) - R, y1: px(H - 1 - r) - R, x2: px(c + 1) + R, y2: px(H - 1 - r) - R }
      : { x1: px(c) + R, y1: px(H - 1 - r) + R, x2: px(c) + R, y2: px(H - 2 - r) - R }
    const placed = []
    const w = board.walls || { h: [], v: [] }
    ;(w.h || []).forEach(([c, r], i) => placed.push(<line key={`wh${i}`} {...seg('H', c, r)}
      stroke="#c9a96e" strokeWidth={R * 0.3} strokeLinecap="round" />))
    ;(w.v || []).forEach(([c, r], i) => placed.push(<line key={`wv${i}`} {...seg('V', c, r)}
      stroke="#c9a96e" strokeWidth={R * 0.3} strokeLinecap="round" />))
    const ghosts = (disabled ? [] : wallMoves).map((m) => {
      const x = m.match(WALL_RE)
      return <line key={`wg${m}`} className="wall-ghost" {...seg(x[1], +x[2], +x[3])}
        strokeWidth={R * 0.3} strokeLinecap="round" onClick={() => onMove(m)} />
    })
    wallEls = <g>{ghosts}{placed}</g>
  }

  const allx = [], ally = []
  shapes.forEach((s) => s.poly.split(' ').forEach((p) => {
    const [x, y] = p.split(',').map(Number); allx.push(x); ally.push(y)
  }))
  // Include cosmetic decorations (loop arcs, edge tracks) so they aren't clipped.
  decorPx.forEach(([x, y]) => { allx.push(x); ally.push(y) })
  // Margin proportional to the board extent (not an absolute pixel pad) so it
  // works for both pixel-space boards and small-coordinate polygon boards (Morris).
  const spanX = Math.max(...allx) - Math.min(...allx)
  const spanY = Math.max(...ally) - Math.min(...ally)
  const mrg = Math.max(spanX, spanY) * 0.04 + cellR * 0.5
  // `board.extent: [minX, minY, w, h]` fixes the viewBox to the FULL original
  // board so it doesn't rescale/recentre as cells vanish (ZÈRTZ's shrinking
  // board — removed rings just leave a gap). Default: fit the current cells.
  const vb = board.extent
    ? board.extent.join(' ')
    : `${Math.min(...allx) - mrg} ${Math.min(...ally) - mrg} ${spanX + 2 * mrg} ${spanY + 2 * mrg}`

  // Coloured edge frame for connection boards (which sides each seat connects).
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
  } else if (board.edges && !isHex && !isPoly) {
    // Square connection boards (Crossway, Gonnect): draw a coloured border on
    // each goal side. `off=R` keeps the frame within the viewBox margin for all
    // offered sizes. top/bottom map to the top/bottom screen edges (min/max y).
    const xs = shapes.map((s) => s.cx), ys = shapes.map((s) => s.cy)
    const minX = Math.min(...xs), maxX = Math.max(...xs)
    const minY = Math.min(...ys), maxY = Math.max(...ys)
    const off = R, e = board.edges
    edgeLines = [
      [minX - R, minY - off, maxX + R, minY - off, e.top],
      [minX - R, maxY + off, maxX + R, maxY + off, e.bottom],
      [minX - off, minY - R, minX - off, maxY + R, e.left],
      [maxX + off, minY - R, maxX + off, maxY + R, e.right],
    ].filter((s) => s[4] != null).map((s, i) => (
      <line key={`edge${i}`} x1={s[0]} y1={s[1]} x2={s[2]} y2={s[3]}
        stroke={SEAT_FILL[s[4]]} strokeWidth={R * 0.5} strokeLinecap="round" opacity="0.9" />
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
            <span style={{ color: c.fill }}>{glyphFor(spec, letter) || letter}</span>
            {n > 1 && <span className="reserve-count">×{n}</span>}
          </button>
        ))}
      </div>
    )
  }

  // A polyomino tile drawn as a mini-grid of its cell offsets, for the palette
  // chips and the orientation strip. NOTE the y-flip: the board draws row 0 at
  // the BOTTOM (squareCells), so a thumbnail must plot +dr UPWARD or every tile
  // would read vertically mirrored against the board it is placed on.
  function tileThumb(offsets, col, size = 30) {
    const cs = offsets.map(([dc, dr]) => [dc, dr])
    const minC = Math.min(...cs.map((o) => o[0])), maxC = Math.max(...cs.map((o) => o[0]))
    const minR = Math.min(...cs.map((o) => o[1])), maxR = Math.max(...cs.map((o) => o[1]))
    const w = maxC - minC + 1, h = maxR - minR + 1
    const n = Math.max(w, h)
    return (
      <svg viewBox={`-0.1 -0.1 ${n + 0.2} ${n + 0.2}`} width={size} height={size}>
        {cs.map(([dc, dr], i) => (
          <rect key={i} x={dc - minC + (n - w) / 2} y={(maxR - dr) + (n - h) / 2}
            width="0.9" height="0.9" rx="0.12" fill={col} stroke="#2a2620" strokeWidth="0.06" />
        ))}
      </svg>
    )
  }

  // Off-board polyomino palette (spec.palette): the tiles a seat has left. Click
  // a tile to arm it; if it has several placeable orientations an orientation
  // strip appears — pick one, then click a highlighted anchor on the board.
  // Tiles with no legal placement anywhere are shown greyed-out (a Blokus player
  // wants to see the pieces they are stuck with).
  // One tray per seat, in seat order, BELOW the board. (Unlike the 2-seat
  // reserve trays this must also read for 4-player Blokus, where a top/bottom
  // split has nowhere to put seats 2 and 3.)
  function paletteTrays() {
    if (!spec.palette) return null
    if (spec.palette.shared) return [paletteTray('shared')]
    return Object.keys(spec.palette).map(Number).sort((a, b) => a - b)
      .map((seat) => paletteTray(seat))
  }

  function paletteTray(seat) {
    const pal = spec.palette
    if (!pal) return null
    const shared = seat === 'shared'
    const tiles = paletteTiles(seat)
    // A shared pool is always the live tray — whoever is to move draws from it,
    // so it takes the mover's colour rather than a fixed seat's.
    const active = !disabled && (shared || currentPlayer === seat)
    const c = colors(shared ? currentPlayer : seat)
    const label = shared ? 'Pool' : `P${seat + 1}`
    const where = active ? 'active' : ''
    if (tiles.length === 0) {
      return <div key={seat} className={`palette-tray ${where}`}>
        <span className="reserve-label">{label}</span>
        <span className="reserve-empty">no tiles left</span>
      </div>
    }
    const armed = place && active ? paletteFor(place.key) : null
    const armedOrients = armed ? legalOrients(place.key) : []
    return (
      <div key={seat} className={`palette-tray ${where}`}>
        <div className="palette-row">
          <span className="reserve-label">{label}</span>
          {tiles.map((t) => {
            const playable = active && legalOrients(t.key).length > 0
            const isArmed = !!place && place.key === t.key && active
            return (
              <button key={t.key} disabled={!playable} title={t.label || t.key}
                className={`palette-chip${playable ? ' active' : ''}${isArmed ? ' selected' : ''}`}
                onClick={playable ? () => {
                  if (isArmed) { setPlace(null); return }
                  const os = legalOrients(t.key)
                  setPlace({ key: t.key, orient: os[0] }); setDrop(null); setSel([]); setPromo(null)
                } : undefined}>
                {tileThumb(t.orients[0], playable ? c.fill : '#5a5248')}
                {t.count > 1 && <span className="reserve-count">×{t.count}</span>}
              </button>
            )
          })}
        </div>
        {armed && armedOrients.length > 1 && (
          <div className="palette-row orients">
            <span className="reserve-label">Turn</span>
            {armedOrients.map((oi) => (
              <button key={oi}
                className={`palette-chip active${place.orient === oi ? ' selected' : ''}`}
                onClick={() => setPlace({ key: place.key, orient: oi })}>
                {tileThumb(armed.orients[oi], c.fill, 26)}
              </button>
            ))}
          </div>
        )}
      </div>
    )
  }

  // Card games (Onitama): a strip of movement cards, each a 5×5 mini-grid of its
  // offsets (oriented toward its holder). Your selectable cards are clickable.
  function cardStrip() {
    const cards = board.cards
    if (!cards) return null
    const moveFor = (name) => (legalMoves || []).find((m) => m === `use:${name}` || m === `pass:${name}`)
    return (
      <div className="card-strip">
        {cards.map((card, i) => {
          const mv = moveFor(card.name)
          const clickable = card.selectable && mv && !disabled
          const col = card.owner == null ? '#9a8a6a' : colors(card.owner).fill
          // Tsuro hand tile: a card with `paths` (4 notch-pairs) is drawn as a
          // mini path-tile (the 4 arcs joining the 8 edge-notches) rather than the
          // Onitama move-grid. Lets a player preview their 3 hand tiles.
          if (card.paths) {
            const np = (n) => { const r = 0.5, c = 0.5, t = r / 3
              return [[c - t, c - r], [c + t, c - r], [c + r, c - t], [c + r, c + t],
                [c + t, c + r], [c - t, c + r], [c - r, c + t], [c - r, c - t]][n] }
            return (
              <div key={i} className="onicard" style={{ borderColor: col }}>
                <div className="onicard-name" style={{ color: col }}>{card.name}</div>
                <svg viewBox="-0.06 -0.06 1.12 1.12" width="44" height="44">
                  <rect x="0" y="0" width="1" height="1" fill="#2a2620" stroke="#4a4238" strokeWidth="0.03" />
                  {(card.paths || []).map((pr, j) => {
                    const a = np(pr[0]), b = np(pr[1])
                    const ctrl = [(a[0] + b[0] + 1) / 4, (a[1] + b[1] + 1) / 4]
                    return <path key={j} d={`M ${a[0]},${a[1]} Q ${ctrl[0]},${ctrl[1]} ${b[0]},${b[1]}`}
                      fill="none" stroke="#d8b878" strokeWidth="0.07" strokeLinecap="round" />
                  })}
                </svg>
                <div className="onicard-tag">{card.owner == null ? '' : `P${card.owner + 1}`}</div>
              </div>
            )
          }
          const offs = card.owner === 1 ? card.offsets.map(([a, b]) => [-a, -b]) : card.offsets
          return (
            <div key={i} className={`onicard${card.selected ? ' selected' : ''}${clickable ? ' clickable' : ''}`}
              style={{ borderColor: card.selected ? '#e7c87a' : col }}
              onClick={clickable ? () => onMove(mv) : undefined}>
              <div className="onicard-name" style={{ color: col }}>{card.name}</div>
              <svg viewBox="-0.1 -0.1 5.2 5.2" width="44" height="44">
                {Array.from({ length: 5 }).map((_, r) => Array.from({ length: 5 }).map((_, c) => {
                  const center = c === 2 && r === 2
                  const move = offs.some(([a, b]) => c === 2 + a && r === 2 - b)
                  return <rect key={`${c}-${r}`} x={c} y={r} width="0.88" height="0.88" rx="0.12"
                    fill={center ? '#c9a96e' : move ? col : '#2a2620'} stroke="#4a4238" strokeWidth="0.05" />
                }))}
              </svg>
              <div className="onicard-tag">{card.owner == null ? 'middle' : `P${card.owner + 1}`}</div>
            </div>
          )
        })}
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

  // Per-cell build height (Santorini): `board.levels[cellId]` = 1..4. Drawn as a
  // stack of concentric "wedding-cake" tiers (levels 1-3) under the worker piece,
  // a blue dome cap at level 4 (impassable, never holds a worker), plus a small
  // height badge so the exact level is unambiguous. Generic: any game can supply
  // board.levels to show a per-cell height. Drawn between the cell fill and the
  // piece so the worker stands on top of the building.
  function levelGlyph(s, level) {
    const tiers = Math.min(level, 3)
    const shades = ['#e9e3d4', '#d7cfba', '#c2b89e']
    const out = []
    for (let k = 0; k < tiers; k++) {
      const half = s.r * (0.84 - 0.21 * k)
      out.push(<rect key={`t${k}`} x={s.cx - half} y={s.cy - half} width={half * 2} height={half * 2}
        rx={s.r * 0.1} fill={shades[k]} stroke="#9a917c" strokeWidth={s.r * 0.05} />)
    }
    if (level >= 4) out.push(<circle key="dome" cx={s.cx} cy={s.cy} r={s.r * 0.34}
      fill="#3a7bd5" stroke="#1f4f8f" strokeWidth={s.r * 0.07} />)
    out.push(<text key="lvl" x={s.cx + s.r * 0.66} y={s.cy + s.r * 0.66} textAnchor="middle"
      dominantBaseline="central" fontSize={s.r * 0.42} fontWeight="bold" fill="#7a6f57">{level}</text>)
    return <g key="lvls">{out}</g>
  }

  // Tsuro path-tile (the 9th render primitive): board.tiles[cellId] = a list of 4
  // [a,b] notch-pairs; each draws a smooth path-arc connecting notch a to notch b
  // inside the cell (a quadratic Bézier with the control point pulled toward the
  // centre so the line curves). Drawn over the cell fill, under the tokens.
  function tileGlyph(s, paths) {
    return <g key="tile">{(paths || []).map((pair, i) => {
      const pa = notchPos(s, pair[0]), pb = notchPos(s, pair[1])
      const ctrl = [(pa[0] + pb[0] + 2 * s.cx) / 4, (pa[1] + pb[1] + 2 * s.cy) / 4]
      return <path key={i} d={`M ${pa[0]},${pa[1]} Q ${ctrl[0]},${ctrl[1]} ${pb[0]},${pb[1]}`}
        fill="none" stroke="#d8b878" strokeWidth={s.r * 0.13} strokeLinecap="round" />
    })}</g>
  }

  // Trax colour-track tile: board.tracks[cellId] = a list of [a, b, colour] segments
  // joining two of the cell's 4 EDGE-MIDPOINTS (0 top, 1 right, 2 bottom, 3 left)
  // in `colour`. Opposite mids → a straight track; adjacent → a corner curve
  // (quadratic Bézier through the cell centre). Drawn over the cell fill.
  function trackGlyph(s, segs) {
    const hw = s.hw || s.r, hh = s.hh || s.r
    const mid = (i) => [[s.cx, s.cy - hh], [s.cx + hw, s.cy], [s.cx, s.cy + hh], [s.cx - hw, s.cy]][i]
    return <g key="trax">{(segs || []).map((seg, i) => {
      const pa = mid(seg[0]), pb = mid(seg[1])
      return <path key={i} d={`M ${pa[0]},${pa[1]} Q ${s.cx},${s.cy} ${pb[0]},${pb[1]}`}
        fill="none" stroke={seg[2] || '#d8b878'} strokeWidth={s.r * 0.16} strokeLinecap="round" />
    })}</g>
  }

  // Directional prongs (Octi): piece.prongs = a list of directions 0..7 (0=N up,
  // clockwise) — each drawn as a short arrow radiating from the pod, so you can
  // read which way it can move/jump. Drawn over the piece disc.
  const PRONG_DIR = [[0, -1], [0.71, -0.71], [1, 0], [0.71, 0.71], [0, 1], [-0.71, 0.71], [-1, 0], [-0.71, -0.71]]
  function prongGlyph(s, piece) {
    const col = colors(piece.owner).stroke
    return <g key="prongs">{(piece.prongs || []).map((d, i) => {
      const [ux, uy] = PRONG_DIR[d % 8]
      const x1 = s.cx + ux * s.r * 0.5, y1 = s.cy + uy * s.r * 0.5
      const x2 = s.cx + ux * s.r * 1.05, y2 = s.cy + uy * s.r * 1.05
      return <g key={i}>
        <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={col} strokeWidth={s.r * 0.16} strokeLinecap="round" />
        <circle cx={x2} cy={y2} r={s.r * 0.12} fill={col} />
      </g>
    })}</g>
  }

  // Real piece glyph (chess family): a solid Unicode chess silhouette filled in
  // the seat colour with a contrasting outline (paint-order: stroke behind fill)
  // so it reads as an actual carved piece on the dark board. Sized to fill the
  // cell; the glyph box has built-in padding so fontSize runs a bit over s.r.
  function pieceGlyph(s, piece, glyph) {
    const c = colors(piece.owner)
    return (
      <text x={s.cx} y={s.cy + s.r * 0.04} textAnchor="middle" dominantBaseline="central"
        fontSize={s.r * 1.85} fill={c.fill} stroke={c.stroke} strokeWidth={s.r * 0.05}
        paintOrder="stroke" style={{ pointerEvents: 'none' }}>{glyph}</text>
    )
  }

  // A compound-piece icon (chancellor/archbishop): a real piece image (cburnett)
  // recoloured to the seat colour, so a fairy piece reads as a piece, not a letter.
  function pieceImage(s, piece, href) {
    const z = s.r * 2.1
    return <image href={href} x={s.cx - z / 2} y={s.cy - z / 2} width={z} height={z}
      style={{ pointerEvents: 'none' }} />
  }
  const iconHref = (piece) => piece.icon
    ? pieceImageHref(piece.icon, colors(piece.owner).fill, colors(piece.owner).stroke)
    : null

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
          const isPlaceTarget = !!place && placeTargets.has(s.id) && !disabled
          const isGhost = placeGhost.has(s.id)
          const isTarget = (!freeMode && !firstStep && nextCells.has(s.id) && !disabled && !selected)
            || isDropTarget || isPlaceTarget
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
            <g key={s.id} data-cell={s.id} onClick={clickable ? () => click(s.id) : undefined}
              onMouseEnter={isTarget ? () => setHover(s.id) : undefined}
              onMouseLeave={isTarget ? () => setHover((h) => (h === s.id ? null : h)) : undefined}
              style={{ cursor: clickable ? 'pointer' : 'default' }}>
              <polygon points={s.poly} fill={fill} stroke={stroke} strokeWidth={sw} />
              {/* Footprint of the armed polyomino at the hovered anchor: the whole
                  tile reads as one shape before you commit to it. */}
              {isGhost && <polygon points={s.poly} fill={colors(currentPlayer).fill} opacity="0.5"
                stroke={colors(currentPlayer).stroke} strokeWidth={sw} pointerEvents="none" />}
              {tiles[s.id] ? tileGlyph(s, tiles[s.id]) : null}
              {tracks[s.id] ? trackGlyph(s, tracks[s.id]) : null}
              {levels[s.id] ? levelGlyph(s, levels[s.id]) : null}
              {isTarget && piece && <circle cx={s.cx} cy={s.cy} r={s.r * 0.9} fill="none" stroke="#5cba6b" strokeWidth={s.r * 0.1} />}
              {piece && (piece.stack
                ? stackGlyph(s, piece)
                : piece.shape === 'ring'
                  // Hollow ring (YINSH/GIPF). `piece.inner` (a seat index) draws a
                  // marker sitting inside the ring; `piece.label` centres text.
                  ? <g>
                      <circle cx={s.cx} cy={s.cy} r={s.r * 0.8} fill="none"
                        stroke={colors(piece.owner).fill} strokeWidth={s.r * 0.2} />
                      {piece.inner != null && <circle cx={s.cx} cy={s.cy} r={s.r * 0.4}
                        fill={colors(piece.inner).fill} stroke={colors(piece.inner).stroke} strokeWidth={s.r * 0.06} />}
                      {piece.label && <text x={s.cx} y={s.cy} textAnchor="middle" dominantBaseline="central"
                        fontSize={s.r * 0.7} fontWeight="bold" fill={colors(piece.owner).fill}>{piece.label}</text>}
                    </g>
                  : piece.shape === 'marker'
                    // Small filled disc (YINSH marker, flippable two-sided stone).
                    ? <circle cx={s.cx} cy={s.cy} r={s.r * 0.46}
                        fill={colors(piece.owner).fill} stroke={colors(piece.owner).stroke} strokeWidth={s.r * 0.07} />
                    : piece.size != null
                      // Nested "gobble" piece (Gobblet): a disc scaled by its size,
                      // so a larger piece visibly covers (gobbles) smaller ones — only
                      // the top piece of a cell's nest is shown. A rim ring reads as a cup.
                      ? <g>
                          <circle cx={s.cx} cy={s.cy} r={Math.min(0.88, 0.34 + 0.135 * piece.size) * s.r}
                            fill={colors(piece.owner).fill} stroke={colors(piece.owner).stroke} strokeWidth={s.r * 0.07} />
                          <circle cx={s.cx} cy={s.cy} r={Math.min(0.88, 0.34 + 0.135 * piece.size) * s.r * 0.6}
                            fill="none" stroke={colors(piece.owner).stroke} strokeWidth={s.r * 0.05} opacity="0.5" />
                          {piece.label && <text x={s.cx} y={s.cy} textAnchor="middle" dominantBaseline="central"
                            fontSize={s.r * 0.6} fontWeight="bold" fill={colors(piece.owner).stroke}>{piece.label}</text>}
                        </g>
                      : (piece.fill && piece.label)
                        // A coloured disc WITH a label (e.g. Kamisado towers, whose
                        // fill matches their home cell's tint) — draw the disc so it
                        // reads as a piece, label in the contrasting stroke colour.
                        ? <g>
                            <circle cx={s.cx} cy={s.cy} r={s.r * 0.6}
                              fill={piece.fill} stroke={piece.stroke || '#111'} strokeWidth={s.r * 0.12} />
                            <text x={s.cx} y={s.cy} textAnchor="middle" dominantBaseline="central"
                              fontSize={s.r * 0.62} fontWeight="bold" fill={piece.stroke || '#111'}>{piece.label}</text>
                          </g>
                        : piece.glyph
                          ? pieceGlyph(s, piece, piece.glyph)
                        : iconHref(piece)
                          ? pieceImage(s, piece, iconHref(piece))
                        : glyphFor(spec, piece.label)
                          ? pieceGlyph(s, piece, glyphFor(spec, piece.label))
                        : piece.label
                          ? <text x={s.cx} y={s.cy} textAnchor="middle" dominantBaseline="central" fontSize={s.r * 1.0} fontWeight="bold" fill={colors(piece.owner).fill}>{piece.label}</text>
                          // `piece.fill`/`piece.stroke` override the seat colour — e.g. ZÈRTZ's
                          // neutral white/grey/black marbles, which aren't tied to a player.
                          : <circle cx={s.cx} cy={s.cy} r={s.r * 0.6}
                              fill={piece.fill || colors(piece.owner).fill}
                              stroke={piece.stroke || colors(piece.owner).stroke} strokeWidth={s.r * 0.07} />)}
              {piece && piece.prongs ? prongGlyph(s, piece) : null}
              {isTarget && !piece && <circle cx={s.cx} cy={s.cy} r={s.r * 0.3} fill="#5cba6b" opacity="0.85" />}
              {isSource && !piece && <circle cx={s.cx} cy={s.cy} r={s.r * 0.18} fill="#c9a96e" opacity="0.7" />}
            </g>
          )
        })}
        {overlayLines}
        {/* Ghost preview: where the mover's whole group lands for the hovered move. */}
        {previewCells && previewCells.map((cid) => {
          const s = shapeById[cid]
          if (!s) return null
          const c = colors(currentPlayer)
          return <circle key={`gh${cid}`} cx={s.cx} cy={s.cy} r={s.r * 0.6}
            fill={c.fill} stroke="#e7c87a" strokeWidth={s.r * 0.12}
            opacity="0.55" style={{ pointerEvents: 'none' }} />
        })}
        {wallEls}
        {tokens.map((tk, i) => {
          const s = shapeById[tk.cell]
          if (!s) return null
          const [x, y] = notchPos(s, tk.notch)
          return <circle key={`tok${i}`} cx={x} cy={y} r={s.r * 0.24}
            fill={colors(tk.owner).fill} stroke={colors(tk.owner).stroke} strokeWidth={s.r * 0.07} />
        })}
      </svg>
      {tray(0, 'bottom')}
      {paletteTrays()}
      {cardStrip()}

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
          <div className="promo-title">{spec.choiceTitle
            || (promo.options.some((o) => !spec.choiceNames && PROMO_LETTERS.has(o.choice)) ? 'Promote to' : 'Choose')}</div>
          <div className="promo-options">
            {promo.options.map((o) => (
              <button key={o.choice ?? 'none'} onClick={() => { onMove(o.move); setPromo(null); setSel([]) }}>
                {o.choice == null ? 'No promotion' : (choiceNames[o.choice] || o.choice)}
              </button>
            ))}
            <button className="promo-cancel" onClick={() => { setPromo(null); setSel([]) }}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  )
}
