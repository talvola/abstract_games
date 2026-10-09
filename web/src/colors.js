// Per-seat colours, shared by the board, move log, and player chips so a
// player's name and their pieces always match. Up to six seats are supported
// (e.g. four-player Rolit). Index 2 (green) also doubles as the "neutral / no
// owner" colour for non-player pieces — Amazons' arrows and Borderline's shared
// king both render with owner 2; green reads clearly as "owned by neither side".
export const SEAT_FILL = ['#d23b3b', '#3b6fd2', '#3aa84a', '#d6a02a', '#9a5bd2', '#2bb0a6']
export const SEAT_STROKE = ['#7a1414', '#173a7a', '#1c5a26', '#7a5a10', '#54307a', '#14605a']

// Named palette a game can opt into with `render.seat_colors` (one name per
// seat, e.g. ["white", "black"] for chess) so a side called "White" is drawn
// white, not red. Absent ⇒ the seat-index colours above. The stroke is chosen to
// contrast with the fill on the dark board: "black" gets a light outline,
// otherwise a black disc / glyph would vanish into a dark square.
export const NAMED_COLORS = {
  white: { fill: '#f1ead9', stroke: '#3b3125' },
  black: { fill: '#16130f', stroke: '#c9b48a' },
  red: { fill: SEAT_FILL[0], stroke: SEAT_STROKE[0] },
  blue: { fill: SEAT_FILL[1], stroke: SEAT_STROKE[1] },
  yellow: { fill: '#e8c42a', stroke: '#7a6210' },
  gold: { fill: '#d4a93a', stroke: '#6e5212' },
  silver: { fill: '#b9bec6', stroke: '#4a4f57' },
}

// The {fill, stroke} for a seat, honouring a game's `render.seat_colors`.
export function seatColor(seat, seatColors) {
  const named = seatColors && NAMED_COLORS[seatColors[seat]]
  return named || { fill: SEAT_FILL[seat] ?? '#aaa', stroke: SEAT_STROKE[seat] ?? '#555' }
}

// Inline style for the small seat dot in player chips / move logs: the fill plus
// a ring in the stroke colour, so a black or white dot still reads on any panel.
export function seatDotStyle(seat, seatColors) {
  const c = seatColor(seat, seatColors)
  return { background: c.fill, boxShadow: `0 0 0 1px ${c.stroke}` }
}
