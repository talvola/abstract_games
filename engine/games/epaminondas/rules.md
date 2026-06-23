# Epaminondas

A phalanx war game designed by **Robert Abbott** (1975). Marshal lines of pieces
("phalanxes") across the board and break through onto your opponent's back row.

## Board & setup
A **14-column × 12-row** rectangular board. Cells are addressed `c,r` with
`0 ≤ c < 14` and `0 ≤ r < 12`.

- **Player 0 (Red)** fills rows **0 and 1** (its **back/home row is row 0**) and
  moves first.
- **Player 1 (Blue)** fills rows **10 and 11** (its **back/home row is row 11**).

Each side therefore starts with two full rows — 28 pieces.

## The phalanx
A **phalanx** is a *maximal* straight line of one or more friendly pieces that sit
adjacent to one another along **one of the eight directions** — the four
orthogonals (up/down/left/right) **and** the four diagonals. "Maximal" means it
cannot be extended by another friendly piece at either end along that same axis.
A single piece is a phalanx of length 1.

## Moving a phalanx
On your turn pick one phalanx and a direction **along its own axis** (either way
along the line). A phalanx of length **L** may advance **1 up to L** squares: the
entire line slides that many steps in the chosen direction. Sliding `k` steps
vacates the `k` rear squares and occupies `k` new squares at the front.

- Every square the front passes through, **and** every destination square, must
  be **EMPTY**.
- A phalanx may **not** move onto or through a friendly piece, and may **never
  jump** any piece.

(In this implementation a move is written as `rear>head_destination`: the source
cell is the phalanx's rear/trailing cell and the destination is where its leading
cell lands — so the UI lets you click the rear of the phalanx, then its landing
square.)

## Capturing
A phalanx may **capture** an opposing phalanx that lies **directly ahead on the
same line** — but **only if the moving phalanx is STRICTLY LONGER** than that
enemy phalanx.

- The mover advances so its **front piece lands exactly on the FRONT square** of
  the enemy phalanx (the square nearest the mover).
- The enemy front must be reachable within the move distance (within `L` squares
  of the mover's front) and **all squares between the two fronts must be empty**
  (no jumping).
- The **entire enemy phalanx** lying on that line is removed.
- You may **never** capture an enemy phalanx of **equal or greater length**, and
  you may never capture by moving through any piece.

The enemy phalanx's length, for the strictly-longer comparison, is the maximal
run of enemy pieces along the mover's axis starting at that front square and
extending **away** from the mover.

## Winning — the "crossing"
Your goal is to **cross**: get more of your pieces onto the **opponent's back
row** than they have on **yours**, a lead they cannot immediately undo.

The standard deferred-crossing rule, **exactly as implemented here**:

> After **every** move, look at the player who is *not* about to move (the
> opponent of the player who just moved — the side that just received its single
> free reply). Let **X** = that player's piece count on the mover's back row and
> **Y** = the mover's piece count on that player's back row. **If X > Y (and
> X > 0), that player wins immediately.**

In practice this means: when you push a piece onto the enemy back row you
*threaten* to win. Your opponent then gets **exactly one move** to respond — they
may **capture your crossing piece**, or **place an equal-or-greater count on your
own back row** to neutralize the threat. If, at the end of that single reply, you
still hold a **strict majority** on their back row, you win. A crossing that the
opponent equalizes (ties) or over-matches does **not** win.

Other terminal conditions:
- A player with **no pieces** loses (the opponent wins).
- A player with **no legal move** on their turn loses.
- A **ply cap** of 400 plies declares a **draw** (guarantees termination; in
  normal human play this is never reached).

### Documented interpretation / ruleset choice
Sources for Epaminondas state the crossing win slightly differently (some phrase
it as "you win at the start of your turn if you have more men on the far back
rank than your opponent has on yours"). These are equivalent in effect to the
rule above: the key invariant is that a crossing only wins **after the opponent
has had one move to answer it**, and only if a **strict** majority survives. This
package evaluates the condition from the perspective of the player who just got
their reply (i.e. immediately after each move), which yields exactly that
one-move-grace behaviour without needing a separate "announcement" phase. The
comparison is **strict** ( `>` ), so an equal count on both back rows is **not**
a win — the defender successfully equalizes by tying. This is the most standard
reading and is implemented cleanly; flagged for review if a stricter source
mandates a different equalization semantics.
