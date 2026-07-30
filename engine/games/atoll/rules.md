# Atoll

**Mark Steere, January 2008.** A two-player connection game on a hexagonal grid.
Eight "islands" of stones ring an empty board, alternating in colour, four per
player. Add one stone per turn; win by joining two of your islands that lie
**exactly opposite** each other. Draws and ties are impossible.

These are the rules *as implemented*. The official one-page rule sheet is
[Atoll_rules.pdf](https://www.marksteeregames.com/Atoll_rules.pdf).

## The board

The standard board (Figure 1 of the rule sheet) has **104 playable cells** and
**36 island stones** — 18 per player in eight islands. Files run vertically, as
the rule sheet draws them.

```
      W   W       B   B            W = second player (Blue)
    W   W   W   B   B   B          B = first player (Red)
      ·   ·   ·   ·   ·            · = empty playable cell
    ·   ·   ·   ·   ·   ·
  B   ·   ·   ·   ·   ·   W
    ·   ·   ·   ·   ·   ·
  B   ·   ·   ·   ·   ·   W
    ·   ·   ·   ·   ·   ·
  B   ·   ·   ·   ·   ·   W
    ·   ·   ·   ·   ·   ·
  B   ·   ·   ·   ·   ·   W
    ·   ·   ·   ·   ·   ·
  W   ·   ·   ·   ·   ·   B
    ·   ·   ·   ·   ·   ·
  W   ·   ·   ·   ·   ·   B
    ·   ·   ·   ·   ·   ·
  W   ·   ·   ·   ·   ·   B
    ·   ·   ·   ·   ·   ·
  W   ·   ·   ·   ·   ·   B
    ·   ·   ·   ·   ·   ·
      ·   ·   ·   ·   ·
    B   B   B   W   W   W
      B   B       W   W
```

Going clockwise round the perimeter the eight islands alternate in ownership:

| position | island | owner | size |
|---|---|---|---|
| top-left | **Blue North** | Blue | 5 |
| top-right | **Red North** | Red | 5 |
| right, upper | **Blue East** | Blue | 4 |
| right, lower | **Red East** | Red | 4 |
| bottom-right | **Blue South** | Blue | 5 |
| bottom-left | **Red South** | Red | 5 |
| left, lower | **Blue West** | Blue | 4 |
| left, upper | **Red West** | Red | 4 |

Because the owners alternate, the island diametrically opposite any island
belongs to the **same** player. Each player therefore has exactly two goals:
**North–South** and **West–East**.

There are eight seams between neighbouring islands round the perimeter, and they
are not all alike:

- **six are notched** — the top centre, the bottom centre and the four corners.
  A single island cell is *missing* there, so the two islands do not touch.
- **two are not** — half-way up the left side (Red West meets Blue West) and
  half-way up the right side. Those two islands sit directly against each other,
  which is why each side column is one unbroken run of eight stones.

Either way exactly **one** playable cell touches both islands of a seam, and it
is the cell a chain uses to reach round a corner.

Island stones sit on real cells of the same grid. They are never captured, never
moved, and are **never legal placements** — those cells are already occupied. The
board shades them faintly so you can tell island from playing area.

## Play

1. **Red moves first**, then players alternate. (The rule sheet calls the first
   player Black; this app paints seat 0 red and seat 1 blue.)
2. A turn is exactly one placement: put one of your stones on **any empty
   playable cell**. Placing is compulsory and always possible while the board is
   not full. Nothing is ever captured or moved.
3. **You win the instant one connected group of your stones contains stones of
   two of your islands that are exactly opposite each other** — i.e. your North
   and South islands, or your West and East islands. *Your island stones count as
   part of the chain*, so a chain reaching your South island and a second chain
   reaching from that same South island to your North island together win, and
   the linking stones inside the island are yours for free.
4. Two cells are connected if they are neighbours on the hex grid (six
   directions: N, S, NE, NW, SE, SW).

Only the player who just placed can have gained a connection, so the win is
checked for the mover.

## Why there are no draws

*Termination.* Each move fills one empty playable cell and nothing is ever
removed, so the number of empty cells strictly decreases by one per ply. The game
therefore ends after at most 104 plies (202 / 332 on the larger boards). No
repetition rule, no move-count cap and no no-progress rule are needed, and none
are implemented.

*No ties.* On a full board exactly one player has a winning connection.

- **Never both.** If Red joins its North and South islands, that chain plus the
  two islands cuts the board into two pieces, and because the islands alternate
  around the perimeter Blue's two opposite islands lie on *opposite sides* of the
  cut. No Blue chain can cross a solid Red one, so Blue cannot also connect.
- **Never neither.** This is the Hex no-draw theorem with eight alternating
  boundary arcs instead of four. On a fully coloured board the Red/Blue interface
  is a set of curves pairing up the eight colour-transition points of the
  perimeter without crossing — four chords, which cut the disc into **five**
  faces, so the eight boundary arcs fall into exactly five blocks, each block
  monochromatic and the blocks pairwise non-crossing. A block of four must be one
  player's whole set of arcs, and any three arcs of one player already contain an
  opposite pair; so the only way to avoid an opposite pair everywhere is five
  blocks of sizes 2+2+2+1+1 — and no three non-opposite same-colour pairs are
  pairwise non-crossing. Enumerating the 14 non-crossing pairings confirms it:
  every one of them connects an opposite pair, for exactly one player.

Empirically as well: random *complete* colourings of all three boards — tens of
thousands of them, uniform, biased and spatially clustered — produced exactly one
winner every time, never two and never none. The selftest re-checks a sample of
288 of them on every run, plus 40 whole random games. The engine still scores a
hypothetical full board with no connection as an honest **0–0 draw** rather than
inventing a tie-break; that branch is dead in real play, and the selftest asserts
both facts.

## Generalized Atoll, and the objective used here

The rule sheet also gives a *generalized* objective for boards with any multiple
of four islands: connect two or more of your islands such that the **shortest
perimeter path touching those islands touches at least (islands / 2 + 1) of
them**. On the eight-island board that threshold is 5 of 8, and the two rules are
provably the same: the shortest perimeter arc covering a set of your islands
reaches five or more islands exactly when the set contains a diametrically
opposite pair. The selftest brute-forces every subset of two or more of a
player's islands — 11 each, 22 in total — and asserts the agreement, so the
simpler "opposite pair" test used by the engine is the generalized rule
specialised to this board.

Figure 4's **Atoll-4 (Hex)**, **Atoll-12** and **Atoll-24** boards are *not*
implemented. Atoll-4 is a 5×5 Hex board (25 playable cells ringed by four
four-stone islands) and Hex already ships as `hex`. Atoll-12 and Atoll-24 are
drawn *mid-game*, so which of their perimeter stones are islands and where the
notches divide them cannot be read off the figure with confidence; rather than
guess a board, only the eight-island game is offered.

## Board sizes

| Option | Playable cells | Island stones |
|---|---|---|
| **11** (standard) | 104 | 36 |
| 15 | 202 | 52 |
| 19 | 332 | 68 |

**Only the 11 board appears in the rule sheet** — Figure 1 draws it and the sheet
names no other size. The 15 and 19 boards are *not* published Atoll: they are the
same eight-island geometry scaled up, matching AbstractPlay's two larger Atoll
variants cell-for-cell, and are offered here as clearly-labelled options. Only
sizes ≡ 3 (mod 4) admit the notch construction, which is why 13 and 17 are not
offered. (The rule sheet's "Generalized Atoll" section is about different island
*counts* — 4, 12, 24 — not about bigger eight-island boards.)

## Notation

Moves are cell ids `"q,r"` (axial). The move log shows the algebraic name of the
cell — file letter left to right, rank counted upwards from the foot of that
file, so `a1` is the bottom cell of the leftmost playable file and `f10` is the
top cell of the middle file. This matches AbstractPlay's notation for the same
board.

## Notes / interpretations

- **Islands are stones, not edges.** The rule sheet is explicit ("The stones of
  your islands can be included in the sequence"), and Figure 3's caption points
  out that stones in Black's South island form part of that winning sequence.
  This implementation therefore puts real, permanent stones on the island cells
  and runs one flood fill over placed stones *and* island stones. (A "Hex-style"
  implementation that instead asks whether your stones reach two opposite *edge
  regions* is equivalent only if it also treats two groups touching a common
  island as connected.)
- **No pie / swap rule.** The rule sheet has none, so none is implemented. (Some
  online implementations offer one; Atoll has a first-player advantage that the
  larger boards do not remove.)
- **Only the mover is checked for a win.** Placing your own stone can only merge
  your own groups, so your opponent cannot be handed a connection by your move.
- **Draw handling.** A genuine tie scores 0–0. See "Why there are no draws" — it
  is unreachable, and it is *not* replaced by a fabricated tie-break.
- **Board geometry source.** Figure 1 has no text layer, so the board was read
  out of the PDF's vector art: 140 circles, 104 grey (playable), 18 black and 18
  white (islands). The selftest carries that transcription and asserts the
  generated board matches it cell for cell, and asserts the eight-island
  perimeter cycle it derives from the geometry alone.
