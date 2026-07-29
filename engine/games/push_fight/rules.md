# Push Fight

A two-player abstract game by **Brett Picotte** (~1990; published by Brettco,
briefly by Penny Arcade in 2015). Shove one of your opponent's pieces off the
board and you win. **Solved completely in 2022** — see *Correctness anchors*.

## The board

Not a rectangle: a 4×8 grid with **six squares missing**. Rank 4 spans files
**c–g**, rank 1 spans files **b–f**, and ranks 2 and 3 are full (a–h) — **26
squares** in all. The shape has 180° rotational symmetry.

**Side rails** (`====` below) run along the *outer top edge of rank 4* and the
*outer bottom edge of rank 1*. A piece can never be pushed through a rail.
**Every other board edge is open** — including the top of `a3`, `b3`, `h3`, the
bottom of `a2`, `g2`, `h2`, the sides, and the little steps beside `c4`/`g4` and
`b1`/`f1`. A piece pushed across an open edge falls off.

```
        a  b  c  d  e  f  g  h
              ==============                <- side rail
   4          .  .  .  .  .                 files c-g
   3    .  .  .  .  .  .  .  .              files a-h
   2    .  .  .  .  .  .  .  .              files a-h
   1       .  .  .  .  .                    files b-f
           ==============                   <- side rail
```

## Pieces

Each player has **five** pieces: **3 squares** (drawn as ■; these are the ones
that can push) and **2 circles** (drawn as discs; they move but never push).
There is also a single shared **anchor**, shown here as a **dark red tint on the
cell** plus the ▣ glyph on the anchored square (a plain square is ■).

Red (player 1) moves first.

## Setup

Two options in the lobby:

- **Free placement (official, the default).** Red places all five pieces, one
  per click, anywhere on the **left half** (files a–d); then Blue places all five
  on the **right half** (files e–h). Pick a square or a circle from your tray,
  then click a square. Most players put four pieces on their centre file.
- **Standard opening.** Skips placement and starts from the position below —
  the default opening of the Push Fight Analyzer, 180°-symmetric, four pieces on
  each centre file:

```
   . O X . .          O = red square    X = blue square
 . . . o X x . .      o = red circle    x = blue circle
 . . o O x . . .
   . . O X .
```

## Your turn

Up to **two moves** (both optional), then **exactly one push** — the push is
mandatory and ends your turn.

- **Move**: pick any one of your pieces (square or circle) and slide it to any
  square reachable through a connected chain of **empty** squares, orthogonally.
  You may not jump over any piece. Move one piece, then a second piece — or move
  nothing at all.
- **Push**: pick one of your **squares** and shove it exactly one step up, down,
  left or right into an **occupied** square. Everything in an unbroken line ahead
  of it moves one step in the same direction, friend or foe alike. A push must
  move **at least one other piece** — stepping into an empty square is a move,
  not a push.

A push is **illegal** if it would drive any piece **through a side rail**, or if
it would move the **anchored** piece (including when that piece merely sits
somewhere in the line being pushed).

**After your push, the anchor moves onto the square that just pushed.** Your
opponent may not push that piece on their next turn. The anchored piece may
still move, and may still push (the anchor only stops the *opponent* pushing it);
once someone else pushes, the anchor leaves it.

## How this is played on the platform

A turn is entered as **separate clicks**, each its own ply, and you keep the turn
until you push:

| what | move string | example |
|---|---|---|
| place a piece (free setup) | `S@c,r` / `C@c,r` | click the tray chip, then a square |
| move | `from>to` | `c2-b2` in the log |
| push | `from>to` | `d2-e2 push` in the log |

Moves and pushes can never be confused: a **move always ends on an empty square**
and a **push always ends on an occupied one**. So the legal pushes are offered
alongside the legal moves at every point in your turn — just click a push
whenever you are ready, or after two moves when only pushes remain. There is no
"done moving" button because none is needed.

The interface only ever offers you a move that still leaves you a legal push, so
you can never paint yourself into a corner mid-turn.

## Winning

- **A piece pushed off the board loses the game for its owner** — including one
  of your own pieces that you shove off yourself. (Such self-destructive pushes
  are legal; the engine offers them, and they lose immediately.)
- **A player who cannot complete a turn** — no legal push after any legal
  sequence of 0, 1 or 2 moves — **loses**.

## Draws (as implemented)

