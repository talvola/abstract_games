# Pocket Knight Chess

Also known as **Tombola** or simply **Pocket Knight**. It is ordinary chess plus
one twist: each player has a single extra knight "in pocket" that can be dropped
onto the board once during the game.

## Standard chess

The board, the setup, and every rule of orthodox chess apply unchanged:

- Standard 8x8 board, standard starting position; White (player 0) moves first.
- Normal moves for all pieces, **castling**, **en passant**, pawn **double-step**,
  and **promotion** to Q/R/B/N.
- **Check**, **checkmate** and **stalemate** as usual.
- Draws by the **fifty-move rule**, **threefold repetition**, and stalemate.

## The pocket knight

- Each side begins with **exactly one knight in hand** (the "pocket knight"),
  shown in a reserve tray (player 1 above the board, player 0 below).
- On any turn, **instead of** moving a piece on the board, a player may **drop**
  their pocket knight onto **any empty square**. The drop is the entire turn.
- A drop is written `N@c,r` (place the knight on cell `c,r`). In the UI you click
  your knight chip in the reserve tray and the legal empty target squares light up.
- As with every move, the **dropping player's own king may not be left in check**.
- A dropped knight is an ordinary knight from that moment on.
- Each player may do this **only once** for the whole game: after the drop, that
  side's reserve is empty and is **never** replenished.

### Captures do not refill the pocket

Unlike Crazyhouse, captured pieces are **never** added to a reserve. The pocket
knight is a one-time resource. Capturing enemy pieces does nothing to your hand.

### Dropping to give check or checkmate

A pocket-knight drop **may give check and may deliver checkmate**. The only
restrictions are that the target square is empty and the mover's own king is not
left in check — exactly the constraints on any other move. This follows the
standard published rule (chessvariants.com, "Pocket Knight"). A few casual
variants forbid mate-by-drop; this implementation does **not** adopt that
restriction.

## Implementation notes / interpretations

- Because reserve material exists, the engine does not award **draws by
  insufficient material** while the shared drops framework is active (captured
  material could in principle re-enter — though here only via the one-time pocket
  knight). In practice king-vs-king with both pockets spent will instead draw by
  the fifty-move or repetition rules.
