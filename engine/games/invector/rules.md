# Invector

**Mark Steere, April 2026.** A two-player annihilation game on a Kōnane board.
Each turn one stone moves one step: either **onto an adjacent enemy stone**,
capturing it, or **onto an adjacent empty pit that is closer to the centre**.
Wipe out the enemy army and you win — *"one of the armies must be destroyed to
the last man."*

## Board and setup

A rectangular grid of pits, one stone per pit, **completely filled** at the start
with a checkerboard of black and white stones. The rule sheet requires **one even
dimension and one odd dimension** and illustrates a 5 × 4; this package offers the
family **W × (W−1)** with W even, so the width is always the even dimension and
the parity requirement cannot be violated by an option.

| Option | Board | Stones each | Opening moves | Proven ply bound |
|---:|---|---:|---:|---:|
| 4 | 4 × 3 (tiny — solved) | 6 | 17 | 26 |
| 6 | 6 × 5 | 15 | 49 | 96 |
| **8** | **8 × 7 (standard)** | **28** | **97** | **236** |
| 10 | 10 × 9 | 45 | 161 | 470 |
| 12 | 12 × 11 | 66 | 241 | 822 |
| 14 | 14 × 13 | 91 | 337 | 1316 |
| 16 | 16 × 15 | 120 | 449 | 1976 |

The **top-left pit holds a Black stone** and the colours alternate from there,
exactly as Figure 1 of the rule sheet draws it. **Black moves first.**

```
Figure 1 (5 × 4)      X = Black   O = White
   X O X O X
   O X O X O
   X O X O X
   O X O X O
```

Because the board starts full and every neighbour of a stone is an enemy, **every
opening move is a capture** — one for each orthogonal edge of the grid.

### The two centre pits

> *"...closer to center, Manhattan distance ... **[There are two center pits.]**"*

With one even and one odd dimension the geometric centre of the board falls
between two pits rather than on one. Those two pits — always orthogonally
adjacent, sharing the middle coordinate of the **odd** dimension and flanking the
centre along the **even** one — are the centre pits, and they are marked on the
board in the app.

```
Centre pits (*) — 5 × 4 as the sheet draws it, and the 8 × 7 default

   . . . . .            . . . . . . . .
   . . * . .            . . . . . . . .
   . . * . .            . . . . . . . .
   . . . . .            . . . * * . . .
                        . . . . . . . .
                        . . . . . . . .
                        . . . . . . . .
```

A pit's **distance** is its Manhattan distance to the *nearer* of the two centre
pits, so both centre pits are at distance 0.

## Playing a turn

Move **one stone of your own colour** one step. **Passing is not allowed**, but
**if you have no legal move your turn is skipped** and your opponent moves again.

### Capturing moves

Move onto an **orthogonally adjacent pit holding an enemy stone**. The enemy
stone is removed and yours takes its place (**capture by replacement**).
Direction is completely unrestricted — a capture may move you *away* from the
centre. Diagonal neighbours can never be captured.

```
Figure 2 (5 × 4)   Y = the black stone to move
   . g . . .       g = a white stone Y CAN capture (all four are orthogonal)
   g Y g . .       r = a white stone Y CANNOT capture (it is diagonal)
   . g r . .
   . . . . .       Two of the four legal captures move Y strictly AWAY from
                   the centre, and a third leaves its distance unchanged.
```

### Non-capturing moves

Move onto an **orthogonally adjacent EMPTY pit that is STRICTLY CLOSER to a
centre pit**. "No farther" is not enough — the distance must go down.
A stone standing **on** a centre pit therefore has no non-capturing move at all;
it can only capture.

```
Figure 3 (5 × 4)   Y = a black stone to move (two are shown)
   O . . . r       g = an empty pit Y MAY move to
   . . . g Y       r = an empty pit Y MAY NOT move to
   . g . . r
   r Y g . .       The centre pits are the two middle pits of column 3.
                   Top Y is at distance 2; its left neighbour is at 1 (legal),
                   the pit above at 3 and the pit below at 2 — both refused,
                   the second because EQUAL is not CLOSER.
```

### The pie rule

