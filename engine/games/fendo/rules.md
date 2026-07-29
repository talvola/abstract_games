# Fendo

**Dieter Stein, 2014** — *"Create boundaries, divide areas, occupy squares."*
Two players, no chance, no hidden information. These are the rules **as
implemented** in this package; the official rules are at
[spielstein.com/games/fendo/rules](https://spielstein.com/games/fendo/rules).

## Material

- A **7×7** board (49 cells).
- **7 pieces** per player — Red is seat 0, Blue is seat 1.
- A supply of **fences**, which belong to neither player — either player may build
  any fence. A fence sits on the single edge **between two orthogonally adjacent
  cells** and blocks movement across it. The outer rim of the board is already a
  solid boundary.

The physical game ships "about 50" sticks; that is a component count, not a rule,
so no limit is enforced here (a 7×7 board has only 84 internal edges, and the
longest of 2,000 uniform-random games used 49).

## Setup

Each player puts one piece on the middle cell of their own side — **Red on a4**
(the left edge, `0,3`) and **Blue on g4** (the right edge, `6,3`). The other six
pieces of each colour wait in stock, shown in the reserve tray. **Red moves
first.**

## Areas

An **area** is a set of cells joined by edges that no fence blocks. Areas are
classified purely by how many pieces stand in them:

| pieces in the area | name | scores |
|---|---|---|
| exactly 1 | **closed** — owned by that piece's owner | its whole size, to that owner |
| 2 or more | **open** | nothing |
| 0 | **empty** | nothing (and see below — these can never be created) |

At the start the entire board is one open area (it holds both starting pieces).
Closed areas are shaded in their owner's colour on the board.

## Your turn — exactly one of two actions

### (a) Select a piece and build a fence

Pick one of your own pieces **that is in the open area** (a piece in a closed
area is finished — it can never act again).

The piece **may** then move. It slides in a straight horizontal or vertical line,
any distance, **and may change direction once, at a right angle**. It may not
pass over or land on another piece, and may not cross a fence. Standing still is
always allowed.

Then a fence **must** be built on one of the **empty sides** of the cell the piece
ends on — a side that is neither the board rim nor already fenced.

**The fence restriction.** After the fence is placed, every enclosed area must
contain **exactly one piece** (of either colour). Concretely, a fence is illegal
if it would

- create an **empty** area (no pieces), or
- leave **more than one open** area (i.e. split the open area into two parts that
  each still hold 2+ pieces).

Because a fence is compulsory, **a piece cannot be selected at all — nor moved to
a given cell — unless some legal fence exists there.** A piece with no legal fence
on its own square and no reachable square offering one simply cannot be played
(this is Example 2 in the designer's rules).

### (b) Add a piece

Place a piece from your stock on an **empty cell that is exactly one move away**
(as defined in (a): straight line or one right-angle turn, nothing in the way)
from one of **your** pieces in the open area. **No fence is built.**

### Passing

A player with no legal action must **pass**.

## End of the game and scoring

The game ends the instant **no open area remains** — every area then holds exactly
one piece. Players may still have pieces in stock; that is fine.

Each player scores the **total number of cells** in all areas they own. The
higher total wins. Since the fence rule forbids empty areas, the 49 cells are
fully partitioned among closed areas at that moment, so the two scores sum to 49
and **the normal ending can never be tied**.

**The one tie-able ending.** If both players pass in succession, the game also
ends (this is the AbstractPlay reference implementation's rule, adopted here to
guarantee termination — the designer's text only says a player with no action
passes). Then the open area still exists, its cells score for nobody, and the two
totals *can* be equal. A tie is scored as an **honest draw** (`winner = None`,
returns `[0, 0]`) — no tiebreak is invented. Single passes are common (they
happened in 1,263 of 2,000 uniform-random games, once a player's pieces were all
sealed in), but **two in a row never occurred** in any of the ~6,000 random and
adversarially-steered games played across development and review — a 3,000-game
uniform sample alone contained 12,171 single passes and no double pass, and
neither did 460 games under a policy that deliberately steers toward positions
where the mover has nothing to do (a further 611 single passes); every one of
them ended with the open area carved away, and none was a draw. There is also a
partial structural reason: while the open area holds exactly **two** pieces,
their owner always has a legal action — fencing the edge that leads toward the
other piece either leaves the area connected or splits it 1-and-1 — so a double
pass needs at least three pieces in the open area, both stocks empty, and every
one of those pieces stuck. The double-pass ending is a safety net, not a
practical outcome.

## Move notation used by this package

| move string | meaning |
|---|---|
| `c1,r1>c2,r2=FENCE_N` | slide the piece from `c1,r1` to `c2,r2`, then fence the **north** side of `c2,r2` |
| `c,r>c,r=FENCE_E` | leave the piece on `c,r` (a zero-length slide), fence its **east** side |
| `P@c,r` | enter a piece from stock onto `c,r` |
| `pass` | no action available |

A fence move is **always** a two-cell path, even when the piece does not move —
`from>from` is the stay-put form. This is deliberate and load-bearing for the web
UI: the click-router matches a *complete* move before it tries to extend a path,
so a one-cell `c,r=FENCE_D` would be consumed by the very click that is meant to
**select** the piece, and move-then-fence could never be played (the fence picker
would pop up, or a stationary fence would fire, the moment you touched a piece).
A **bare** `c,r` is never a legal move either — entering a piece from stock rides
the reserve/drop channel (`P@c,r`) so that the two cannot collide.

`FENCE_N` / `FENCE_S` / `FENCE_E` / `FENCE_W` name the side of the piece's **final**
cell. In the web UI you click the piece (it highlights, and so do its legal
destinations **plus its own square**), then click where it goes — clicking the
piece again means "stay here" — and finally pick which side the fence goes on from
the chooser. To enter a piece from stock you click your reserve chip and then a
highlighted cell. The move log uses the designer's algebraic names:
`b3-b6, fence N` = slide b3→b6 and fence its north side; `d5 stays, fence E` =
stand still on d5 and fence its east side; `enter d5` = enter a piece on d5.

**Cell ids.** `"c,r"` with `c` = file `a`…`g` = 0…6 and `r` = rank 1…7 = 0…6, so
`a4` is `0,3` and `g4` is `6,3`.

## Interpretations and sourcing

Everything below was resolved from the designer's rules page and cross-checked
move-for-move against the AbstractPlay `gameslib` reference implementation
(MIT-licensed; used here purely as a rule-enforcing oracle — no code was copied).
Two of the designer's own worked diagrams are additionally reproduced as
assertions in `selftest.py` — the *placement* picture (all 21 marked entry cells)
and *Example 2* (the piece with no legal action) — so the two most interpretable
rules are anchored on Dieter Stein's pictures and not only on someone else's
code.

1. **Starting cells.** The designer says "the center space on their side"; the
   reference implementation puts them on **a4 and g4**, i.e. the two players face
   each other across the *files*. Adopted.
2. **"Exactly one move away"** for entering a piece means the same slide as in
   action (a) — including the one right-angle turn — and the source piece must be
   in the open area. It does **not** mean "one step".
3. **A piece may stay put** and still build a fence (the designer's move is
   explicitly optional: "This piece *may* now be moved").
4. **The fence goes on the final cell only**, never on a cell passed through.
5. **The legality test is global**: after the fence, *no* area anywhere may be
   empty and *at most one* may be open. It is not restricted to the area just
   split off.
6. **Empty areas score nothing** and, given rule 5, cannot exist; the code still
   scores them as nobody's, so it stays correct if a position is ever loaded that
   contains one.
7. **Handicap** (the stronger player takes only 6 or 5 pieces) is described in the
   designer's rules but is deliberately **not implemented** — it is a rating
   device rather than a rule, and the reference implementation has no such
   variant to check it against.
8. **Termination.** Every non-pass move either lays a permanent fence (at most
   84 internal edges exist on a 7×7 board) or spends a piece from stock (at most
   12), and two passes in a row end the game — so no game can exceed 193 plies.
   No artificial ply cap is used or needed. Uniform-random games in fact run
   7–90 plies (2,000-game sample; longest observed 90).

## Why this is not one of our other games

**Not Quoridor.** Quoridor is a *race*: each player has a pawn that must cross to
the far side, and its walls are two cells long, owned (ten each), and restricted
only by "you may not seal a pawn off entirely". Fendo has seven pieces a side,
unlimited shared one-cell fences, no destination at all, no path-preservation
rule, and it is scored by area rather than won by arrival. The only shared idea is
"barriers laid between cells".

**Not Domain.** Domain is polyomino placement with Othello-style flipping on a 9×9
grid; territory there is the tiles you own, not regions of the board, and there is
no movement. Fendo's pieces move, its boundaries are separate from its pieces, and
its score is the *size of the region each piece is sealed into*.

**Not a Go/territory clone either** — no captures, no eyes, and the enclosure is a
hard graph partition made of explicit fence objects rather than an inference about
influence. The characteristic Fendo decision (do I seal myself into a big room
now, or stay in the shrinking open area and keep fighting?) does not exist in any
other package in this library.
