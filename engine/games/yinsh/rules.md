# YINSH

YINSH is the fifth game in Kris Burm's GIPF project. Two players each control
**5 rings** and share a common supply of two-sided (white/black) **markers**.
The goal is to be the first to **remove three of your own rings** from the board.

## The board (verified geometry)

The board is a hexagonal lattice of **85 intersection points**, shaped like a
truncated six-pointed star. A point is a lattice coordinate `(x, y)` with
`x, y in [-5, 5]` satisfying

```
(0.5 * sqrt(3) * x)^2 + (0.5 * x - y)^2 <= 4.6^2
```

This yields exactly **85 points**, arranged in eleven columns of length
**4, 7, 8, 9, 10, 9, 10, 9, 8, 7, 4** (the canonical YINSH board). Points are
addressed in move notation by their coordinate id `"x,y"`.

Points are connected by **three families of lines** (the triangular grid):

- constant `x`  — vertical step `(0, ±1)`
- constant `y`  — step `(±1, 0)`
- constant `x − y` — step `(±1, ±1)`

A ring or a row of markers always lies along one of these three directions.

## Pieces

Each player has **5 rings** (rendered as hollow rings in the player's colour).
Markers are a shared supply rendered as small filled discs in the colour of
whoever currently owns that face. A marker inside a ring is drawn inside it.

## Setup phase

Starting with **White (player 0)**, players **alternate placing their 5 rings**
on any empty points — **10 placements** in total. Then play begins (White first).

## Play phase — a turn

On your turn:

1. **Place a marker** of your colour on the point occupied by **one of your own
   rings** (that point must not already hold a marker).
2. **Move that ring** in a straight line along one of the three board
   directions. The ring:
   - slides over any number of consecutive **empty** points and may stop on any
     of them; **or**
   - when its path reaches an occupied point, it must **jump** the entire
     contiguous run of **markers** (of either colour) and land on the **first
     empty point beyond** them.
   - A ring may **never pass over or land on another RING** — rings block.
   - A ring must move **at least one point**.
3. **Flip** every marker the ring jumped over to the opposite colour. (The
   marker you just dropped is not flipped.)

## Forming a row of five

Whenever there is a line of **five or more consecutive markers of one colour**,
the **owner of that colour** must:

1. remove **exactly five** of those markers from the board (if six or more are
   in a line, the owner chooses which five), then
2. remove **one of their own rings** and set it aside (this counts toward the
   win).

**Resolution order:** rows are resolved after the ring has moved (and markers
flipped). The **mover resolves all of their own rows first**; then the
**opponent** resolves any row(s) the move created for *them*. Each removal frees
the resolver to take a further removal if another of their rows remains.

## Winning

The **first player to remove three of their own rings wins** immediately.

If the defensive move cap is somehow reached with neither player at three
removed rings, the player who has removed **more** rings wins (equal → draw).
This tie-break is a platform safeguard; in practice the row mechanic terminates
the game well before the cap.

## Implementation notes / choices

- **Move notation.** A play move is `src>dst` (drop a marker on your ring at
  `src`, move that ring to `dst`). A row removal is a follow-up move
  `R:c1,c2,c3,c4,c5|ringPoint` — the five marker cells removed and the ring
  removed — mirroring the platform's two-step "mill then remove" pattern. Setup
  placements are a single cell id.
- **Choosing five of six.** When a maximal run is longer than five, every valid
  window of five consecutive markers in that run is offered as a distinct
  removal move, paired with every one of your rings.
- **Marker supply.** The physical game has 51 markers; here the supply is
  effectively bounded only by the 85 points and a defensive ply cap, which does
  not affect normal play.
