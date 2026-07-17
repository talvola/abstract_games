# Tâb

**Tâb** (Arabic *ṭāb*) is the running-fight dice-war game of Egypt and the
wider Middle East — the root game of the tâb/sîg/deleb family and a cousin of
the Nordic Daldøs and Sáhkku. This package implements the ruleset recorded by
**Edward William Lane in Cairo in the 1820s** (*An Account of the Manners and
Customs of the Modern Egyptians*, pp. 346–349 — the primary historical
description), cross-checked against Wikipedia "Tâb" and the Ludii DLP entry
(evidence: Lane 1836; Murray 1951: 95).

## Board and setup

- **4 rows** of squares (*beyts*), an odd number per row — **7, 9, 11, 13 or
  15** (board-size option; default **9**, the size of Lane's own worked
  diagram). Lane: "the beyts are usually seven, nine, eleven, thirteen, or
  fifteen, in each row."
- Each player fills their own **outer row** with one piece (*kelb*, "dog") per
  square. Red owns the bottom row, Blue the top.

## The stick dice and the throw chain

Four two-sided stick dice (flat/white vs round/black faces). The throw's value
is the number of **white faces up** — except that zero whites counts **6**:

| Whites up | 0 | 1 | 2 | 3 | 4 |
|-----------|---|---|---|---|---|
| Value | 6 (*sitteh*) | **1 (tâb)** | 2 | 3 | 4 |
| Throw again | yes | yes | no | no | yes |

A **1, 4 or 6 earns another throw**; a 2 or 3 ends the throwing. The whole
chain is thrown first and **banked**, then the values are spent **one at a
time, in any order, each on any one piece** — Lane's own example: having
"thrown tab (or one), and then four, and then two, he may take the kelb in *o*
by the throw of two; then, by the throw of four, take that in *s*; and, by the
throw of tab, pass into *a*". A value that can be used must be used; values
that cannot be used are forfeited (`pass` ends the turn, discarding whatever
remains in the bank).

## Conversion (Christians → Muslims)

Every piece starts as a dead **"Christian"**: it cannot move at all until a
**tâb** throw converts it to a **"Muslim"**, which also advances it **one
square**. One tâb converts one piece. Conversion proceeds **from the exit end
of the home row**: only the *foremost* unconverted piece may be converted
(Lane: "He must always commence with the kelb in beyt I"). A tâb may instead
be spent moving any Muslim one square.

## The track

All pieces of both players move through each row **in the same direction**
(boustrophedon). For Red (bottom row, moving left→right): along the home row,
out into the row above at its right end, right→left across it, then
left→right across the next row up — after which the two middle rows form an
**endless loop**. At the end of the second middle row (the highlighted
**branch square**) the piece may either continue the loop or — see below —
turn into the **enemy's home row**, crossing it against its owner's direction
and rejoining the loop at the far end. Blue's track is the 180° mirror.
**No piece ever returns to its own home row.**

### The enemy home row

- A piece may enter the enemy home row **only while at least one enemy piece
  remains in it** (Lane: "may then either repeat the same round or enter his
  adversary's row, as long as there is any kelb remaining in that row").
- Each piece may enter it **only once in the game**; afterwards it circulates
  the two middle rows forever.
- A piece inside the enemy home row is **frozen** — it cannot move at all —
  while **any of its owner's pieces remain in the owner's own home row**,
  *unless* the whole home-row force is united in a single stack (the *'eggeh*
  exception). It is otherwise a safe camp: enemy pieces that have left their
  home row can never come back to it.

## Capturing, stacks and reduction

- Landing exactly on a square holding **enemy pieces captures the whole
  pile** — they are removed from the game. Unconverted Christians can be
  captured where they sit (that is the point of raiding the enemy home row).
- Landing on your **own Muslim(s) unites** the pieces into a **stack**
  (*'eggeh*) that thereafter moves as one piece. A stack can only be
  **divided by a tâb**, which splits one kelb off it (moving it one square);
  landing on your own *unconverted* piece is not allowed.
- If a stack is moved **back into a row it has already passed through**
  (either half of the loop, or the rows its members crossed before uniting),
  it is **cut down to a single kelb** — the excess pieces leave the board.
  Such a move is never compulsory: when reduction moves are your only option
  you may `pass` instead (Lane: "he need not avail himself of such a throw").

## Winning

Capture **all** of the opponent's pieces to win. If no capture or conversion
occurs for a long stretch (500 plies) or the game exceeds a hard cap, it ends
as an honest **draw**.

## Sources & interpretations

Primary: **Lane (1836/1860), pp. 346–349** (verbatim, incl. his lettered board
diagram); secondary: **Wikipedia "Tâb"**, **Ludii DLP "Tab"** (Tab.lud, whose
track strings match Lane's diagram exactly), Murray 1951: 95 (cited by Ludii).
Contested/ambiguous points, resolved as follows:

- **Board size**: Lane attests 7–15 (odd); his worked example is 9 → default
  9 (Ludii's "described" default is 7 — offered as an option).
- **Conversion order**: Lane's "must always commence with the kelb in beyt I"
  is read as *foremost-Christian-first throughout* (the reading that
  generalises his sentence; matches the daldos/sáhkku family convention).
  Some readings apply it only to the very first conversion.
- **Throw protocol**: modelled as roll-the-whole-chain-then-spend (Lane
  describes throwing until a 2/3 and then distributing the values freely).
  Lane's ceremonial opening ("they first throw alternately until one has
  thrown tab") is emergent here: a turn whose chain contains no tâb converts
  nothing and passes.
- **The freeze**: Wikipedia reads Lane as "cannot move any further at all"
  (implemented); Ludii instead only forbids *leaving* the row. Lane's obscure
  rider "…or unless he have only an 'eggeh in his row, **and does not throw
  tab**" is implemented in Ludii's simplified form (a single united home-row
  stack lifts the freeze) without the throw-dependent clause.
- **Stack history**: Lane says reduction applies to rows passed "either
  separately or together", so a stack's visited-rows are the **union** of its
  members' histories; a split-off kelb and a reduction survivor inherit the
  stack's history (including the used-up enemy-row entry).
- **Landing on an own Christian** is disallowed (Lane is silent; an 'eggeh is
  a union of *converted* pieces).
- Lane's four-player/forfeits variant (Sultan, Wezeer, foot-whipping) and the
  reduced-piece-count setups are not implemented.
