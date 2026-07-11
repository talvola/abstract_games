# Bobail

Traditional two-player game from the Morbihan region of Brittany, France.
Played on a **5×5** board. Each player owns **5 pieces**; a shared neutral
piece, the **Bobail**, belongs to nobody and is moved by both players.

- **Red** (moves first) starts on the bottom row — Red's *home row*.
- **Blue** starts on the top row — Blue's home row.
- The **Bobail** (the green ◉) starts on the centre square.

## A turn = two moves

Except for the game's very first turn, a turn is two sub-moves by the same
player, in this order:

1. **Step the Bobail** exactly **one square** in any of the 8 directions, to an
   **empty** square. This is mandatory.
2. **Slide one of your pieces** in any of the 8 directions **as far as it can
   go** — until the edge of the board, or the square before another piece or
   the Bobail. You may not stop early, and pieces never jump or capture.

**First-turn exception:** the opening player does *not* move the Bobail — their
first turn is a single piece slide.

The UI plays both sub-moves by click: on the Bobail step, click the Bobail then
its destination; on the slide, click your piece then its (full-distance)
destination.

## Winning

- **Bobail home:** the moment the Bobail lands on a player's home row, **the
  owner of that row wins** — instantly, even in the middle of a turn (the piece
  slide is not played), and *regardless of who moved it there*: with the Bobail
  cornered you can be forced to deliver it onto the opponent's row.
- **Bobail trapped:** if at the start of your turn you cannot step the Bobail
  (every adjacent square is occupied or off-board), **you lose** — the player
  who sealed it in wins. The same applies in the rare case where no Bobail step
  leaves you any piece slide to complete the turn: a player who cannot complete
  a legal turn loses.

## Draws (backstop)

The traditional rules define no draw, but nothing forces progress, so this
implementation adds honest backstops: **threefold repetition** of the same
whole position (all pieces + Bobail + player to move, at the start of a turn)
or **400 sub-moves** without a result is a **draw**.

## Notes on this implementation

- Sources: the BGA rules summary, the French rule sheet ("Le Bobail" PDF),
  dragono.fr and 1234.pm all agree on the turn order, the one-square Bobail
  step, the mandatory full-distance slide and both win conditions; the
  first-turn exception is stated explicitly by BGA, the French sheet and
  dragono.fr (1234.pm is silent on it). The "row owner wins even if the
  opponent moved the Bobail there" reading follows BGA's explicit "moved to
  *either* player's home row — that player wins".
- **Bobail vs Neutron:** Neutron (Robert A. Kraus, 1978) shares the same skeleton
  — 5×5, five pieces a side, a shared centre piece moved before one of your own,
  win by bringing it to your own back rank. The defining difference is the shared
  piece's movement: the **Neutron is a full slider** (it flies until blocked,
  like the pieces), while the **Bobail steps exactly one square**. That makes
  Bobail a slow escort-and-trap game (surrounding the Bobail is a first-class
  win condition and a constant threat) where Neutron is a tempo game about
  launching the shared piece across the board. Neutron is not currently in this
  library; they are distinct games.