Invector uses the **pie rule**. On **White's first turn only**, White may — instead
of moving a white stone — **switch colours and become Black**, claiming Black's
opening move as his own. The position on the board is untouched; only who owns
which colour changes, and the turn then passes to the other player, who is now
White. In the app this appears as a **"Swap colours (pie rule)"** button, and the
board caption follows the exchange — after a swap the player who took the pie is
named **Black** for the rest of the game.

## Object of the game

> The goal is to capture all enemy stones. When you have removed all enemy stones
> from the board, you win.

There is no other way to end the game, and no draw is reachable.

## Notation

A move is written using the rendered board's own coordinates — file letters left
to right, rank numbers **upward from the bottom**. A capture uses `x`
(`d4xd5`), a non-capturing move uses `-` (`d4-d5`). The pie swap is logged as
`swap (pie)`.

---

## Ruleset choices made in this implementation

Everything below was checked against the official rule sheet
(`marksteeregames.com/Invector_rules.pdf`, md5 `74648185f2d914ea8c6c63c72e6a040e`,
ModDate 2026-05-20) and cross-checked against the independent AbstractPlay
`gameslib` implementation.

**Which revision of the sheet?** The live PDF is the third revision and has never
been archived — the Wayback Machine's newest capture (2026-04-19) predates it.
The two archived revisions were compared with the live one, text and parsed
figure geometry:

| Revision | ModDate | What changed |
|---|---|---|
| archived 2026-04-13 | 2026-04-10 | — |
| archived 2026-04-19 | 2026-04-15 | **the whole pie rule was added**, "starting with Black" was added, and Figure 2 gained the **red dot** on the diagonally adjacent white stone |
| **live** (this port) | **2026-05-20** | a typo only: "designed Invector in April 2006" → "2026". Figure geometry byte-identical to the 2026-04-15 revision |

So the rules implemented here are the 2026-04-15 ruleset, which is the current
one; anyone working from the older archived sheet would ship Invector **without
a pie rule**.

1. **Board family.** The sheet allows *any* rectangle with one even and one odd
   dimension and illustrates a 5 × 4. Rather than expose two independent
   dimensions, this package offers the **W × (W−1)** family with W even — the
   same family, and the same **8 × 7** default, as `gameslib`. (Figure 1's 5 × 4
   is that same shape turned on its side; the rules are symmetric in the two
   axes, which `selftest.py` asserts by transposing Figure 3 and getting the
   transposed answer.) The extra **4 × 3** size is offered because it is small
   enough to solve exhaustively; `gameslib` does not list it.

2. **Checkerboard orientation.** Figure 1 puts a **black stone on the top-left
   pit**. On an even-width, odd-height board the *vertical* mirror preserves the
   checkerboard parity — a genuine symmetry that no test could detect — while the
   *horizontal* mirror flips it and would effectively hand Black the other
   colour. So "top-left is Black" is exactly the half of the symmetry group that
   has to be pinned from the printed figure, and it is asserted for every size.

3. **Which two pits are the centre pits.** Implemented as *the pits nearest the
   board's geometric centre* — one even dimension and one odd dimension give
   exactly two of them, orthogonally adjacent. Figure 3 prints the **complete**
   set of legal and illegal non-capturing destinations for two black stones, and
   `selftest.py` **measures how much that figure actually settles** rather than
   assuming it settles everything: of eleven named candidate definitions it kills
   **eight** (including both axis-swapped pairs, "all four middle pits", the
   corner pits, the Chebyshev metric and "no farther" instead of "strictly
   closer"), and of all **6,195** subsets of the 5 × 4 board of size ≤ 4 it kills
   **6,022**. The survivors are dealt with explicitly:
   - *an asymmetric single centre pit* — excluded by the sheet's own bracketed
     "[There are two center pits.]" and by the requirement that the rule be
     invariant under the board's reflections (neither player has a distinguished
     side). Figure 3 **plus** that invariance leave **exactly one** of the 6,195
     candidates standing, and it is the one implemented.
   - *the Euclidean metric* — not a wrong variant at all: for the single
     orthogonal steps this game makes, Euclidean and Manhattan are proved
     behaviourally identical (0 disagreements over every step of ten boards).

