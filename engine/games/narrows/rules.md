# Narrows

**Mark Steere, May 2026.** A two-player game of rook captures on a Kōnane board,
where the goal is not to capture but to open **channels** — you win the moment
every one of your stones can reach every other one through open water.

## Board and setup

A rectangular grid of pits, one stone per pit, **completely filled** at the start
with a checkerboard of black and white stones. The rule sheet allows any size
**with at least one even dimension**; this package offers the family
**W × (W−1)** with W even, so the width is always the even dimension:

| Option | Board | Stones each | Opening moves |
|---:|---|---:|---:|
| 4 | 4 × 3 | 6 | 17 |
| 6 | 6 × 5 | 15 | 49 |
| 8 | 8 × 7 | 28 | 97 |
| 10 | 10 × 9 | 45 | 161 |
| **12** | **12 × 11 (standard)** | **66** | **241** |
| 14 | 14 × 13 | 91 | 337 |
| 16 | 16 × 15 | 120 | 449 |

The **top-left pit holds a Black stone** and the colours alternate from there,
exactly as Figure 1 of the rule sheet draws it. **Black moves first.**

```
Figure 1 (5 × 4)      X = Black   O = White
   X O X O X
   O X O X O
   X O X O X
   O X O X O
```

## Playing a turn

Move **one stone of your own colour**. **Passing is not allowed**, and every move
is a capture.

### Rook captures

Slide one of your stones orthogonally (up, down, left or right) onto **the first
enemy stone that stone can see** in that direction — the enemy stone is either
**adjacent** to yours, or **separated from it only by empty points**. The enemy
stone is removed and yours takes its place (**capture by replacement**). A stone
of *either* colour standing in the way blocks the ray, and you may never land on
an empty point or on a friendly stone.

```
Figure 2 (5 × 4)   the marked black stone (Y) can capture the three marked whites (g)
   X X . O X
   g Y . . g          west: adjacent      east: across two empty points
   X g O X X          south: adjacent     north: blocked by a friendly stone
   . O O X O
```

Every move therefore removes **exactly one enemy stone** and never adds one.

### The pie rule

Narrows uses the **pie rule**. On **White's first turn only**, White may — instead
of moving a white stone — **switch colours and become Black**, claiming Black's
opening move as his own. The position on the board is untouched; only who owns
which colour changes, and the turn then passes to the other player, who is now
White. In the app this appears as a **"Swap colours (pie rule)"** button, and the
board caption follows the exchange — after a swap the player who took the pie is
named **Black** for the rest of the game.

## Object of the game

> All of your stones must be linked to all of your other stones via orthogonally
> interconnected paths of **unoccupied points and/or friendly stones**.

Equivalently: delete every *enemy* stone from the board; in what remains — empty
points and your own stones — **all of your stones must lie in one connected
region**. Think of your islands as being joined by open water; the *narrows* are
the thin channels that do the joining.

```
Figure 3 (5 × 4)   Black has won.  * = the empty points that do the linking
   X O O * X
   X * * X O          Every black stone reaches every other one through
   X O O X .          empty points and friendly stones.  White does not:
   O X X * O          his stones fall into three separate regions.
```

The point marked `.` in Figure 3 is empty and touches Black's region, but it
links nothing — the rule sheet leaves it undotted for exactly that reason.

**You can win on your turn or on your opponent's turn.** After every move both
players are checked. If the move links **only one** player, that player wins —
even if it was the *opponent* who moved. If a single move links **both** players
at once, **the player who made the move wins**.

A player holding just one stone is trivially linked, so the game always ends well
before the board empties.

## Notation

A move is written `from` `x` `to` using the rendered board's own coordinates —
file letters left to right, rank numbers **upward from the bottom** — so
`b2xb5` means "the stone on b2 slides up the b-file and takes the stone on b5".
The pie swap is logged as `swap (pie)`.

---

## Ruleset choices made in this implementation

Everything below was checked against the official rule sheet
(`marksteeregames.com/Narrows_rules.pdf`) and cross-checked against the
independent AbstractPlay `gameslib` implementation, which this package matches
move-for-move over thousands of plies at every board size.

1. **Board family.** The sheet allows *any* rectangle with at least one even
   dimension and illustrates a 5 × 4. Rather than expose two independent
   dimensions, this package offers the **W × (W−1)** family with W even (the
   same family, and the same **12 × 11** default, as `gameslib`). The parity
   requirement is therefore satisfied structurally and cannot be violated by an
   option. The extra **4 × 3** size is not in `gameslib`; it is offered because
   it is small enough to solve exhaustively (see below), and it is legal under
   the sheet.

