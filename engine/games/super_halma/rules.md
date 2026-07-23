# Super Halma

**Super Halma** (Stephen Perkis, *Abstract Games* issue 15, Autumn 2003) is a
10×10 variant of Halma whose defining novelty is a **long-range symmetric jump**:
a piece can leap over another piece any number of empty squares away, landing the
same distance beyond it. The 10×10 board with 19 pieces per side is Perkis's
"10x10 Super Halma"; a 10×10 International Checkers set is ideal for it.

Two players race their pieces from their own corner camp into the diagonally
opposite enemy camp. Nothing is ever captured.

## Board and camps

The board is a **10×10** grid. Coordinates are `c,r` with `c` the column
(0 = left) and `r` the row (0 = top).

Each player has **19 pieces** packed into a staircase **home camp**:

- **White (player 0)** starts in the **top-left** corner and **moves first**.
- **Black (player 1)** starts in the **diagonally opposite bottom-right** corner
  (the 180° rotation of White's camp).

White's camp, per-row column counts from the top-left corner:

```
row 0: c 0,1,2,3,4   (5)
row 1: c 0,1,2,3,4   (5)
row 2: c 0,1,2,3     (4)
row 3: c 0,1,2       (3)
row 4: c 0,1         (2)
```

That is 5+5+4+3+2 = **19**. Black's camp is the same staircase rotated 180° into
the bottom-right corner. In the board display each player's **target** camp is
tinted faintly so the goal is visible.

## Movement

There is no passing, and exactly **one** of your own pieces moves per turn. On
your turn you make **one** of the following (you may **not** combine a step and a
jump in the same turn):

- **(A) Step** — move the piece **one square** in any of the **8 directions**
  (orthogonal or diagonal) to an **empty** square.

- **(B) Jump** — the Super Halma move. Jump over **any one** piece (a piece of
  **either** player — there is no capture, the jumped piece stays put) that lies
  some number **k ≥ 0** of **empty** squares away in a straight line (one of the
  8 directions), landing the **same number k** of empty squares **beyond** it in
  that same straight line. The landing is thus the **mirror image** of the start
  across the jumped piece. All *k* intervening squares on **both** sides and the
  **landing** square must be empty. **k = 0** (adjacent piece, land immediately
  beyond) is the ordinary Halma jump.

  Because only empty squares may lie between you and the jumped piece, the piece
  you jump is always the **first** occupied square along that direction. From the
  landing square you **may continue jumping** (each further hop may pick a new
  direction). The entire chain is **one move**, and you may **stop after any hop**.

Pieces may **enter and exit both camps without restriction** (unlike some Halma
variants, there is no rule pinning a piece inside a camp).

### Move notation

A move is a `>`-separated path of the squares the piece occupies:

- a step or a single jump is `a>b` (e.g. `0,5>1,5` step, `0,5>6,5` jump);
- a jump chain is `a>b>c>…` listing every square it lands on (e.g. `0,0>2,0>4,0`).

Because every legal stopping point of a chain is offered as its own move, the UI
lets you click a jump out as far as you wish and stop.

## Winning

You win by **occupying every square of the enemy camp** (your target camp, the
mirror corner). Concretely: the target camp is **entirely occupied** — by **any**
pieces — **and at least one** occupant is one of **your own** pieces. Any empty
target cell means you have not yet won.

**Enemy pieces in your target camp do not block your win** (squatter guard). If
an opponent parks a piece in your target camp, it merely fills one of the slots
that must be occupied — it cannot deny you the win. You still must deliver at
least one of your own pieces into the camp.

### Documented simplification of the "small print" rules

Perkis's article proposes elaborate **anti-spoiling "small print" winning
conditions** (a win when no piece can be moved closer to the enemy corner / to a
vacant target square, with a connected-group-plus-accessible-square exception)
and **trapped-piece draw** clauses. By the author's own account these are
"non-interfering" rules that, between genuine opponents, **almost never fire** —
the *normal* win (occupying all enemy-camp squares) is stated in the article as
an instance of them.

This package implements the **normal win + squatter guard** (matching the
platform's `halma` package) and **omits** the full small-print anti-spoiling /
trapped-piece machinery. This is a documented interpretation; it preserves
ordinary play and only differs in the pathological spoiling positions those rules
target.

## Draw (termination safety net)

A no-progress / ply cap keeps the game finite and guarantees termination (a
safety net, not a strategic rule):

- **No-progress draw cap.** Each ply, the moving player's total *goal-distance*
  (the sum over their pieces of the Chebyshev distance to their target corner) is
  checked; if it does **not** strictly decrease for **80 consecutive plies** (and
  no further own piece enters the target camp) the game is a **draw**.
- **Hard ply cap.** A hard **500-ply** cap also forces a **draw**. In ordinary
  play a side homes in long before either cap.

These caps are documented here as the local source of truth.