4. **"Manhattan distance", not a path around obstacles.** The sheet glosses the
   distance as "via a series of orthogonally adjacent pits", which could be read
   as a shortest path through *unoccupied* pits. It is not: the same sentence
   says "Manhattan distance", the pits themselves are never removed, and the
   `gameslib` differential (plain Manhattan) matches this package over thousands
   of positions. Figure 3 alone **cannot** tell the two readings apart — all six
   of its dots agree under both — and `selftest.py` records that gap explicitly
   instead of assuming the figure covers it.

5. **Captures are not subject to the centre rule.** "You can move to capture an
   orthogonally adjacent enemy stone **in any direction**." Figure 2 proves it:
   two of the four marked captures move the stone strictly away from the centre
   and a third leaves its distance unchanged.

6. **The skip rule is real, and it fires.** A player whose stones are all either
   on centre pits or hemmed in by friends, with no adjacent enemy, has no legal
   move; his turn is skipped and the opponent moves again. This is implemented
   inside `apply_move` (the platform requires a non-terminal position to offer at
   least one move), it is *not* a pass — nothing is added to the move log — and it
   happens in ordinary play at every board size.

7. **Both players stuck at once is IMPOSSIBLE — proved, not defended.** Such a
   position would freeze the game forever, so it matters. Let *m* be the smallest
   distance-to-centre among all stones. If *m* > 0, the stone attaining it has a
   neighbour one step closer to a centre pit; that neighbour cannot hold a stone
   (its distance would be smaller than *m*), so it is empty and that stone can
   move. If *m* = 0, some stone stands on a centre pit; the other player's
   closest stone either has an empty closer neighbour, or that neighbour holds a
   stone nearer the centre than any of his own — necessarily an enemy, i.e. a
   capture — unless he *too* stands on a centre pit, and the two centre pits are
   adjacent, so those two stones capture each other. Every case gives somebody a
   move. Random play can never demonstrate this, so `selftest.py` verifies it
   **exhaustively on 523,852 constructed boards** over two small grids. The
   engine still scores a hypothetical double-stuck position as an honest **draw**
   rather than inventing a winner for it.

8. **Termination: no ply cap, no repetition rule.** Let *N* be the number of
   stones on the board and *D* the sum over all stones of their distance to the
   centre. A **capture** removes the victim, which stood on the destination, so
   *N* drops by one and *D* changes by exactly −*d*(from) ≤ 0 — a capture can
   never *raise* the distance sum. A **non-capturing move** leaves *N* alone and
   drops *D* by exactly one. So (*N*, *D*) strictly decreases lexicographically
   on every ply, and the game cannot loop or repeat a position. Counting gives at
   most *W·H − 1* captures, at most *D₀* quiet plies (*D₀* = the full board's
   distance sum), plus the one optional pie ply — the bound in the table above,
   computed in code by `max_plies(w, h)` from the board dimensions and asserted
   on random play at every size; it is never a pinned constant, and the engine
   itself never consults it. Real games are far shorter: over 2,000 uniform-random
   games on the standard 8 × 7 board the length ran **80–138 plies** (mean 107,
   5th–95th percentile 94–120) against a proven bound of 236.

9. **A genuine tie is a draw.** There is no tiebreak anywhere. The only
   non-decisive outcome is the unreachable double-stuck position, which scores
   0–0. Conversely, the capture that removes the last enemy stone usually leaves
   the winner with no legal move either — the **decisive result outranks** that,
   and is asserted to.

10. **The pie swap is a move.** It appears in the legal-move list as `swap`,
    **only** when exactly one ply has been played, and it is implemented as an
    exchange of colours with the position untouched. Because Invector is
    decisive, a correct pie rule must hand the win to the *second* player — he
    simply takes whichever side is winning. On the tiny 2 × 5 board this is
    verifiable end to end: **without** the pie that board is a *first*-player win,
    and **with** it a *second*-player win.

