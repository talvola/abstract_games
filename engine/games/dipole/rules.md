# Dipole

A stacking game by **Mark Steere**, invented May 2007, played with an ordinary
checkers set. Rules as implemented here, taken from the designer's own rule
sheet: [Dipole_rules.pdf](https://www.marksteeregames.com/Dipole_rules.pdf).

## Board and setup

An **8×8 checkerboard** with a **dark square in each player's lower-left corner**.
**Only the 32 dark squares are used** — a checker never touches a light square.

Each player starts with **one single stack of all 12 of their checkers** (the
"pole" the game is named for), on a dark square of their own nearest row:

- **White** (bottom seat) on **e1** = `4,0`
- **Black** (top seat) on **d8** = `3,7`

```
   +---+---+---+---+---+---+---+---+
 8 |   |###|   |B12|   |###|   |###|
   +---+---+---+---+---+---+---+---+
 7 |###|   |###|   |###|   |###|   |
   +---+---+---+---+---+---+---+---+
 6 |   |###|   |###|   |###|   |###|
   +---+---+---+---+---+---+---+---+
 5 |###|   |###|   |###|   |###|   |
   +---+---+---+---+---+---+---+---+
 4 |   |###|   |###|   |###|   |###|
   +---+---+---+---+---+---+---+---+
 3 |###|   |###|   |###|   |###|   |
   +---+---+---+---+---+---+---+---+
 2 |   |###|   |###|   |###|   |###|
   +---+---+---+---+---+---+---+---+
 1 |###|   |###|   |W12|   |###|   |
   +---+---+---+---+---+---+---+---+
     a   b   c   d   e   f   g   h
```

(`###` = a dark, playable square. The two poles are 180°-rotationally symmetric.)

**White moves first.** A **Board** option offers the designer's larger variant:
a **10×10** board with **20 checkers** a side, White on **e1** = `4,0` and Black
on **f10** = `5,9`.

## The one rule everything follows from

> **The number of squares a stack is moved must equal the number of checkers in
> the moved stack.**

On your turn you take **any number of checkers off the top of one of your
stacks** (from 1 up to the whole stack) and move *those* checkers, in a straight
line, **exactly that many squares**. Whatever you left behind stays put.

- **Nothing ever blocks a move.** Stacks fly over anything in between,
  friendly or enemy, of any size.
- Because only dark squares exist, a **straight (non-diagonal) move must be an
  even number of squares**. Diagonal moves always land on a dark square, so any
  count works.

### Move, merge, capture, bear off

| Kind | Directions | Requirement |
|---|---|---|
| **Move** to an empty square | forward, diagonally forward | — |
| **Merge** onto your own stack | forward, diagonally forward | heights add |
| **Capture** an enemy stack | **any of the eight** | the enemy stack must be **no taller** than the moving sub-stack |
| **Bear off** (destination lies outside the board) | forward, diagonally forward | those checkers leave play **for good** |

"Forward" means toward the opponent's row: **up** the board for White, **down**
for Black.

A **capture removes the ENTIRE enemy stack** from the game — it is not captured
into your stack, it is gone. Your moving sub-stack then occupies the square.
You may only capture a stack of size **≤** the number of checkers you moved.

**Bearing off:** pretend the squares continue forever beyond the edge and make
the move normally; if the destination is off the real board, the moved checkers
are removed from play. The dark-square rule still applies out there, so a lone
checker on the far row can leave *diagonally* (1 square) but not straight ahead.
Removal is possible **only** in the three forward directions — you can never
retreat off your own edge.

## Sitting out

> "If you have no moves available, you must sit the game out until you do have a
> move available. If you have any moves available, you must move. There will
> always be a move available to one player or the other."

The engine implements this by simply not offering the turn to a player who has
no legal move; the other player moves again (the caption says so, e.g. *"Black
to move — White has no legal move"*).

## Object of the game

> **To win, all of your opponent's checkers must be removed from the board.**

Both capturing and bearing off remove checkers permanently, so this cuts both
ways: **if you bear off your own last checker, you lose.** Bearing off your big
opening stack is legal and instantly fatal — `e1: bear off 12` on move 1 hands
the game to Black.

**Draws cannot occur in Dipole** — the designer's words, and provably so here:
see *Interpretations* 8 for why neither player can ever be stalemated out of a
move, and *Why the game must end* for why the game cannot go on forever. No
draw has been seen in 3,800 machine-played games either.

## Notation and clicking

- A normal move, merge or capture is `from>to`, e.g. `4,0>7,3` (e1–h4). The
  number of checkers moved is *implied* — it is exactly the distance — so you
  simply **click your stack, then the destination**.
- A bear-off has no destination square, so it is written `from>off=k` and is
  offered as a **button** under the board, labelled e.g. *"e1: bear off 4"*.
  There is one button per distinct count (from a 12-stack on e1: 4 through 12).

## How this differs from the other stacking games here

Dipole is not a relative of **Focus** (move the top *k* of a stack exactly *k*
cells and pile onto whatever is there, keeping enemy men as prisoners under
yours), of **Mixtour** (move onto another stack a distance equal to the *target*
stack's height, never to an empty cell, and win by building a 5-tower), or of
**Lasca**/**Bashni** (draughts jumps that tuck the jumped piece under your
column). Those are all games of **mixed-colour columns**, where control shifts
as the top piece changes.

**In Dipole every stack is a single colour, and captured material is destroyed,
never gained.** The whole game is the interaction of two ideas found nowhere
else in this library: *distance equals the number of movers*, and *the board
edge is a shredder that both players are being pushed toward*, because
non-capturing moves are forward-only. Material only ever goes down, and you lose
by running out — so the tension is between advancing (to attack) and hoarding
(to survive). Its nearest cousins by feel are **Emergo** and **Attangle**, and
they are structurally different games.

## Interpretations

Everything below is decided by the rule sheet; these are the places where a
naive reading could have gone another way.

1. **The pole squares.** The text never names them; they were read off Figure 1
   of the PDF (pixel-measured against the printed grid at 300 dpi — White on
   **e1**, Black on **d8**) and cross-checked for 180° symmetry. The 10×10
   squares (e1 / f10) follow the same rule — the dark square of the near row
   closest to the board's centre file. Both agree with the AbstractPlay
   reference implementation.
   **Steere revised this.** An earlier printing of the same sheet, still
   mirrored at
   [superdupergames.org/rules/dipole.pdf](https://superdupergames.org/rules/dipole.pdf),
   says *"Note the asymmetric arrangement with both stacks just left of center,
   from White's perspective"* and its Figure 1 puts White on **c1** (Black stays
   on d8) — an arrangement that is **not** 180°-symmetric. The current sheet at
   marksteeregames.com dropped that sentence and moved White to e1; the
   [30 May 2009 Wayback capture](https://web.archive.org/web/20090530041122/http://www.marksteeregames.com/Dipole_rules.pdf)
   already matches today's text word for word, so the setting has been e1 / d8
   for at least fifteen years. **This implementation follows the current sheet**
   (e1 / d8), and the 10×10 board follows its symmetry rather than the old
   sheet's *"both just right of center"*.
2. **Who moves first** is not stated on the current sheet, but the earlier
   printing says outright *"White moves first"*, and
   [igGameCenter](https://iggamecenter.com/en/rules/dipole) — a third,
   independent implementation — says *"Players move alternately, starting with
   the player with the light checkers."* White (the bottom seat) moves first,
   which is also this platform's seat-0-first convention.
3. **"A portion of a stack"** is taken off the **top**. Since every stack is
   mono-coloured this is only bookkeeping — a stack is fully described by its
   owner and its height.
4. **Bear-off counts.** The rule sheet says a move whose destination falls
   outside the board removes the moved checkers, so *every* sub-stack size whose
   destination is off the board is a distinct legal move. From the opening
   12-stack on e1 that is nine different bear-offs (4…12), not one. The
   AbstractPlay implementation only supports the smallest such count, because
   its move notation has no room for the number; the rule sheet wins here and
   the divergence is documented in `_diff_gameslib.py`.
5. **Bear-off direction.** "Stacks can only be removed in the forward or
   diagonally forward directions", so a capture direction can never take you off
   the board and you can never voluntarily retreat off your own edge.
6. **Dark-square parity applies beyond the edge** ("pretend the board squares
   extend outward far beyond the boundaries, and make a basic move
   accordingly"), so a straight bear-off still needs an even count.
7. **Winning by wiping out the opponent takes effect immediately**, on the move
   that does it — it is not deferred to the wiped-out player's turn. (The
   AbstractPlay reference only notices such a win one ply later, after the
   emptied player passes; the winner is the same either way.)
8. **A double stalemate is impossible**, and here is why. Take the **tallest
   stack on the board**, height *H* on some square, and move all *H* of it one
   diagonal step forward per checker. A diagonal destination is always a dark
   square, so parity never blocks it, and exactly one of three things is true:
   the destination is off the board (a legal bear-off), it is empty or friendly
   (a legal move or merge — both are forward), or it holds an enemy stack, whose
   height is at most *H* because *H* is the maximum (a legal capture). So **the
   owner of a maximal stack always has a move**, which is precisely Steere's
   *"there will always be a move available to one player or the other"*. The
   code still scores the unreachable case as an **honest draw**, `0–0`, rather
   than inventing a winner.
9. **The ply cap is a backstop, not a rule.** See below.

## Why the game must end (and why the ply cap is dead code)

Steere's own finitude essay at
[abstractgames.org/finitude.html](https://www.abstractgames.org/finitude.html)
discusses several of his games but **does not cover Dipole**, so here is the
argument this implementation relies on.

Let **Φ** be the sum, over every checker on the board, of how many rows it has
advanced toward the enemy's back row (so 0 ≤ Φ ≤ *M*·(*size*−1), where *M* is the
number of checkers in play).

- A **non-capturing move** (plain or merging) sends *k* checkers exactly *k* rows
  **forward**, so it raises Φ by *k*² ≥ 1.
- A **bear-off** strictly reduces the material *M*.
- A **capture** strictly reduces *M* (it deletes at least one enemy checker) and
  can lower Φ by at most *k*² ≤ *N*².

*M* never increases, so there are at most *M* = 2*N* material-reducing moves in
the whole game. **No position can ever recur:** if one did, *M* would have to be
equal at both visits (it never grows), so every move in between was
non-capturing, so Φ strictly rose — a contradiction. There is therefore no
repetition rule and none is needed.

Counting the bound **per checker** rather than per move is what makes it tight.
Let *I* be the total rise and *D* the total fall of one checker's own
advancement while it is on the board. Its advancement is never negative and
never exceeds *size*−1, so *I* ≤ (*size*−1) + *D*. Summing over all *M*
checkers, the total rise of Φ is at most *M*·(*size*−1) + Σ*D*, and Σ*D* is
bounded by the ≤ *M* captures, each of which can drag its movers back at most
*k*² ≤ *N*² rows. Every non-capturing move contributes at least 1 to that total
rise, so:

> plies ≤ *M*·(*size*−1) + *M*·*N*² + *M*
> = 24·7 + 24·144 + 24 = **3 648** (8×8), 40·9 + 40·400 + 40 = **16 400** (10×10).

The implementation carries that bound as a hard ply cap purely as a backstop; it
is **unreachable by the argument above**, and it has never fired. Over 3,800
machine-played random games the longest was **66 plies** (8×8) and **106 plies**
(10×10); with bear-offs deliberately suppressed to 1% to stretch games out, **89**
and **147**. Not one of those games was a draw. If the cap ever *did* fire it
would score a draw — and, as required everywhere in this codebase, **a decisive
result outranks it**: a win delivered on the capping ply is still a win.

## Correctness anchors

- **Differential vs the AbstractPlay `gameslib` reference implementation**
  (`_diff_gameslib.py`, manual/one-time, needs node; oracle only, no code
  copied): **500 random games, 30,474 positions, 485,703 moves compared** across
  both board sizes — the full on-board move set (as algebraic square pairs), the
  set of squares that can bear off, the entire board, the side to move,
  terminality and the winner. **0 mismatches.** The opening position matches
  move for move: 10 on-board moves from e1 (e3, e5, e7, f2, g3, h4, d2, c3, b4,
  a5) in both engines. The two known divergences — bear-off counts (see
  *Interpretations* 4) and gameslib's one-ply-late end-of-game detection (7) —
  are handled explicitly by the harness, and the rule sheet decides both.
- **`selftest.py`** (pure stdlib, in the test suite): the setup from Figure 1,
  the exact 19-move opening list derived square by square, the merge in Figure 4
  (3 + 2 = 5, jumping a black 5-stack), the capture in Figure 5, captures in all
  eight directions with the ≤ size rule at its boundary — *generated and then
  executed*, because a sideways capture is the one case where reading the row
  delta instead of the Chebyshev distance silently yields a zero-size move —
  bear-off parity, the two ways to win, the sit-out rule, a poisoned-counter
  re-scoring showing a win outranks the ply cap, a whole-game
  serialize/deserialize sweep comparing state objects, per-ply invariants
  (material never grows, no empty stack, at least one player always has a move),
  a `render()` bounds sweep on both board sizes, the last-move highlights, and a
  contrast check of the board tints against `Board.jsx`'s highlight colour.
- **Independent re-derivation (QA):** a second move generator written straight
  from the rule sheet, without reference to `game.py`, agreed on **39,528
  positions** across random boards and whole games on both sizes; an independent
  `apply_move` agreed on every ply of 800 games; the move-string ↔ (count,
  direction) mapping was proved bijective by enumerating every destination from
  every square on both sizes; and no double stalemate exists in 40,000 random
  positions or in an exhaustive scan of all 35,712 two-stack positions.
- **Mutation testing:** 55 targeted single-point mutations of `game.py` in two
  independent rounds (wrong distance, backward moves allowed, capture size rule
  inverted, reversed winner, aliased state, dropped serializer fields, hard-coded
  8×8 render, bare-float heuristic, draw counter consulted before the win check,
  turn handed to the stuck player, invisible board tints, …) — **all killed** by
  the selftest, except two that were then *proved* to be behaviour-preserving:
  the redundant bear-off parity test, and the no-checkers short-circuit in
  `_has_move`.
