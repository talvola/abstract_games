# Shobu

**Shobu** (Manny Vega & Jamie Sajdak, 2019; Smirk & Dagger Games) is a
two-player abstract strategy game played simultaneously across **four small
boards**. The name means "showdown."

## The boards

There are **four 4×4 boards**, arranged in a **2×2 super-layout**:

```
    +---------+---------+
    | board 2 | board 3 |   <- Player 1's HOME row (far side)
    |  LIGHT  |  DARK   |
    +---------+---------+
    | board 0 | board 1 |   <- Player 0's HOME row (near side)
    |  DARK   |  LIGHT  |
    +---------+---------+
```

- Two boards are a **DARK** colour (boards 0 and 3, on one diagonal) and two are
  **LIGHT** (boards 1 and 2, on the other diagonal). Each player therefore faces
  exactly **one dark + one light** board on their side.
- The **two boards on a player's side** of the table are that player's **HOME
  boards** (Player 0 = boards 0 and 1; Player 1 = boards 2 and 3).

## Setup

Each player has **4 stones on every board**, placed on the row nearest to them:
Player 0 fills row `r = 0` on each board, Player 1 fills row `r = 3`. That is
**16 stones per player** (4 stones × 4 boards).

## A turn: passive move, then aggressive move

A full turn is **two moves by the same player**, in order:

### 1. Passive move

Move **one of your stones** on **one of your two home boards**, **1 or 2
squares** in any of the **8 directions** (orthogonal or diagonal).

- The passive move may **NOT push** anything: every square it passes over and
  the square it lands on must be **empty**. No jumping.

### 2. Aggressive move

Then move one of your stones the **same direction and the same distance** (1 or
2) as the passive move, on a board of the **opposite colour** to the board you
made the passive move on (dark ↔ light).

- The aggressive move **MAY push**. Along its line of travel there may be **at
  most ONE stone, and that stone must be an opponent's**. You can never push two
  stones at once, and never push one of your own stones.
- The pushed opponent stone is shoved **one square further** in the move
  direction. The square it lands on must be **empty or off the board**:
  - off the board ⇒ that stone is **removed from the game**;
  - blocked by another stone ⇒ the push (and the move) is **illegal** (it would
    require pushing two stones).

### Both halves must be possible

A passive move is only legal if a **matching aggressive move also exists**. If
no aggressive move matches a given passive move, that passive move is invalid
and you must choose another.

## Winning

You **win the instant your opponent has no stones left on any one of the four
boards** — i.e. you have cleared all four of their stones off a single board.

## Move encoding (this implementation)

A turn is entered as two separate moves so the same player keeps the turn:

- **Passive move:** `"b,c,r>b,c2,r2"` — pick your stone on a home board, then its
  empty destination. The interface then offers only the legal aggressive moves.
- **Aggressive move:** `"b,c,r>b,c2,r2"` — same direction and distance, on the
  opposite-colour board; it may push one opponent stone.

After the aggressive move the turn passes to the opponent. The caption shows
whose turn it is and whether a passive or aggressive move is expected.

## Termination

Real games end quickly. As a safety net this implementation caps the game at
**200 full turns**; reaching the cap is scored as a **draw**.

## Interpretations / notes (as implemented)

- **Board / colour arrangement:** dark boards on the bottom-left/top-right
  diagonal, light on the other, so each player owns one dark and one light home
  board (the standard physical arrangement). The orientation of "near" vs "far"
  is cosmetic — directions are vectors shared by the passive and aggressive
  moves, so play is unaffected by which side is drawn at the bottom.
- **Push legality:** the path of the aggressive move (the 1 or 2 squares it
  passes over and lands on) may contain at most one stone; it must be the
  opponent's; and the single square one step beyond it must be empty or off the
  board. This faithfully encodes "push at most one opponent stone, never two,
  never your own."
- **Win as event:** the per-board elimination is checked after each aggressive
  move and stored as the winner.
