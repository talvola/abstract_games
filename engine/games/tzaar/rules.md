# TZAAR

**TZAAR** (Kris Burm, 2007) is the fourth game of Project GIPF — a sharp
stacking-and-capture duel. This page documents the rules **as implemented** by
this package.

## Board

The board is a **hexagonal board of hexagons** (a "hexhex") of **side 5**: every
cell with axial coordinate `q,r` (cube `s = -q-r`) satisfying
`max(|q|, |r|, |s|) ≤ 4`. That is **61 cells** total. The single **centre cell
`0,0` is empty** at the start of the game, leaving **60 playable cells**, each
holding one piece at setup. There are **6 hex directions**. A piece or stack
**slides in a straight line over any number of vacant cells** and stops on the
**first occupied cell** in that direction. It may **never jump over a piece** and
never lands on an empty cell — every move *and* capture ends on the first
occupied cell in some direction.

## Pieces

Each player owns **30 pieces** in three **types** of differing importance:

| Type | Importance | Count per player |
|---|---|---|
| **Tzaar** | highest | 6 |
| **Tzarra** | middle | 9 |
| **Tott** | lowest | 15 |

A **stack** is a column of pieces. Its **type is the type of its TOP piece**, and
its **height** is the number of pieces in it. A lone piece is a stack of height 1.
A stack is **controlled** by whoever owns its top piece (at setup every stack is
height 1, so control = ownership). The renderer shows each stack as a layered
tower (reusing the Lasca tower glyph) labelled with its top type and height.

## Setup (fixed canonical layout)

In the physical game the 60 pieces are placed in a **randomized** arrangement.
To avoid a chance node and keep games reproducible, this implementation uses a
**fixed, deterministic canonical layout**:

1. The 60 non-centre cells are taken in a fixed order (sorted by `(q, r)`).
2. A fixed length-30 **type sequence** per colour is built by an even
   deterministic spread: 6 Tzaar slots on a 6-way split of 30, 9 Tzarra slots on
   a 9-way split of the remaining 24, and 15 Totts — giving exactly **6 Tzaar /
   9 Tzarra / 15 Tott**, well interspersed (no long runs of one type).
3. Cells are dealt alternating colours (cell *i* → owner `i % 2`); each colour
   walks its own copy of the type sequence.

This yields the correct 30 + 30 composition with the centre empty, and is
identical on every game.

## A turn — TWO actions

White moves first. A turn consists of **two actions**:

1. **Capture (mandatory).** Pick a stack you control and **slide** it in a
   straight line over vacant cells to the **first occupied cell** in some
   direction. If that cell holds an **enemy** stack whose **height is ≤ your
   stack's height**, the enemy stack is **removed entirely** and **replaced** by
   your stack (*capture by replacement*). Your stack's height is **unchanged** —
   you do **not** bank or keep any enemy pieces. You may **not** jump over a
   piece, and you cannot capture a taller enemy or a friendly stack. You **must**
   make at least one capture; if you cannot, you lose (see below).

2. **Second action (optional).** *Either*
   - another **capture** (same rule), *or*
   - a **stack move**: **slide** a stack you control to the **first occupied
     cell** in some direction; if it is a **friendly** stack, **combine** them.
     Your moved stack goes **on top**, the combined **height is the sum**, and the
     resulting **type is your moved stack's top type**.

   You may **skip** the second action (a "pass").

### First-move rule

The standard TZAAR convention is implemented: the **very first action of the
game is a single capture only** — the opening player does **not** take a second
action on the first turn. From the second turn onward, every turn is the full
two-action turn (capture, then optional capture-or-stack).

## Winning and losing

A player **loses immediately** if, **at the start of their turn**, either:

- they have **zero stacks of any one of the three types** — all of Tzaar,
  Tzarra and Tott must survive (a stack counts as its **top** type); or
- they **cannot make a capture** (no controlled stack can slide to a capturable
  enemy stack).

The opponent wins in either case.

## Termination

Captures strictly reduce the total piece count, so the game cannot loop
indefinitely; a defensive **600-action ply cap** (scored as a draw) is included
as a hard safety net but is not expected to be reached in real play.

## Notes / ruleset choices

- **Board size and first-move rule** follow the standard published TZAAR rules
  (hexhex side 5, 60 pieces, centre empty; opening move = single capture).
- The **starting layout is fixed/deterministic** (documented above) rather than
  randomized, by design — there is no chance node.
