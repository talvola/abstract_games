# Redstone

Mark Steere, February 2012 (with a design contribution by Luis Bolaños Mures).
A draw-free Go variant: **all captures are made with shared, permanent red
stones**. Implemented from the author's rule sheet —
[Redstone_rules.pdf](https://marksteeregames.com/Redstone_rules.pdf)
([BGG](https://boardgamegeek.com/boardgame/120533/redstone)).

## Board and stones

- Square grid of points (this module offers **7×7, 9×9 or 13×13**; the sheet
  does not prescribe a size). Adjacency is orthogonal.
- Black (first) and White each have unlimited stones of their own colour, and
  **share** an unlimited supply of **red** stones.

## Groups and liberties

A *group* is an orthogonally connected set of like-coloured **black or white**
stones — red stones never form groups. A *liberty* is an empty point adjacent
to a group.

## Placement rules

Players alternate placing exactly one stone on an empty point. **No passing** —
a placement is always available and must be made.

- A placement that leaves one or more groups (of either or both colours)
  without liberties is a **capturing placement, and may only be made with a
  red stone**. You may not fill a group's last liberty — even an enemy
  group's — with your own colour.
- Conversely, **a red stone may only be placed if it bounds** (deprives of all
  liberties) at least one group of either or both colours.
- When a red placement bounds several groups, **all of them are removed
  immediately and simultaneously**, regardless of colour. *Unlike Go*: if your
  own group is only temporarily bounded (it would regain liberties once the
  neighbouring enemy group is lifted), it is **still removed** (sheet, Fig. 3).
- **Self-capture is allowed** (with a red stone).
- Red stones are permanent: they are never removed, so positions never repeat
  and no ko/superko rule exists.

## Object of the game — annihilation

- If your placement removes **all enemy stones** from the board, **you win**.
- If your placement removes **every black and white stone** at once, **you
  (the mover) win**.
- If your placement removes all of **your own** stones while enemy stones
  remain, **you lose**.

Draws cannot occur.

## Pie rule

On White's first turn (move 2), White may play **swap** instead of placing:
White takes over Black's opening stone and Black moves next.

## Move encoding (this module)

`c,r=black` / `c,r=white` — place your own stone; `c,r=red` — place a shared
red stone; `swap` — pie rule. On the board a click plays the only legal colour
directly and opens a picker on the rare points where both your colour and red
are legal.

## Interpretations / engine notes

- The sheet states a player always has a placement available. Defensively, if
  a player ever had no legal placement they would lose (Steere's standard
  "unable to move loses" convention) — provably unreachable from the initial
  position: a mover with no placement would need every empty point to be a
  hole surrounded by enemy/red stones with no group in atari, which forces
  the mover to have *no stones on the board at all* (any mover group needs a
  liberty, i.e. an adjacent empty point) — and past the opening plies the
  game already ends the moment a placement removes a player's last stone.
- Game length is structurally finite: red stones only accumulate (at most one
  per capture, never removed), and between captures every move fills an empty
  point.
