// Per-seat colours, shared by the board, move log, and player chips so a
// player's name and their pieces always match. Up to six seats are supported
// (e.g. four-player Rolit). Index 2 (green) also doubles as the "neutral / no
// owner" colour for non-player pieces — Amazons' arrows and Borderline's shared
// king both render with owner 2; green reads clearly as "owned by neither side".
export const SEAT_FILL = ['#d23b3b', '#3b6fd2', '#3aa84a', '#d6a02a', '#9a5bd2', '#2bb0a6']
export const SEAT_STROKE = ['#7a1414', '#173a7a', '#1c5a26', '#7a5a10', '#54307a', '#14605a']
