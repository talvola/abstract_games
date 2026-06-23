# Halma

**Halma** (Greek for "jump", invented 1883) is the classic jump-race game and
the direct ancestor of Chinese Checkers. Two players race their pieces across a
square board from their own corner camp into the opponent's corner camp. Nothing
is ever captured.

## Board and camps

The board is a square grid. A `size` option chooses the variant:

- **8×8 — 10 pieces each (default, snappy).**
- **16×16 — 19 pieces each (classic).**

Each player's pieces start packed into a **triangular camp** in one corner.
Coordinates are `c,r` with `c` the column (0 = left) and `r` the row (0 = top).

**Player 1 (player 0)** starts in the **top-left** corner; **Player 2
(player 1)** starts in the **diagonally opposite bottom-right** corner (the
180° rotation of player 1's camp).

### 8×8 camp shapes (10 pieces)

Player 1's camp, per-row column counts from the corner:

```
row 0: c 0,1,2,3   (4)
row 1: c 0,1,2     (3)
row 2: c 0,1       (2)
row 3: c 0         (1)
```

Player 2's camp is the same triangle rotated 180° into the bottom-right corner
(cells `(7,7),(6,7),(5,7),(4,7),(7,6),(6,6),(5,6),(7,5),(6,5),(7,4)`).

### 16×16 camp shapes (19 pieces)

Player 1's camp, per-row column counts from the corner:

```
row 0: c 0,1,2,3,4   (5)
row 1: c 0,1,2,3,4   (5)
row 2: c 0,1,2,3     (4)
row 3: c 0,1,2       (3)
row 4: c 0,1         (2)
```

Player 2's camp is the 180° rotation into the bottom-right corner.

In the board display each player's **target** camp is tinted faintly so the goal
is visible.

## Movement

On your turn you make **one** of the following with a single piece:

- **(A) Step** — move the piece to any of the **8 adjacent** squares
  (orthogonal or diagonal) that is **empty**.

- **(B) Jump** — hop over **exactly one** adjacent occupied square (a piece of
  **either** player — there is no capture, the jumped piece stays put) in any of
  the 8 directions, landing on the **empty** square immediately beyond. From the
  landing square you **may continue jumping** (each further hop may be in a
  different direction). The entire chain of jumps is **one move**, and you may
  **stop after any hop** you like.

You may **not** mix a step and a jump in the same turn: a step move is exactly
one square; a jump move is one-or-more jumps.

### Cannot leave the opposing camp once entered

Once one of your pieces has reached the **opposing (target) camp** — the camp
you are racing to fill — it may **not leave it again**. Such a piece may only
move to cells that are themselves inside the target camp (it may still shuffle
**within** the camp). This applies to steps and to every landing of a jump
chain (the piece may neither stop on nor pass through a cell outside the target
camp). A piece that is not in the target camp is unrestricted.

### Move notation

A move is a `>`-separated path of the squares the piece occupies:

- a step is `a>b` (e.g. `1,2>2,3`);
- a jump chain is `a>b>c>…` listing every square it lands on
  (e.g. `2,1>4,3>4,5`).

Because every legal stopping point of a chain is offered as its own move, the
UI lets you click a jump out as far as you wish and stop.

## Winning (anti-spoiling)

You win when your **target** camp (the opponent's starting camp, the mirror
corner) is **entirely occupied** — by **any** pieces — **and at least one** of
those occupants is one of **your own** pieces. Any **empty** target cell means
you have not yet won.

**Enemy pieces in your target camp do not block your win.** If an opponent parks
a piece ("squats") in your target camp, that piece merely fills one of the slots
that must be occupied — it cannot deny you the win. You still have to actually
deliver at least one of your own pieces into the camp.

This resolves Halma's classic **spoiling problem**, where an opponent could
permanently deny a win by leaving a single piece sitting in your target camp,
forcing a no-progress draw. Halma has several competing spoiling resolutions
(e.g. forbidding any piece from remaining in its own home camp at the end); this
package implements the most standard one — **"enemy pieces in your target camp
don't block your win."**

## Draw (termination safety net)

A no-progress / ply cap keeps the game finite and guarantees termination (it is
a safety net, not a strategic rule):

- **No-progress draw cap.** Each ply, the moving player's total *goal-distance*
  (the sum over their pieces of the Chebyshev distance to their target corner)
  is checked; if it does **not** strictly decrease for **60 consecutive plies**
  (and no further own piece enters the target camp), the game is a **draw**.
- **Hard ply cap.** A hard **400-ply** cap also forces a **draw**. In ordinary
  play a side homes in long before either cap.

These rules are documented here as the local source of truth.