11. **Exhaustive solves.** Through the shipped `Game` API, with an on-stack
    repetition check that proves the game graph acyclic directly rather than
    inferring it from "the search finished":

    | Board | states | leaves | draws | value |
    |---|---:|---:|---:|---|
    | 2 × 3 (and its transpose 3 × 2) | 325 | 30 | 0 | second player |
    | 2 × 5, no pie | 22,920 | 475 | 0 | **first** player |
    | 2 × 5, with pie | 32,903 | 594 | 0 | second player |
    | 4 × 3, with pie (one-time, 78 s) | 376,393 | 2,696 | 0 | second player |
    | 4 × 3, no pie (one-time, 60 s) | 273,378 | 2,200 | 0 | second player |

    Zero draws and zero no-move leaves anywhere; the longest 4 × 3 line is 18
    plies against a bound of 26. The three tiny boards in the first rows are
    re-solved by `selftest.py` on every run; the 4 × 3 pair is a one-time offline
    result, frozen here.

12. **Verified against `gameslib`.** Board contents, legal-move target sets and
    the final result were compared ply by ply against AbstractPlay's independent
    implementation over **3,514 positions in 38 complete games** at five board
    sizes (4 × 3 through 12 × 11), with our engine choosing the move on even
    plies and the oracle on odd plies (so the oracle must also *reject* moves it
    thinks illegal), and with the coordinate map checked on every ply by
    comparing the whole board. **No mismatches.** Two areas the oracle
    structurally cannot cover were tested here instead:
    - it implements the **pie rule** as a UI-level flag outside the game class,
      so the swap gets zero differential coverage (a run in which White takes the
      pie and the colour map is inverted for the rest of the game was added
      anyway, and also matched);
    - its `checkEOG` only counts stones, so it has **no notion of "nobody can
      move"** — a double-stuck position would leave it passing forever. That
      case is excluded by the proof in note 7, not by the differential.

    `gameslib` expresses the skipped turn as an explicit `pass` move rather than
    as a skip; this is the same rule (the differential plays its `pass` wherever
    this package skips, and the two stay in step). Reading its code, its
    `validateMove("pass")` does accept a pass exactly when `moves()` offers one —
    it is not the dead-code case found in `minefield.ts` last wave.

13. **No bot evaluation is shipped, and that is a measurement, not an
    omission.** The obvious eval for an annihilation game — the normalised
    material balance *(mine − yours) / (all stones)*, which even agrees exactly
    with the true payoff at a terminal position — was implemented and measured
    *through `MCTSBot`*, the consumer that would use it, against the generic
    constant-zero fallback: same search budget, seats alternated, on the standard
    8 × 7 board where the rollout cutoff genuinely fires. Over **120 games** it
    scored **61–59 (50.8%)** — three independent batches of 40 went 25–15,
    19–21 and 17–23, i.e. indistinguishable from no eval at all. So the package
    ships no `heuristic`, and `selftest.py` asserts that none is present. If one
    is ever added it must be measured the same way; a directionally sensible
    eval is not automatically a stronger bot.

## How this is *not* Kōnane, and not Narrows

The library already contains **Kōnane** (which Invector's design notes name as its
inspiration) and **Narrows**, Mark Steere's other 2026 Kōnane-board game. All
three share a board and a checkerboard setup and nothing else that decides a game.

| | Kōnane | Narrows | Invector |
|---|---|---|---|
| Opening | two stones are **removed** | board stays **full** | board stays **full** |
| Move | **jump** an adjacent enemy into the empty pit beyond, chaining | **slide** onto the first enemy in line of sight, any distance | step onto an **adjacent** enemy, **or** onto an adjacent empty pit closer to the centre |
| Every move a capture? | yes | yes | **no** — quiet moves exist |
| Goal | last player able to **capture** wins | **link** all your own stones through open water | **annihilate** the enemy army |
| No legal move | you **lose** | cannot happen | your turn is **skipped** |
| Pie rule | no | yes | yes |
| Draws | none | none reachable | none reachable |

Kōnane is a normal-play game about mobility; Narrows is a connection game; only
Invector is decided by pure extermination, and only Invector has a geometry — the
pull toward the two centre pits — that makes a stone's *position* on the board a
resource it can spend.
