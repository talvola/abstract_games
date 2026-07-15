# Cathedral

*The Strategy Game of the Medieval City* — **Robert P. Moore**, New Zealand, 1979.

Two factions raise buildings inside a walled city, claiming ground and walling
each other out. A neutral Cathedral, placed before play, mediates the struggle.

Rules below are **as implemented**, and follow the official rulesheet
(© 1978 Robert P. Moore, New Zealand Patent 190034), cross-checked against the
designer's site, [cathedral-game.co.nz](https://www.cathedral-game.co.nz/about-how-to-play.html).

## The city and the pieces

The board is a **10×10 grid enclosed by a wall** (the wall is the edge of the
grid, not extra squares). Each player has **14 buildings**, and there is one
neutral **Cathedral**:

| Building | Shape | Squares | Each player has |
|---|---|---|---|
| Tavern | single square | 1 | 2 |
| Stable | domino | 2 | 2 |
| Inn | L-tromino | 3 | 2 |
| Bridge | I-tromino (straight) | 3 | 1 |
| Manor | T-tetromino | 4 | 1 |
| Square | O-tetromino (2×2) | 4 | 1 |
| **Abbey** | S/Z-tetromino — **chiral** | 4 | 1 |
| Infirmary | X-pentomino (plus) | 5 | 1 |
| Castle | U-pentomino | 5 | 1 |
| Tower | W-pentomino (staircase) | 5 | 1 |
| **Academy** | F-pentomino — **chiral** | 5 | 1 |
| *Cathedral* | *6-square Latin cross* | *6* | *one, neutral* |

That is **47 squares each**, and `2 × 47 + 6 = 100` — the two players' buildings
plus the Cathedral tile the city **exactly**.

## Rotate, but never flip

A building may be **turned to any of its four rotations but NEVER flipped over**.
This is the rule that gives the game its bite, and it is why the **Abbey** and the
**Academy** are *chiral*: the two colours hold **mirror-image forms** of those two
pieces. Every other building is identical for both colours (its mirror image is
just one of its own rotations).

## Play

1. **Light places the Cathedral** anywhere in the city, lined up with the
   squares. This is a setup action, not a move.
2. **Dark then makes the first move**, and the players alternate. A move is
   placing one building, lined up with the squares, on empty squares — never in
   ground the opponent has claimed.

## Claiming ground (rule 4)

If you **completely enclose** part of the city **with your buildings alone, or
your buildings and the wall**, that part becomes your property and your opponent
may not build in it. You may still build in it yourself.

Buildings must meet **wall to wall** — *a corner-to-corner contact is not a
boundary*, and space merely pinched off at a corner point leaks back into the
city and is not claimed. (Implemented as the standard connectivity duality:
buildings bound edge-to-edge, so enclosed space is flood-filled including
diagonals — exactly the rulesheet's note 4.)

**You may not use the Cathedral as part of the boundary** of a claim. A Cathedral
that still borders open ground therefore walls nothing off — the pocket beside it
simply reaches the rest of the city *through* the Cathedral.

**Neither player may claim space on their first move.**

## Capturing (rule 5)

If your enclosure isolates **one and only one** enemy building **or the
Cathedral**, it is **removed** and you claim the space.

- A captured **building goes back to its owner's stock and may be replayed** later.
- The **Cathedral, once removed, is gone for the rest of the game.**
- If an enclosure holds **two or more** pieces (one of which may be the
  Cathedral), **none** may be removed and the space stays open to both players.
  So a building that *touches* the Cathedral is safe from capture, and so is the
  Cathedral — neither can be sealed off from the other.

## Ending and winning (rules 6-7)

The game ends when **neither** player can place. If one player is stuck, they
pass and the other keeps building until they too are stuck or run out.

The **winner** is the player who places all their buildings while the opponent
does not. Otherwise the player whose **unplaced buildings cover the fewest
squares** wins — and if those are **equal, the game is an honest draw**.

(Note: Wikipedia reports the fewest-squares tiebreak but drops the draw. The
draw is published in both the 1978 rulesheet and the designer's current rules,
and is implemented here.)

## Interpretations and notes

The rulesheet is short and a few points need a decision. Each choice below is
covered by `selftest.py`.

1. **"Your first move"** means your first *building* — the Cathedral placement is
   setup, since rule 3 says Dark "makes the first and each alternate move". This
   clause does real work: without it Dark's opening building would formally leave
   the Cathedral as the only piece in the single remaining region and so "isolate"
   it, carrying off the Cathedral and the whole board on move one.
2. **A claim missed on your first move takes effect from your second move on.**
   Territory is recomputed from the position rather than stored as a one-time
   event, so a pocket your opening building sealed becomes yours once you have
   played a second building — the opponent gets exactly one turn to use it.
3. **Your own buildings never count toward "two or more".** They form the
   *boundary* of an enclosure, not its contents; only enemy buildings and the
   Cathedral are counted. This matches rule 5's wording ("one and only one of
   *your opponent's* buildings or the Cathedral") and strategy tip D, which
   assumes your buildings can sit harmlessly in your own ground.
4. **Capture is automatic, not optional.** Rule 5 says you *may* remove the piece
   but must do so *immediately* or it stays. Taking the capture always resolves
   it at the moment of enclosure, which makes the position self-contained; a
   declined capture cannot then linger, because no enclosure of exactly one piece
   can survive the move that made it.
5. **One move may capture in two separate enclosures.** "Two or more" applies
   *within one* enclosure; two distinct pockets, each holding exactly one piece,
   each resolve.
6. **Light holds the Abbey and Academy as the rulesheet draws them; Dark holds
   the mirror images.** Only the *relative* handedness matters — reflecting the
   whole game is an isomorphism — so which colour gets which is arbitrary.
7. **Termination.** Every move places a building, so with no captures the game
   ends within 29 plies. Captures return buildings to stock, so play is not
   bounded by stock alone; a **200-ply cap** ends the game as a backstop, scored
   by the normal rule 7 comparison (not a fabricated result). Real play does not
   approach it — random games run about 25 plies.
8. **Not implemented:** rule 8's multi-game series scoring (each match is a
   single game), and the optional *Tom Lehmann* opening variant given on the
   designer's site (the second player places the Cathedral together with their
   first building).
