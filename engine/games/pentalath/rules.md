# Pentalath

**Pentalath** (originally **Ndengrod**) was designed in 2009 by **Cameron
Browne** — specifically by his *evolutionary game-design program*, which evolved
existing rulesets; Ndengrod was the program's most-liked output. It was renamed
Pentalath by Néstor Romeral Andrés as a sister game to *Yavalath* and published
by nestorgames. It is **five-in-a-row with Go-style capture**.

## Board

A **hexagonal board of hexes (a "hexhex") with 5 hexes per side — 61 cells in
total**, the same board used by Yavalath. The six corners are **present** (the
board is a full hexagon of hexes, not corner-clipped). Cells use **axial
coordinates** `q,r`, and every cell has up to **6 neighbours**.

## Play

- Two players, **Black** and **White**. Black moves first.
- On your turn, **place one stone of your colour on any empty cell**.

### Capture (Go-style)

A **group** is a maximally-connected set of same-colour stones (6-neighbour
adjacency; a lone stone is a group). A group's **freedom** (liberty) is an
**adjacent EMPTY cell on the board**.

- The **board edge grants no freedom**: an off-board neighbour is not an empty
  cell, exactly as in Go. Only an in-bounds, unoccupied neighbour counts.
- After your placement, **any enemy group now left with no freedom is captured
  and removed** from the board.
- Captures are resolved **before** checking your own stone: enemy groups are
  removed first, which may open up freedom for your group.

### No suicide

> *"Pieces may not commit suicide but may create their own freedom through
> capture."*

A placement is **illegal** if your own just-placed group would have **no
freedom** *and* the move **captures nothing**. A placement that fills your own
last liberty **but captures an adjacent enemy group** (thereby opening a
freedom) **is legal**.

## How to win

**Make a line of FIVE OR MORE of your stones in a row** along one of the **three
hex axes**. Because a capture can break up a line, the win is checked on the
board **after** captures resolve — so only the player who just moved can complete
a winning line. Capturing is therefore a tool to *break up* your opponent's
threatened five.

## Pie rule (swap)

By default the **second player (White), on their first turn, may play `swap`**
instead of placing: this takes over the opening — every stone on the board
becomes White's — and play then passes back to the other player. This equalises
the first-move advantage. The pie rule can be turned off via the **Pie rule**
option.

## Termination

There is **no ko/superko rule** in Pentalath. Because captures recycle cells,
play could in principle repeat, so this implementation declares a **draw** if a
large number of plies pass with **no capture** (a no-progress cap), or if the
board fills with no winner. In practice the five-in-a-row goal makes draws rare.

## Implementation notes / choices

- **Board shape:** full hexhex, side 5 (61 cells). The original machine output
  used a trapezoid; the published Pentalath uses this hexagonal board, which is
  what is implemented here.
- **Liberty = empty on-board cell**; the edge gives no liberty (faithful to the
  Go-style rule quoted above).
- **Capture order:** enemy groups before own group (standard Go ordering),
  enabling "freedom through capture".
- **No superko**; termination via a no-progress ply cap → draw.
- **Swap** is modelled as the action move `"swap"`, offered only as White's first
  action.

Moves are single-cell placements `"q,r"` (axial), or the literal `"swap"`.
