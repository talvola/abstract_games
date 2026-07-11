# Cation

Luis Bolaños Mures (June 2016). A drawless square-board connection game that
resolves the classic square-grid crosscut problem with **ko fights**.

## Board and goal

- Played on the points of an initially empty square grid (default 11×11; the
  designer's Zillions version offers 3×3 up to 19×19).
- **Black** owns the **top and bottom** edges, **White** the **left and
  right** edges.
- You win by completing a chain of **orthogonally adjacent** stones of your
  colour touching your two opposite edges. Diagonal adjacency does *not*
  connect.
- Black moves first. **Pie rule**: on White's first turn only, White may play
  `swap` to take over Black's opening stone instead of making a regular move.
  Because the two goals are transposed (rows vs columns), the stone is claimed
  at the diagonally mirrored point `(c,r)→(r,c)` — the value-preserving
  equivalent of "changing sides" (same convention as Hex, Konobi and Rhode).

## Crosscuts

A **crosscut** is a 2×2 pattern of stones consisting of two diagonally
adjacent black stones and two diagonally adjacent white stones (the two
opposite-colour diagonals "cross").

## Playing a turn

On your turn you face one of two situations:

1. **No crosscuts on the board** — you must place a stone of your colour on an
   empty point such that it forms **no crosscut containing a stone that was
   placed by the opponent on their latest turn**. Forming crosscuts out of
   *older* stones is allowed — that is how ko fights start. If no such
   placement exists, you must **pass** (passing is otherwise not allowed).
2. **One or more crosscuts on the board** — you must take a **friendly** stone
   from one of those crosscuts and place it on a **different empty point where
   it doesn't create any other crosscut**. If no such point exists, the stone
   is simply **removed** from the board (click the stone itself).

A stone relocated under rule 2 counts as "placed on the latest turn" for
rule 1 (this matches the designer's own Zillions implementation, which moves
its latest-stone marker onto the relocated stone). After a pass or a
removal-only turn, the opponent's next placement is unrestricted.

The winning connection is checked after every placement **and** every
relocation — sliding a stone out of a crosscut can complete your chain.

## Moves in this implementation

- Placement: click an empty point.
- Crosscut resolution: click one of your stones in a crosscut, then the
  destination point. If a stone has no legal destination, clicking it removes
  it.
- `pass` (only when forced) and `swap` (pie rule) appear as buttons.

## Draws / termination

By the rules Cation is drawless and every crosscut-resolution move strictly
reduces the number of crosscuts, so games end naturally. As the platform's
standard backstop against pathological play, two consecutive passes (only
possible in a theoretically unreachable dead position) or reaching the hard
ply cap of 8×N×N is scored as an honest draw.

## Version note

This implements the complete **2016 ruleset**, which is identical across the
designer's BGG announcement thread, his Zillions of Games submission (id
2500), and the AiAi report. In April 2026 the designer mentioned he has
"streamlined" Cation, but no streamlined ruleset has been published anywhere
we could find; if one appears, this package should be revisited.

Source: [New games: Cation and Rhode (BGG)](https://boardgamegeek.com/thread/1593043).
