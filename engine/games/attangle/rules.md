# Attangle

Dieter Stein, 2006 — the third game of his stacking trilogy (after *Accasta* and
*Matrx*). Implemented from the designer's official rules,
[spielstein.com/games/attangle/rules](https://spielstein.com/games/attangle/rules)
(*this version: 13 May 2008*), plus
[Grand Attangle](https://spielstein.com/games/attangle/rules/grand-attangle)
(*20 Sep 2009*) for the variant, and differentialled against the AbstractPlay
`gameslib` reference implementation (`_diff_ap.py`).

## Board and material

A hexagonal board with **4 spaces on each edge — 37 spaces** in all. The board
starts **empty**, and each player holds a stock of **18 pieces**. White moves
first, then turns alternate.

The **centre space `d4`** is a **void**: it must stay unoccupied for the whole
game. Pieces may still slide *across* it. It is drawn recessed and marked `x`.

Spaces use the official algebraic names: rows `a`–`g` from the bottom up,
numbered left to right inside each row (`a1`–`a4`, `b1`–`b5`, … `d1`–`d7`, …
`g1`–`g4`). The centre is `d4`.

A **stack** is a pile of pieces. The player who owns the **topmost** piece
controls the whole stack; a stack can never be split.

## A turn

Passing is not allowed. On your turn you must do exactly one of:

1. **Place** one piece from your stock on any empty space (never a void), or
2. **Capture.**

## Capturing

A capture moves **two stacks you control** onto **one stack the opponent
controls**, coming in from **two different directions**.

- Pieces move in a straight line, any number of spaces, over **empty spaces
  only** — so the two attackers are simply the first pieces *visible* from the
  target along two of its six rays. Rays may cross the void.
- The three piles merge onto the target's space, and you then **return the
  topmost piece — always one of yours — to your stock**.
- **The stack that remains may be at most three pieces high.**

That height limit is the whole capture law. It permits exactly the three
captures the rulebook illustrates:

| attackers | target | merged | after take-back |
|---|---|---|---|
| single + single | single | 3 | **2-stack** (Fig. 2.1) |
| single + single | double | 4 | **3-stack** (Fig. 2.2) |
| single + double | single | 4 | **3-stack** (Fig. 2.3) |

and it rules out everything else, which is what the designer's rule of thumb
"**only one double stack can be involved**" is shorthand for: a second double
would make the merged pile five high. It also means a **triple stack can never
move and can never be captured** — triples are frozen for the rest of the game.

**Where each piece ends up.** The target's pieces stay at the bottom; the
**taller** attacker lands on them, then the shorter one — so your two pieces sit
directly on top (exactly as the rulebook's Fig. 2.3 notes) — and the top one
goes back to stock. Concretely, writing stacks bottom→top with `W`/`B`:

- `W` + `W` capture `B` → `BW` (a 2-stack, White on top)
- `W` + `W` capture `WB` → `WBW`
- `BW` + `W` capture `B` → `BBW`

Because the merge order depends only on stack **height**, naming the two
attackers in either order gives the identical position.

## End of the game

- **You win the moment you complete your third triple stack.** (Triples can
  never be dismantled, so the count only ever goes up.)
- **A player with an empty stock and no capture available loses** — the rules
  say they must resign. Note that a player who still has a piece in stock always
  has a placement: the 36 non-void spaces exactly match the 36 pieces, so an
  empty space always exists while any piece is in hand.

**There is no draw.** Every terminal position is +1 / −1; there is no tie to
resolve and no ply cap that could fabricate one (see below).

## Termination

Attangle recycles material — a capture puts a piece *back* into stock — so it is
worth stating why it cannot run forever. Let `T` be the number of triple stacks
on the board and `D` the number of doubles.

- Every capture creates exactly one stack: type 2.1 gives `D+1, T+0`;
  types 2.2 and 2.3 each give `D−1, T+1`.
- A triple is permanent, and each `T+1` belongs to the mover, who wins on
  reaching 3. So at most **5** triples are ever made (2 + 2, then the winning
  one), i.e. at most 5 captures of type 2.2/2.3.
- The remaining captures (type 2.1) number `D_final + 5` at most, and
  `2·D_final + 3·T_final ≤ 36` pieces, so **captures ≤ 20**.
- Each placement spends a piece from stock, and stock is only refilled by a
  capture, so **placements ≤ 36 + captures**, and the whole game is at most
  **76 plies** (Grand Attangle: ≤ 9 triples, ≤ 31 captures, ≤ 110 plies).

The package therefore declares **no ply cap and no draw**. Random play ends in
roughly 30–100 plies; the selftest re-derives the two ceilings from the argument
above (rather than hard-coding them) and asserts every random game stays under
them, so a termination regression fails loudly instead of turning into a silent
draw.

## Variant: Grand Attangle (official)

Selectable from the lobby. Board with **5 spaces per edge (61 spaces)** and
**seven voids** — the centre `e5` plus `b3 c6 d2 f7 g2 h4`, a six-fold pinwheel
(read off the designer's setup figure and confirmed to be one rotational orbit).
Each player has **27 pieces**, **three of which start on the board**: White
`b4 f2 g6`, Black `c2 d7 h3` (also one six-fold orbit, colours alternating), so
**24 are in hand**. **Five** triple stacks win. Everything else is identical.

## Move encoding (this implementation)

Cells are axial ids `q,r`; the rules text above uses the official algebraic
names, and the move log shows those.

- **Placement** — a single cell, e.g. `0,-3`. One click on an empty space. The
  move log shows the algebraic name (`g1`).
- **Capture** — `attacker>attacker>target`, e.g. `-1,0>1,0>-3,0`: click your two
  attacking stacks, then the enemy stack. The move log shows `d1+d5xd3`
  (`#` when the move ends the game).

Both orders of the two attackers are listed as legal moves, so the board is
clickable whichever attacker you pick first; they are the *same* move and
produce byte-identical positions.

The two trays beside the board are **stock counters** (`P ×n`). You do not need
them to place — click an empty space directly.

## Interpretations and notes

- The designer's "only one double stack may be involved" is a **rule of thumb**
  for the height limit, not an extra rule: it is implied by "maximum height
  three after taking one piece back". This implementation enforces the height
  limit alone, which gives exactly the three captures of the rulebook figures.
- A ray is blocked by the **first** piece it meets, so two of your pieces in
  line with the target count as a single attacker; a capture genuinely needs two
  different directions.
- The designer's fourth figure — *"White or black: no captures are possible
  here"* — is reproduced verbatim as a test position (white `e1`, white-topped
  doubles `e2`/`f5`, black `d5`/`e5`, white `c4`): both sides really do have
  zero captures there, even though White sees `e5` from two directions, because
  both of those attackers are double stacks.
- The rules do not spell out what happens if a player has pieces in stock but no
  empty space. That case is unreachable (36 pieces, 36 non-void spaces — and 54
  and 54 in Grand Attangle), so nothing is invented for it.
- **Grand Attangle stock.** spielstein's equipment list is "2 × 27 pieces" and
  the setup is "the players place **3 of their pieces**", so 24 remain in hand —
  and 27 + 27 = 54 is exactly the number of non-void spaces, mirroring the base
  game's 18 + 18 = 36. AbstractPlay's `gameslib` instead starts the hand at 27
  *in addition* to the 3 placed pieces. This package follows the designer;
  `_diff_ap.py` sets the oracle's hand to 24 so the two are comparable (and can
  reproduce the divergence with `--ap-hand 27`).

## Why this is not Accasta

Both are Dieter Stein hex-37 stacking games, so the distinctness question is
fair — but only the board is shared.

|  | Accasta (1998) | Attangle (2006) |
|---|---|---|
| Start | both armies fully deployed in home "castles" | **empty board**; 18 pieces in hand |
| Turn | move a stack (or part of one) | **place a piece**, or capture |
| Piece types | Shields / Horses / Chariots, range 1/2/3 | one piece type |
| Movement | step-by-step, cannot jump, range from the piece | **only as part of a capture**: two stacks converge from two directions, any distance over empty spaces |
| Stacks | split anywhere, the head leads any number below | **never split**; height capped at 3, and a triple is frozen forever |
| Capture | landing on a stack buries it; recapture liberates | three piles merge and **one piece leaves the board**, back to stock |
| Goal | race — three stacks inside the enemy castle | **build three triple stacks**, anywhere |
| Board furniture | two 9-space castles | one untouchable **void** at the centre |

Accasta is a race across the board with a heterogeneous army; Attangle has no
race, no geography beyond the void, no piece types, and no stack movement at all
outside the converging capture. The tactical unit in Accasta is "which slice of
my tower do I lead where"; in Attangle it is "which two of my pieces see that
enemy stack". They share a designer and a board, not a game.
