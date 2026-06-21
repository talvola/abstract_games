# Fanorona

Fanorona, the national board game of Madagascar. This package implements the
full game (*Fanoron-Tsivy*, the 5×9 version) with mandatory capturing.

## Board

A grid of **5 rows × 9 columns** of intersections, rendered here as a
**9-wide × 5-tall square board**: pieces sit at the cell centres and the
alquerque-style connecting lines are *cosmetic* (not drawn). Cells use the
platform `col,row` notation, columns `0–8` and rows `0–4`.

### Lines (adjacency)

- **Orthogonal** neighbours (up/down/left/right) are **always** connected.
- **Diagonal** neighbours are connected **only on "strong" intersections**. A
  point `(c, r)` is **strong** (has the four diagonal lines) iff `c + r` is
  **even**; "weak" points (`c + r` odd) have only the four orthogonal lines.

So the strong points form a checkerboard; the centre `(4, 2)` is strong.

## Setup

All 45 intersections are filled except the **centre `(4, 2)`**, which starts
empty: **22 White** (player 0) vs **22 Black** (player 1).

- **White** fills the bottom two rows (`r = 0, 1`) — 18 pieces — plus four on
  the middle row.
- **Black** fills the top two rows (`r = 3, 4`) — 18 pieces — plus four on the
  middle row.
- **Middle "clash" row** (`r = 2`), left → right (column 4 empty):
  `Black, White, Black, White, –, Black, White, Black, White`
  (columns 0, 2, 5, 7 Black; columns 1, 3, 6, 8 White).

This is the standard alternating opening array that puts the two armies into
immediate contact. **White moves first.**

## Movement and capture

A piece moves **one step** along a connected line to an **empty** adjacent
point. There are two ways to capture, both performed by that single step:

- **Approach** — you move *toward* the enemy. The first enemy on the far side
  of your **destination**, in your direction of travel, and **every enemy
  continuing in that straight line** (until a gap or one of your own pieces),
  is removed.
- **Withdrawal** — you move *away* from the enemy. The enemy directly
  **behind your starting point** (opposite your direction of travel), and its
  in-line successors (until a gap or a friendly piece), is removed.

A single step can be a pure approach, a pure withdrawal, or — if enemies sit on
**both** sides — offer **both**; see *Ruleset choices* below.

### Mandatory capture (and *paika*)

If **any** capture is available **anywhere** on the board, you **must** capture.
A non-capturing move (**paika**) is legal **only** when no capture exists for
the side to move.

### Capture chains

After capturing you **may continue** capturing **with the same piece**, subject
to two restrictions:

1. **Change direction** — no two consecutive steps may be along the same
   line-direction.
2. **No revisiting** — the moving piece may not return to a point it has already
   occupied during this turn (including its starting point).

You **may stop** the chain after any capture (you are never forced to continue),
and the chain necessarily ends when no further capturing step is available. The
**first** step of a turn that has any capture available must itself capture.

## Winning

You **win** by capturing **all** of the opponent's pieces. A player who has no
pieces, or who has **no legal move** on their turn, **loses**.

To guarantee termination for the platform's random self-play, a hard
**1000-ply cap** is applied; reaching it is scored as a **draw**. (In practice
games end by annihilation far sooner.)

## Move notation

A move is the platform's `>`-separated path of the points the piece visits,
e.g. `1,2>2,2` (a single step) or `1,1>2,1>2,2` (a two-capture chain). When a
single step offers **both** an approach and a withdrawal, the destination
carries a suffix to disambiguate: `=A` (approach) or `=W` (withdrawal), e.g.
`4,2>5,2=A`. Unambiguous capturing steps and paika moves carry no suffix.

## Ruleset choices (as implemented)

- **5×9 *Fanoron-Tsivy*** only (no smaller *Telo*/*Dimy*/*Efa-tra* boards).
- **Diagonal lines on strong points only**, with strong defined as
  `(c + r)` even — equivalently the corners and centre are strong.
- **Opening array**: the standard contact array described above, centre empty,
  White on the bottom.
- **Mandatory captures**, maximal chains *optional in length* (you may stop
  after any capture — this matches common Fanorona rules, where the player
  chooses when to end the chain; the engine offers every legal stopping point
  as a distinct move).
- **Approach-vs-withdrawal ambiguity**: when one step can capture in both
  manners, the **player chooses** exactly one (encoded `=A`/`=W`); you never get
  both lines at once.
- **No "official" published move/perft counts are asserted** — the bundled
  `selftest.py` instead checks the rule mechanics directly on hand-built
  positions plus an engine conformance pass.
- Some Fanorona traditions add an *eating-back* / repeated-attack restriction or
  a "Vela" finishing convention; those are **not** implemented here beyond the
  change-direction and no-revisit chain rules.
