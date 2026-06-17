// Generic renderer: draws ANY game from its RenderSpec. It understands board
// geometries (square, hex), not games. A cell is clickable when its id is in
// `legalMoves` (works for placement-style games where a move == a cell id).

const OWNER_FILL = ['#d23b3b', '#3b6fd2'] // player 0 red, player 1 blue
const OWNER_STROKE = ['#7a1414', '#173a7a']

function pieceColors(owner) {
  return {
    fill: OWNER_FILL[owner] ?? '#888',
    stroke: OWNER_STROKE[owner] ?? '#444',
  }
}

// ---- geometry ------------------------------------------------------------
function squareCells(board) {
  const cells = []
  for (let r = 0; r < board.height; r++)
    for (let c = 0; c < board.width; c++)
      cells.push({ id: `${c},${r}`, x: c, y: r })
  return { cells, cell: 1 }
}

const SQRT3 = Math.sqrt(3)
function hexCells(board) {
  const size = board.size
  const cells = []
  for (let q = -(size - 1); q <= size - 1; q++)
    for (let r = -(size - 1); r <= size - 1; r++)
      if (Math.abs(q + r) <= size - 1) {
        cells.push({
          id: `${q},${r}`,
          x: SQRT3 * q + (SQRT3 / 2) * r,
          y: 1.5 * r,
        })
      }
  return { cells, cell: 1 }
}

function hexPolygon(cx, cy, s) {
  const pts = []
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 180) * (60 * i - 30)
    pts.push(`${cx + s * Math.cos(a)},${cy + s * Math.sin(a)}`)
  }
  return pts.join(' ')
}

// ---- component -----------------------------------------------------------
export default function Board({ spec, legalMoves, onCellClick, disabled }) {
  if (!spec) return null
  const board = spec.board
  const legal = new Set(legalMoves || [])
  const pieces = {}
  for (const p of spec.pieces || []) pieces[p.cell] = p
  const highlights = {}
  for (const h of spec.highlights || []) highlights[h.cell] = h.kind

  const isHex = board.type === 'hex'
  const { cells } = isHex ? hexCells(board) : squareCells(board)

  // Scale to a comfortable pixel size and compute the viewBox from extents.
  const R = 30 // cell radius in px
  const px = (v) => v * (isHex ? R : R * 2.2)
  const xs = cells.map((c) => px(c.x))
  const ys = cells.map((c) => px(c.y))
  const m = R * 1.6
  const minX = Math.min(...xs) - m
  const minY = Math.min(...ys) - m
  const w = Math.max(...xs) - Math.min(...xs) + 2 * m
  const h = Math.max(...ys) - Math.min(...ys) + 2 * m

  return (
    <svg
      viewBox={`${minX} ${minY} ${w} ${h}`}
      style={{ width: '100%', maxWidth: 520, height: 'auto', touchAction: 'manipulation' }}
    >
      {cells.map((c) => {
        const cx = px(c.x)
        const cy = px(c.y)
        const piece = pieces[c.id]
        const isLegal = legal.has(c.id) && !disabled
        const hl = highlights[c.id]
        const clickable = isLegal

        return (
          <g
            key={c.id}
            onClick={clickable ? () => onCellClick(c.id) : undefined}
            style={{ cursor: clickable ? 'pointer' : 'default' }}
          >
            {isHex ? (
              <polygon
                points={hexPolygon(cx, cy, R)}
                fill={hl === 'last-move' ? '#3a3228' : '#2a2620'}
                stroke="#4a4238"
                strokeWidth="1.5"
              />
            ) : (
              <rect
                x={cx - R}
                y={cy - R}
                width={2 * R}
                height={2 * R}
                fill={hl === 'last-move' ? '#3a3228' : '#2a2620'}
                stroke="#4a4238"
                strokeWidth="1.5"
              />
            )}

            {piece &&
              (piece.label ? (
                <text
                  x={cx}
                  y={cy}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={R * 1.1}
                  fontWeight="bold"
                  fill={pieceColors(piece.owner).fill}
                >
                  {piece.label}
                </text>
              ) : (
                <circle
                  cx={cx}
                  cy={cy}
                  r={R * 0.66}
                  fill={pieceColors(piece.owner).fill}
                  stroke={pieceColors(piece.owner).stroke}
                  strokeWidth="2"
                />
              ))}

            {isLegal && !piece && (
              <circle cx={cx} cy={cy} r={R * 0.16} fill="#c9a96e" opacity="0.7" />
            )}
          </g>
        )
      })}
    </svg>
  )
}
