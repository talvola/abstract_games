# Croda

Orthogonal draughts by **Ljuban Dedić** (Croatia, 1995) — 1989 Yugoslav
champion of International Draughts — designed for a minimal margin of draws.
Rules as implemented here, from Christian Freeling's article *"International
Checkers Versus Croda"* (**Abstract Games #9**, Spring 2002, pp. 5-6),
cross-checked against Freeling's own
[mindsports.nl rules page](https://mindsports.nl/index.php/on-the-evolution-of-draughts-variants/draughts-variants/508-croda)
(the two sources agree on every rule).

## Board and setup

- A regular chess board; **all 64 squares** are used. Files `a`-`h`, ranks
  `1`-`8`.
- Each player has **24 men** filling their first three ranks (White ranks 1-3,
  Black ranks 6-8). **White moves first.**

## Moving

- A **man** moves one square **forward** — straight ahead or diagonally
  forward — to an empty square. No sideways or backward moves; the diagonal
  step is the *only* diagonal motion in the game.
- A **king** (promoted man, marked K) moves like a chess **rook**: any number
  of unobstructed squares along a rank or file, never diagonally.

## Capturing

- All capture is **orthogonal** (along ranks and files) — men never capture
  diagonally. Capturing is **compulsory** and takes precedence over any quiet
  move.
- A **man** captures by the **short leap** in all four orthogonal directions
  (forward, backward and sideways): it jumps an adjacent enemy piece to the
  empty square immediately beyond.
- A **king** captures by the **long leap**: it flies along an open rank or
  file to an enemy piece and lands on any empty square beyond it on the same
  line, and may then turn and continue.
- If the jumper can jump again from its landing square it **must** continue.
  **Majority rule:** among all available capture sequences of all pieces you
  must play one capturing the **maximum number of pieces** (a king counts as
  one piece, same as a man); a capturing king must choose its route to
  maximize the sequence. With several maximal options the choice is free.
- Captured pieces are removed **only after the whole sequence ends**: a
  jumped piece stays on the board until then, may **not be jumped twice**,
  and still blocks passage and landing squares, while empty squares may be
  crossed repeatedly — enabling the *Coup Turc* combination.

## Promotion

- A man promotes to king only if it **ends its move** on the opponent's back
  rank. A man that jumps **on and off** the back rank in mid-capture must
  complete the sequence and does **not** promote.

## End of the game

- A player with **no legal move** — all pieces captured, or completely
  blocked — **loses**.
- **Draws (as implemented):** 50 consecutive plies without a capture or a man
  move, or a hard 400-ply cap, is a draw. (The published rules give draw by
  3-fold repetition or mutual agreement; men can only advance, so only kings
  can repeat — the no-progress rule covers those cases. Use the draw-offer
  buttons for agreement.)

## Notation

The move log uses algebraic draughts notation: `f1-e2` for a step,
`d5xd1xh1xh3xe3` for a capture path (the squares the piece visits).

*Correctness anchor:* the package selftest replays Freeling's printed "Coup
Turc in Croda" problem (AG #9, p. 5) move for move — `1.f1-e2 a5:d5 2.c2-d3
d5:d1:h1:h3:e3 3.e2:e4:e6:c6:c8+` — with both Black replies and White's final
promotion chain verified as forced.
