# HexDame

Christian Freeling (1979). International draughts adapted, rule for rule, to a
hexagonal board. Rules as implemented here, from Freeling's own site
[mindsports.nl](https://www.mindsports.nl/index.php/arena/hexdame/72-rules)
(cross-checked with Wikipedia and *Abstract Games* #8).

## Board and setup

- A hexagonal board of hexagons, 5 cells per side (61 cells). Cells are named
  by file `a`-`i` and rank `1`-`9` (oblique lines); White's corner is **a1**
  (bottom left), Black's is **i9** (top right).
- Each player has **16 men** filling the 4x4 rhombus in their corner: White on
  files a-d x ranks 1-4, Black on files f-i x ranks 6-9. **White moves first.**
  Players must move in turn.

## Moving

- A **man** moves one cell to a vacant cell in one of the **three forward
  directions** (straight forward or oblique forward).
- A **king** (promoted man, marked K) is *flying*: it moves any distance along
  a line of vacant cells in any of the **six directions**.

## Capturing

- Capturing is **compulsory** and works in **all six directions** (men capture
  backward too). A man jumps an adjacent enemy piece to the cell immediately
  beyond, which must be vacant. A king jumps an enemy piece it sees at any
  distance along an open line, landing on any vacant cell beyond it.
- If the jumper can jump again from the landing cell, it **must** continue.
  **Majority rule:** among all available capture sequences (of all pieces), you
  must play one capturing the **maximum number of pieces** (a king counts as
  one piece, same as a man); with several maximal options you choose freely.
- Captured pieces are removed **only after the whole sequence ends**: a jumped
  piece stays on the board until then, may **not be jumped twice**, and blocks
  further jumps (the *Coup Turc*). Cells may be visited more than once.

## Promotion

- The back rank is the **nine cells** of the two far sides of the board: for
  White, file `i` plus rank `9` (i5-i9 and e9-i9); for Black, file `a` plus
  rank `1`.
- A man promotes to king only if it **ends its move** on the back rank. A man
  that visits a back-rank cell in mid-capture must complete the capture and
  does **not** promote.

## End of the game

- A player with **no legal move** — all pieces captured, or completely blocked
  — **loses**.
- **Draws (as implemented):** 50 consecutive plies without a capture or a man
  move, or a hard 400-ply cap, is a draw. (Freeling's rules give draw by
  3-fold repetition or agreement; use the draw-offer buttons for agreement.)

## Notation

The move log shows traditional HexDame notation: `c5-d6` for a move,
`e7xc5xe5` for a capture path (the cells the piece visits).
