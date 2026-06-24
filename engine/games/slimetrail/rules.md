# Slimetrail

*Bill Taylor, 1992. A two-player abstract race/pursuit game.*

## Equipment

- An **N x N** square board (this implementation: 7x7, **8x8** default, or 9x9).
- Two **goal cells** in opposite corners:
  - **Red** (player 0) owns the **bottom-left** corner `0,0`.
  - **Blue** (player 1) owns the **top-right** corner `(N-1,N-1)`.
- One shared, neutral **marker** (the "snail"), which starts on the **centre** cell.
- A supply of **slime** markers (green).

## Play

Players alternate; **Red moves first**. On your turn you must **slide the marker
one step** to an adjacent cell — orthogonally *or* diagonally (a chess **king**
step). The destination must be:

- on the board, and
- **not slimed** (the marker can never enter a slimed cell).

After the marker moves, the cell it **just left** is permanently covered in
**slime** and can never be entered again. Because every move slimes one cell, a
cell is never visited twice and the marker's trail can never cross itself.

## How to win

- **Reach a goal.** The moment the marker is moved **onto a goal cell**, the
  **owner of that goal wins** — *regardless of who moved it there*. Landing on
  `0,0` wins for **Red** (player 0); landing on `(N-1,N-1)` wins for **Blue**
  (player 1). You can be
  forced into a position where your only legal move delivers the win to your
  opponent.
- **Trap your opponent.** If the player to move has **no legal slide** (the
  marker is boxed in by slime and the board edges), that player **loses** and the
  opponent wins.

## Termination

The board is finite and each move slimes exactly one cell, so the marker can make
at most N x N moves before it is trapped. The game therefore always ends, with a
decisive result (one player reaches a goal, or one player is trapped). A
defensive ply cap (a draw) exists in code but is never reached in real play.

## Notation

A move is the marker's **destination cell** `c,r` (a single click on the cell the
snail steps to). The move log shows e.g. `Blue: snail -> 3,4`.

## Interpretations / implementation notes

- **Board size & start.** Online implementations vary (bodogemu uses 7x7; other
  references describe a general N x M rectangle). This port uses a square board
  with goals in the two opposite corners and the marker starting on the centre
  cell; size is a manifest option (default 8x8).
- **8-directional movement.** Sources agree the marker moves like a king
  (horizontal, vertical, *and* diagonal) to any adjacent un-slimed cell.
- **Trapped player loses.** Taken from the common "...or if the opponent is
  blocked" implementation (e.g. bodogemu): a player with no move loses. This also
  guarantees a decisive, well-defined terminal in every line.
- **Optional "reachability" restriction NOT enforced.** Some combinatorial-game
  presentations forbid moving the marker to a cell from which neither goal is
  still reachable (to keep it a "last player to move wins" CGT game). This port
  does not enforce that extra restriction — it keeps the rule set minimal and
  relies on the trapped-loses rule for termination.

## Source

- BoardGameGeek: <https://boardgamegeek.com/boardgame/31467/slimetrail>
- Rules summaries: gamecabinet.com, Mancala World wiki, bodogemu.com,
  combinatorialgametheory.blogspot.com.
