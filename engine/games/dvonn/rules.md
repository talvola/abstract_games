# DVONN

**DVONN** (Kris Burm, 2001) is the third game in the **GIPF project**. It is a
two-player **stacking** game: you fight to control the tallest, most numerous
stacks while keeping them anchored to the three red **DVONN** pieces.

This page documents the rules **as implemented** in this package.

## The board

49 hexagonal fields arranged as the canonical DVONN board — an **elongated
hexagon** that is *five hexes wide, nine on the edges, eleven across the centre*.
We model it as **5 rows** whose lengths are **9, 10, 11, 10, 9 = 49**, using axial
`q,r` hex coordinates. Adjacency is the usual six hex directions, so the board has

- **6 corner fields** with 3 neighbours,
- **18 edge fields** with 4 neighbours,
- **25 interior fields** with 6 neighbours.

Each field holds at most one **stack** (a pile of pieces). A stack is *controlled*
by whoever owns its **top** piece; only the top colour matters for control.

## Pieces

- **23 White** + **23 Black** (the two players), plus
- **3 red DVONN pieces** — neutral; they belong to neither player but anchor the
  board (see the DVONN rule). A stack that contains a DVONN piece "holds a DVONN".

A single piece is a stack of **height 1**.

## Phase 1 — Placement

The board starts **empty**. Players alternate placing one piece on any empty
field, one piece per field, until **all 49 fields are filled**:

1. First the **3 red DVONN pieces** are placed (one per turn).
2. Then the players alternate placing their own pieces — **White** then Black,
   White then Black, … — until each has placed all **23**.

There is no movement and no removal during placement. When the 49th piece is
placed the board is full and play moves to Phase 2, with **White to move first**.

> Placement-order note: the physical game specifies that the three DVONN pieces
> are placed first and then the 23 + 23 player pieces are placed alternately. This
> package follows exactly that order. (Some published descriptions let the two
> players also alternate placing the DVONN pieces; the only thing that matters for
> the game is that all 3 DVONNs and all 23+23 pieces end up on distinct fields,
> which this guarantees.)

## Phase 2 — Movement

On your turn you must, if you can, **move one stack you control** (your colour on
top):

- Move it in a **straight line** along **one of the six hex directions**.
- Move it **exactly a number of fields equal to its height** (height *n* moves
  *n* fields). You may pass over fields (empty or occupied) in between.
- It must **land squarely on top of another OCCUPIED field**. You may **never**
  land a stack on an empty field, and a height-*n* stack whose every distance-*n*
  landing (in all six directions) is empty or off the board **cannot move**.

The moved stack is placed **on top** of the destination stack, so the destination
keeps growing taller. A stack is **immobile** exactly when none of its six
distance-*n* landings is an occupied on-board field — for example a stack so tall
that every landing falls off the board.

### The DVONN rule (connection)

**Immediately after every move**, the board is checked: starting from every stack
that holds a **DVONN** piece, follow chains of edge-adjacent stacks. Every stack
that **cannot** be reached this way — i.e. is no longer connected to any DVONN
piece — is **removed from play**. Removed pieces leave the game permanently; they
are never returned to a reserve. (If, after a move, no DVONN piece remains on the
board at all, every stack is removed.)

This is the heart of DVONN: cutting the opponent's stacks off from the DVONN
pieces wipes them out.

### Passing

If the player to move has **no legal move** but the opponent still does, the player
**passes** and the opponent continues. (The UI shows a *pass* button.)

## End of the game and scoring

The game **ends** as soon as **neither** player can move. Then each player scores
the **total number of pieces** in all the stacks they control (every piece in a
stack you top counts — your own pieces, buried enemy pieces, and any buried DVONN
pieces alike). The player with the **most** pieces **wins**; an equal count is a
**draw**.

## Notation

- Placement move: a single field id, e.g. `4,2`.
- Movement move: `from>to`, e.g. `3,2>5,2` (the stack at `3,2` moves to `5,2`).
- `pass` when you have no legal move.

## Source / faithfulness notes

Implemented to match the official DVONN rules (Kris Burm / Don & Co.). Two points
worth flagging:

- **Six movement directions** (not three): DVONN stacks move along all six hex
  axes. Interior fields have six neighbours.
- **Jumping is allowed**: a stack may pass over intervening empty *or* occupied
  fields; only the **landing** field must be occupied.

Official rules: <https://boardgamegeek.com/boardgame/2346/dvonn>.
