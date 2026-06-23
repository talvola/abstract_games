# Dameo

**Dameo** is a modern draughts (checkers) variant invented by **Christian Freeling
in 2000**. It is played on a standard **8×8 board using ALL 64 squares** (unlike
classic draughts, which uses only the dark squares). Two players, **White** and
**Black**, each command **18 men**. White moves up the board (toward higher rows);
Black moves down.

Cells use `col,row` coordinates, `0,0` in White's lower-left corner.

## Starting position

Each side fills a **trapezoid**: the full back rank, then a row of six, then a row
of four, centred:

- **White:** row 0 → all eight cells `0,0 … 7,0`; row 1 → `1,1 … 6,1`; row 2 → `2,2 … 5,2`.
- **Black:** the mirror image — row 7 → all eight cells; row 6 → `1,6 … 6,6`; row 5 → `2,5 … 5,5`.

That is 8 + 6 + 4 = **18 men** per side.

## Moving (no capture available)

A man moves **forward only**, in one of two ways:

1. **Man step** — a single man moves **one square forward**: straight ahead
   (orthogonally) **or** diagonally forward. Men never step sideways or backward.

2. **Linear movement (the Dameo signature)** — a **straight, unbroken line of two
   or more of your own men**, lined up along a **forward axis** (a column, or
   either forward diagonal), moves **one square forward as a single unit** when the
   square at the front of the line is empty. The whole file shifts forward by one:
   the rear man vacates its square and the empty square just past the front fills.
   Equivalently, the rear man "jumps over" the file to the empty square in front of
   it. A man that shifts onto the far rank is promoted.

   A **horizontal (sideways) line cannot make a linear move** — sideways is not a
   forward man-direction. Kings never take part in a linear move.

In the click UI a linear move is entered by clicking the **rear man** of the file
and then the **empty destination** square just past the front; because that span is
two or more squares it never collides with a one-square man step.

## Capturing — mandatory, maximal, chained

Capturing is **compulsory**. Whenever any capture is available you must capture,
and you must play a sequence that captures the **maximum possible number** of enemy
pieces (the **majority rule**); among equally-long maximal sequences you may choose
any.

- **Men capture ORTHOGONALLY only** — forward, backward **or** sideways (never
  diagonally) — by jumping a single adjacent enemy piece and landing on the empty
  square directly beyond it.
- **Chained:** if, after a jump, another enemy can be jumped, the capture **must**
  continue (with right-angle turns allowed) until no further jump is possible.
- **End-of-move removal:** captured pieces stay on the board (blocking the path)
  until the entire move is finished, then **all** are removed at once. A piece may
  **not be jumped twice** in one move.

## Kings (flying kings)

A man that **ends its move on the far rank** is promoted to a **King**.

- **Move:** a king moves **like a chess queen** — any number of empty squares in
  any of the eight directions.
- **Capture:** a king captures **rook-wise (orthogonally only)** by the **long
  leap** — it slides over any number of empty squares to a single enemy piece, then
  lands on any empty square beyond it (before the next obstruction), and may
  continue the chain. The same mandatory / maximal / end-of-move-removal rules
  apply.

## Winning and draws

A player who has **no men or kings left**, or who **has no legal move**, **loses**.

To guarantee termination this implementation adds the standard draughts
**no-progress draw**: if 50 plies pass with no capture and no man advancing
(only king moves), the game is a **draw**; a hard 400-ply cap also draws.

## Implementation notes / ruleset choices

- **Linear-movement distance — one square (faithful to Freeling).** The
  authoritative mindsports.nl rules and every faithful implementation
  (iggamecenter, playstrategy, Wikipedia) define a linear move as the line moving
  **one square forward** along its axis (equivalently, the rear man jumping over the
  file to the empty square in front). This package implements exactly that.
  *(Some informal descriptions suggest a line can slide "any distance" over empty
  squares — that is not the documented Dameo rule, so it is **not** implemented.)*
- **Linear-move orientations:** only the three forward axes (vertical column, and
  the two forward diagonals). A horizontal line cannot move, matching "men move
  forward only".
- Captures are orthogonal-only for both men and kings; movement is queen-wise for
  kings and forward-only (orthogonal + diagonal) for men — the deliberate Dameo
  asymmetry between *movement* directions and *capture* directions.

Official rules: <https://mindsports.nl/index.php/arena/dameo/65-rules>
