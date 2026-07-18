# Circular Chess

Circular Chess is the medieval **round** game — the Byzantine *shatranj
al-muddawara*, described as early as the 10th century — revived in its modern
form by **Dave Reynolds of Lincoln, England (1983)**. Reynolds founded the
**Circular Chess Society** and the game has been played for a **World
Championship in Lincoln since 1996**. It is a Recognized Chess Variant. These
rules follow the Reynolds / Lincoln (World Championship) ruleset.

## The board

The board is an **annulus**: **4 concentric rings** (files), each divided into
**16 sectors** (radial ranks), for **64 cells**. The centre is an unplayable
hole. It is topologically a **16 × 4 cylinder**:

- The **sector** axis (0–15) **wraps** — sector 15 is adjacent to sector 0, so
  you can move all the way round a ring.
- The **ring** axis (0 = innermost … 3 = outermost) is **bounded** — there is no
  wrap across the centre hole or off the outer edge.

Cells are named `sector,ring` (e.g. `0,0` is the inner cell of sector 0).

## Setup

The standard chess set is "folded" onto the ring: take a normal board, split it
down the middle, join the short ends and bend it round. Each army **straddles a
line**; the two lines lie on **opposite sides** of the board. King and Queen sit
on the **inner** ring adjacent across the seam, then Bishops, Knights and Rooks
outward; the pawns sit one sector further, toward the enemy.

| Sector | ring 0 (inner) | ring 1 | ring 2 | ring 3 (outer) |
|---|---|---|---|---|
| White 15 | Q | B | N | R |
| White 0  | K | B | N | R |
| White 1  | P | P | P | P |
| White 14 | P | P | P | P |
| Black 7  | Q | B | N | R |
| Black 8  | K | B | N | R |
| Black 9  | P | P | P | P |
| Black 6  | P | P | P | P |

Sectors 2–5 and 10–13 start empty — the two battlefields where the armies clash.

## How the pieces move

All pieces move as in orthodox chess, adapted to the cylinder:

- **Rook** — slides around a ring (any number of sectors) **or** radially in/out
  across the rings.
- **Bishop** — slides diagonally (one sector and one ring per step).
- **Queen** — rook + bishop.
- **Knight** — the usual (1,2)/(2,1) leaps, with the sector taken modulo 16 and
  the ring kept on the board.
- **King** — one step to any of its (up to) 8 neighbours.

**Null-move ban.** A rook or queen may **not** run the whole way round a ring
back to the square it started on (such a "move" would not change the position).
A circular slide is therefore limited to 15 sectors — it always stops one sector
short of its own square.

## Pawns

Each pawn keeps a **fixed rotational direction** round the board and always
continues that way. An army's two pawn groups march in **opposite directions**,
both heading for the opponent's back pieces on the far seam:

- White pawns on sectors 1–7 travel in the **+sector** direction; those on 8–14
  travel **−sector**.
- Black pawns on sectors 9–15 travel **+sector**; those on 0–6 travel **−sector**.

Pawns capture one step diagonally in their direction of travel (to the adjacent
ring). From its **home** sector a pawn may advance **one or two** squares
(*double first step*; toggle with the **Pawn double first step** option). There
is **no en passant**.

**Promotion.** A pawn promotes on reaching the opponent's back-piece sectors —
six squares from home — to a **Queen, Rook, Bishop or Knight**. (White pawns
promote on sectors 7/8, Black pawns on sectors 15/0.)

## Other rules

- **No castling.**
- **Check, checkmate, stalemate** are standard. The round board has no corners,
  so stalemate is rare; when it does occur it is an honest **draw**.
- Additional draws: the **fifty-move** rule (100 half-moves with no pawn move or
  capture), lone kings (K vs K), and a hard move cap (for termination).
- **White (player 1) moves first.**

## Sources

- Chess Variants Pages — *Circular Chess* (Hans Bodlaender, corrected by 1996
  World Champion Rob Stevens): https://www.chessvariants.com/shape.dir/circular.html
- Wikipedia — *Circular chess*.
- George Jelliss, *mayhematics.com* — round-board chess (Lincoln version notes:
  double first step retained; no en passant, no castling; null-move ban).
- The Circular Chess Society / World Championship rules (Reynolds, Lincoln 1996).