The official rules have no draw rule other than agreement ("If you and your
opponent get stuck for any reason, you can agree to call the game a draw. A draw
is very rare."), and the complete solution shows that the standard openings are
in fact **tied with perfect play** — perfect play never ends. Two backstops
therefore make the game terminate, and both score an honest **0–0 draw**:

- **Threefold repetition** — the same position (pieces, anchor and side to move,
  measured at the start of a turn) occurring for the third time.
- **Turn limit** — 300 completed turns. The complete solution's longest forced
  win is 49 turns for one player (97 turns in total), so the cap sits at roughly
  three times the game's own decisive bound and can never truncate a real fight.

**A decisive result always outranks both counters**: a piece pushed off the board
never consults them at all, and a "cannot push" loss is decided before them.

## Interpretations

1. **Who loses when a piece falls off.** The official sheet is written from the
   winner's side ("push ONE of their opponent's pieces off the board"). Bosboom,
   Demaine & Rudoy state it precisely — *"A player loses if any of their pieces
   are pushed off the board (even by their own push)"* — and Verver's solver
   counts positions where a player "cannot legally push without pushing their own
   piece off the board" as immediate losses. We implement the loser-side rule.
2. **"Cannot push" is evaluated over the whole turn**, not just the current
   position: you are only stuck if *no* sequence of up to two moves leaves you a
   push. This matches the solver, whose successor list is a list of complete
   turns. (In practice the rule appears to be unreachable — see below.)
3. **The anchored piece can still push and still move.** The official rules only
   forbid the *opponent* pushing it.
4. **Free placement is unrestricted within your half** — you may stack your
   pieces however you like, including badly. The official sheet's "Position your
   pieces to leave yourself a push or you lose" is the only constraint.
5. **Red always takes the left half.** The official rules let the first player
   *choose* a side; since the board is 180°-symmetric that choice is cosmetic, so
   we fix it (as Verver's implementation does).
6. **Repetition and the turn limit are ours**, not Picotte's. They replace the
   official "agree to a draw", which an asynchronous engine cannot offer.

## How this differs from the library's other pushing games

**Abalone** is the nearest relative — also "shove enemy pieces off the edge" —
but it is a hex board where pushing is a *contest of numbers* (a longer line of
your marbles pushes a shorter enemy line), pushes are optional, there is no
anchor and no rails, and you must eject six marbles to win. Push Fight ejects
**one** piece, the push is **mandatory and unopposed** (any square shoves any
line), and the **anchor** — a piece that cannot be pushed back on the very next
turn — is the tactical heart of the game and has no analogue in Abalone.
**boop** pushes every neighbour one square but returns booped pieces to their
owner's pool and is won by lining up three cats; **Quixo** slides whole rows and
is an N-in-a-row game; **Ataxx**, **Three Musketeers** and **Konobi** share
nothing beyond the square grid. Push Fight's distinguishing trio — the mandatory
push, the single shared anchor, and the notched board with partial rails — is
unique in this library.

## Correctness anchors

- **The board geometry, the rails and the standard opening** come from Maks
  Verver's [complete solution of Push Fight](https://github.com/maksverver/pushfight)
  (its `html/src/board.js` `FIELD_INDEX` and `INITIAL_PIECES`), corroborated by
  the official rules page and by figure 2.1 of Bosboom, Demaine & Rudoy,
  [*Computational Complexity of Generalized Push Fight*](https://arxiv.org/abs/1803.03708).
  The selftest asserts the standard opening's 26-character position string is
  exactly `.OX.....oXx....oOx.....OX.`, which pins the cell set, the traversal
  order and the opening at once. The eight cells our board gives degree 2 are
  exactly the eight Verver proves can never hold the anchor
  (`a2 a3 b1 c4 f1 g4 h2 h3`).
- **Turn differential vs the reference generator** (`_diff_reference.py`, needs
  `node`; it emits its own harness with `--write-harness`, so the run is
  reproducible from the three upstream `html/src/*.js` files alone): at every
  turn-start position of random games it compares both the complete **set of
  legal turns** and the **resolved position after each turn** (landing squares,
  anchor placement, and which colour lost a piece). Largest run: 243 positions,
  **1,316,081 legal turns compared, 0 mismatches**. The harness is driven with an
  *algebraic* piece list rather than our 26-character permutation string, so the
  oracle is not handed the very field ordering it is meant to check.
- **Differential vs the complete tablebase** (`_diff_solver.py`, needs network;
  `https://styx.verver.ch/pushfight/lookup/perms/…`): 14 positions, **22,067
  successor positions and 64,744 legal turns, 0 mismatches**, and mate-in-1
  agreement on all 14 (11 `W1`, 1 `W3`, 2 `T`); independently re-run on 6 further
  sampled positions (8,414 successors, 0 mismatches). Because the solver's
  successors are replayed *through this engine*, this checks where every shoved
  piece lands and where the anchor ends up, not merely which turns are legal.
- **The solved value.** Verver reports that *"every starting position where each
  player puts four pieces on the starting line leads to a tied position"*.
  Spot-check from our standard opening: the tablebase scores the positions after
  `d4-e4`, `c2-d2`, `d1-e1`, `d1-c3,d4-d3` and `c2-c3,d2-b2,d4-d3` all as **`T`**,
  so Red can force at least a draw; and it scores the position after
  `d4-c4,c2-d2` as **`W1`** — a blunder — where this engine finds the same
  immediate win for Blue (`e4-d4, e3-e4, d4-c4`, shoving the red square off
  beside `c4`). Our engine also agrees the opening itself has no immediate win.
- **"Cannot push" appears to be unreachable in the standard 3+2 game.** It never
  occurred in 3,000 random games, and an exhaustive sweep of all
  C(26,10) = 5,311,735 ten-piece occupancy sets found 851 with five or more
  fully-immobile squares and **no** stuck position among any assignment of
  colours, piece types and anchor. Informally: a square with an occupied
  horizontal neighbour can always push (there is no horizontal rail) unless the
  anchor is in that line, and with three squares and only one anchor a player can
  always find one. The rule is implemented and unit-tested anyway, on a
  synthetic position driven through `apply_move`.
- **Selftest**: 28 checks (pure stdlib, <2 s), covering geometry, rails, open
  edges, push chains and anchor placement, both loss conditions, the "cannot
  push" rule being judged over a *whole* two-move turn, the two draw counters
  (each proved load-bearing, proved not to fire one step early *and* pinned to an
  exact threshold), "a decisive result outranks every counter" under poisoned
  counters, the state round trip over whole games plus hand-built drawn states,
  render bounds, the anchor tint surviving the last-move highlight, and the
  heuristic's shape under a forced MCTS rollout cutoff.

## Official source

Brettco's rules page (the site's DNS no longer resolves; archived at
[web.archive.org](http://web.archive.org/web/20250523181918/https://pushfightgame.com/rules.htm)).