2. **Checkerboard orientation.** Figure 1 puts a **black stone on the top-left
   pit**. That single datum is what fixes the colouring: on a board of even width
   and odd height, mirroring **vertically** leaves the checkerboard parity
   unchanged (a genuine symmetry that no test could detect), while mirroring
   **horizontally** flips it and would effectively hand Black the other colour.
   The convention is asserted for every board size in `selftest.py`.

3. **The pie swap is a move.** It appears in the legal-move list as `swap`,
   **only** when exactly one ply has been played, and it is implemented as an
   exchange of colours with the position untouched: after it, the player who
   swapped owns the stones that opened the game, the other player is on move as
   White, and every group is exactly where it was. On the 4 × 3 board this is
   verifiable end to end — **without** the pie rule that board is a *first*-player
   win, and **with** it a *second*-player win, which is precisely the effect a
   correctly implemented pie rule must have.

4. **The win condition, stated as a graph property.** "All of your groups linked
   together by empty regions" is implemented as: the subgraph induced on
   *(empty points) ∪ (your stones)* has **exactly one** connected component that
   contains a stone of yours. This is the sheet's own bracketed restatement, and
   it reproduces Figure 3 exactly (Black: one region; White: three).

5. **A player with no stones has not won.** The definition above gives a
   stoneless player *zero* groups, not one, so he does not win by having nothing
   left to link — the same reading `gameslib` takes. The case is in any event
   **unreachable**: reaching zero stones would require the opponent to be down to
   one stone first, and one stone is trivially linked, so the game ended a move
   earlier. Asserted over random play at three board sizes and over the entire
   4 × 3 solve.

6. **"No capture available" cannot happen** — this is proved, not defended, and
   the sheet needs no rule for it. You have no capture *if and only if* no row and
   no column holds stones of both colours (a line holding both must somewhere have
   two consecutive stones of opposite colour, and those two capture each other).
   But if every row and column is monochromatic, then each player occupies a set
   of rows and columns disjoint from the other's, so any two of his stones are
   joined by travelling down one stone's column and then along the other's row —
   every pit on that route is empty or friendly. Both players would already be
   linked, so the game ended on the previous move. Because random play can never
   reach such a position, `selftest.py` verifies it **exhaustively on 551,853
   constructed boards** over three small grids. The engine still scores a
   hypothetical no-move position as an honest **draw** rather than inventing a
   winner for it.

7. **Termination: no ply cap, no repetition rule.** Every capture removes exactly
   one enemy stone and nothing is ever put back, so no position can repeat and the
   stone count strictly decreases. Starting from *m = W·H/2* stones each, the
   counts run (m, m) → (m, m−1) → (m−1, m−1) → …, and the game is over the moment
   either count reaches 1; that first happens after **W·H − 3** captures, so a
   game lasts at most **W·H − 2** plies including the one optional pie ply. The
   bound is computed in code from the board dimensions (`max_plies(w, h)`) and
   asserted on random play at every size — it is never a pinned constant. Real
   games are far shorter: over 5,000 uniform-random games on the standard 12 × 11
   board the length ran **34–94 plies** (mean 59, 5th–95th percentile 47–75),
   against a proven bound of 130.

8. **A genuine tie is a draw.** There is no tiebreak anywhere. The only outcome
   that is not a win for one side is the unreachable no-capture position, which
   scores 0–0.

9. **The dotted "narrows".** When the game ends, the app marks the empty points
   whose removal would split the winner's stones apart. On Figure 3 this
   reproduces the sheet's four blue dots exactly (and, correctly, leaves the fifth
   empty point unmarked). It is a **display aid with no effect on play**.

## How this is *not* Kōnane

The library already contains **Kōnane**, which Narrows is explicitly inspired by
and which shares only its board and its checkerboard setup. Everything that
decides a game is different:

| | Kōnane | Narrows |
|---|---|---|
| Opening | two stones are **removed** to make room | the board stays **full**; the first move is a capture |
| Capture | **jump** an *adjacent* enemy into the empty pit beyond, chaining in a straight line | **slide** onto the first enemy stone in line of sight, at **any** distance across empty points |
| Stones removed per turn | one **or more** (a chain) | exactly **one** |
| Goal | **last player able to move wins** (normal play) | **link all of your own stones** through empty points and friendly stones |
| Winning on the opponent's turn | impossible | **yes** — the opponent's move can link you |
| Pie rule | no | **yes** |
| Draws | none | none reachable |

In Kōnane you want your opponent to run out of moves; in Narrows nobody ever runs
out of moves, and you want the board carved into channels.
