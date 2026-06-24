# Seirawan Chess

Seirawan Chess (S-Chess / S-HARP), by **Yasser Seirawan** and **Bruce Harper**
(2007), is standard chess plus two extra pieces that start *off the board* and
enter through a mechanic called **gating**.

These are the rules **as implemented** in this package.

## Standard chess applies

The board, the starting position, and all ordinary chess rules are unchanged:

- Pieces move and capture exactly as in chess.
- **Castling**, **en passant**, and the pawn **double-step** all work normally.
- You may never make a move that leaves your own king in check. **Checkmate**
  wins; **stalemate** is a draw.

## The two new pieces

Each player holds one of each in reserve at the start:

- **Hawk (H)** moves as a **Bishop or a Knight** (the bishop+knight compound).
- **Elephant (E)** moves as a **Rook or a Knight** (the rook+knight compound).

The Hawk and the Elephant are shown in the **reserve trays** above and below the
board.

## Gating — how the Hawk and Elephant enter

Gating is the signature rule:

- The **first time** you move one of your **original back-rank pieces** (or when
  you **castle**), you **may** simultaneously place a Hawk or an Elephant from
  your reserve onto the square that piece just **vacated**. The gated piece
  appears as the *second half of the same turn*.
- Gating is **optional** on every such move. Each gate piece can be introduced
  **only once**.
- **You lose the right once a square's piece leaves without gating.** If an
  original back-rank piece moves off (or is captured on) its home square without a
  piece being gated there, that square can never gate again. If you develop every
  back-rank piece without gating, you forfeit the chance entirely.
- **Castling.** Castling vacates **both** the king's and the rook's home squares.
  You may gate **one** piece onto **either** the king's or the rook's vacated
  square — but not onto both in the same turn.
- **You may not gate to block a check.** You cannot gate while your king is in
  check (just as you cannot castle out of check). A gated piece **may** itself
  give check, and may even deliver **checkmate**.
- Normal king-safety still applies to the resulting position: a move-plus-gate is
  legal only if your king is not left in check afterward. (A gated piece sits on
  the square you just vacated, so it can never expose your own king — the gating
  variants are legal exactly when the bare move is.)

## Pawn promotion

A pawn reaching the far rank promotes. It may promote to a **Queen, Rook, Bishop,
or Knight** as usual, and **additionally** to a **Hawk or Elephant — but only if
that piece is still in your reserve**. Promoting to a Hawk or Elephant **removes
it from your reserve**, so it can no longer be gated.

## Draws

Standard chess draws apply:

- **Threefold repetition** — the same position (board, reserves, gating rights,
  and side to move) occurring three times.
- **The fifty-move rule** — 100 half-moves with no capture and no pawn move.
- **Stalemate** — the side to move has no legal move and is not in check.

A hard ply cap also forces a draw in the rare event a game runs extremely long.
There is no "insufficient material" draw while gate pieces remain in reserve.

## Notation / how to play in the app

A normal move is a path (e.g. `e2-e4`). A move that gates is the same move with a
gate choice attached — in the app, when you make a back-rank piece's first move
(or castle) and you still have a Hawk or Elephant in reserve, a small **picker**
appears letting you choose *no gating*, *Gate Hawk*, or *Gate Elephant* (and for
castling, also the rook-square variants). Pawn promotion uses the same picker to
choose the promotion piece (including Hawk/Elephant when still in reserve).

In move notation a gate is written after the move with a slash, e.g.
`Nb1-c3/Ha1` means "knight b1–c3, gating a Hawk onto b1" (the vacated square).
