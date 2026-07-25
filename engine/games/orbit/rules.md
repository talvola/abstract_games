# Orbit

**Steven Meyers, 2000.** A Go-like territory game with no liberties, no
capture-by-suffocation and no *ko*. Everything turns on **encirclement**:

> *"Half-orbits prohibit, orbits capture and prohibit."*

Orbit is really a family of 29 related games; this package implements the one the
designer made standard, **Half-Prohibition Orbit**.

## The board and a turn

1. Two players, Black and White, on a **16×16 board — stones go on the points**,
   as in Go. (9×9, 11×11 and 13×13 are offered as options.) The board starts empty.
2. **Black moves first.** On your turn you either **place one stone of your colour
   on an empty point** (subject to prohibition, below) or **pass**.
3. Stones never move. They can be captured, and some are removed automatically
   when the game ends.

## Connection, half-orbits and orbits

4. Two stones are **connected** if they are **orthogonally *or* diagonally**
   adjacent. A **connected group** is a maximal set of same-coloured stones linked
   through such adjacencies.
5. A **half-orbit** is a connected group which, **together with one side of the
   board**, completely encircles one or more points. A corner point belongs to
   *both* of the sides that meet there.
6. An **orbit** is a connected group that completely encircles one or more points
   on its own.
7. **Forming a half-orbit captures nothing**, but from then on the **opponent may
   never play inside that formation**. **Forming an orbit captures every opposing
   stone inside it** *and* likewise prohibits the opponent from playing there.
   Captured stones are simply returned to their owner and score nothing.
8. You may always play inside **your own** formations — prohibition is one-way.
   Prohibition is a live property of the current position: if the enclosing wall
   is later broken, the formation is destroyed and the points are free again.
9. **You may not "mirror" the opponent's moves ten or more turns in succession**
   (rule 5 on the designer's rules page — it stops the copycat strategy on an
   even board).

## Opening balance

10. **Pie rule** (default): after Black's first move, White may play **Swap**
    instead of a stone, taking over Black's position; the other player then moves
    as White.
11. The designer's site specifies a **refined pie rule**, offered as an option:
    Player 1 plays the first three plies himself — **Black, White, Black** — and
    Player 2 then chooses which colour to take, **with White to move**. (Passing
    is allowed in those plies, which is how the plain pie rule is reproduced;
    passes inside this setup phase do not end the game.)

## End of the game and scoring

12. When **both players pass consecutively** the game is over. Stones that cannot
    avoid capture are then removed automatically.
13. Your **score is your territory**: the number of **vacant** points inside your
    own orbits and half-orbits. Your own stones do not count and captured stones
    do not count.
14. **Shared territory** — vacant points lying inside **both** players'
    formations, where neither player is allowed to play — counts for **neither**
    player. Points inside nobody's formation (*dame*) also count for nobody.
15. The higher score wins. **An exact tie is a draw.**

## Implementation notes / interpretations

* **The enclosure test.** Take the complement of a player's stones (every empty
  point plus every enemy stone) and split it into **4-connected** components —
  4-connectivity of the enclosed region is the exact dual of the 8-connectivity of
  the enclosing wall, so a component is sealed precisely when no 4-step path
  escapes off the board. OR together the board-edge memberships of the
  component's points:
  * **no edge point at all** → an **orbit**;
  * **exactly one side** → a **half-orbit**;
  * **two or more sides** → nothing. Sealing such a region would need two sides —
    that is a *quarter-orbit*, which exists in other members of the Orbit family
    but **not** in the standard game. In particular a **bare corner point is never
    enclosed**: it belongs to both of the sides meeting there. (Confirmed by
    Diagram 5 on the designer's rules page, where the corner P1 — walled in by
    White stones at O1 and P2 — is marked neutral, and by the published score.)
* **Why testing the complement of *all* your stones is faithful to "a connected
  group".** Rule 5 defines a formation as *a connected group* which (with one
  side) encircles points, whereas the test above works on components of the
  complement of **all** of a player's stones at once. The two are equivalent, and
  deliberately so: extra stones of your own sitting inside your own formation can
  only *shrink* a complement component, and a shrinking component's side-mask can
  only lose bits, never gain them — so they can never open a sealed region, nor
  seal an open one. This is checked by differential test in `selftest.py`
  (per-group evaluation vs. the shipped test agree on all eight published diagrams
  and on thousands of random positions), so the cheap formulation is used.
* **What counts as "mirroring" (rule 9).** The designer's rule 5 does not define
  the word; it exists to stop the copycat strategy, which on an even board with
  no centre point is *central symmetry*. So a move counts as mirroring when it is
  the **180° point reflection** of the opponent's immediately preceding
  **placement** — `(c, r) → (W−1−c, H−1−r)`. The counter is per player; the tenth
  successive mirror is the illegal one (nine in a row is fine), only the mirroring
  player is restricted, and any non-mirroring move — including a pass by either
  side, which breaks the succession — resets it to zero.
* **No self-capture.** A player's enclosure map depends only on his *own* stones,
  so adding a stone can never capture your own — and never changes what the
  opponent is forbidden to do either.
* **Automatic removal at the end (rule 12) is made deterministic.** There is no
  negotiation here, so: each player is assumed to fill every vacant point of the
  regions he encloses *exclusively* (the opponent is prohibited there and can
  never interfere), and the orbit captures that result are applied. Both players'
  removals are computed from the same snapshot, so the outcome does not depend on
  whose turn it is, and the process repeats until nothing more dies. This is a
  purely local test — it does **not** search whether the enclosing wall could
  itself be killed. It reproduces both of the designer's published scored
  positions exactly (see `selftest.py`).
* **Running score.** The board caption shows the score the position would have if
  both players passed right now (i.e. after that automatic removal), and tints the
  vacant points each player currently encloses, with shared territory in grey.
* **Termination.** The game also stops at a hard cap of `3 × width × height`
  plies and is scored normally; this only exists so that random play is guaranteed
  to terminate — real games end by double pass long before it (random 16×16 games
  average ~280 plies).

## Sources

* *Abstract Games* magazine, **issue 12 (Winter 2002), pp. 21–23** — "Orbit: A new
  game of territory" by Steven Meyers, with Diagrams 1–3 (puzzle solution p. 29).
* Steven Meyers' own rules page, `home.fuse.net/swmeyers/orru.htm` (now only on
  the Internet Archive) — the fuller statement of the rules, source for the
  anti-mirroring rule, the refined pie rule and two published scored positions.
