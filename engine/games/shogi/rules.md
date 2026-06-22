# Shogi (Japanese chess)

Shogi is played on a 9×9 board. Its signature is the **drop**: a captured piece
switches sides and can be returned to the board as your own. These are the rules
**as implemented** here. Sente (Black, player 1) sits at the bottom and moves
first; Gote (White, player 2) is at the top.

## Pieces and how they move

Each side starts with a King (K), Rook (R), Bishop (B), two Golds (G), two
Silvers (S), two Knights (N), two Lances (L), and nine Pawns (P). "Forward" is
toward the opponent.

- **King** — one square any direction.
- **Rook** — any distance orthogonally. **Bishop** — any distance diagonally.
- **Gold** — one square orthogonally or one square forward-diagonally (six
  squares; not the two back-diagonals).
- **Silver** — one square diagonally or one square straight forward (five
  squares).
- **Knight** — jumps to the two squares two-forward-and-one-to-the-side (only
  forward, and it jumps over pieces).
- **Lance** — any distance straight forward.
- **Pawn** — one square straight forward. It captures the same way it moves (no
  diagonal capture, no double step, no en passant).

## Promotion

The **promotion zone** is the farthest three ranks from your side. A piece that
**moves into, out of, or within** the zone *may* promote at the end of that move.
Promotion is optional **except** when the piece could otherwise never move again,
where it is **mandatory**: a Pawn or Lance reaching the last rank, or a Knight
reaching the last two ranks.

Promoted pieces:

- **Promoted Pawn/Lance/Knight/Silver** (+P, +L, +N, +S) all move exactly like a
  **Gold**.
- **Promoted Rook** (+R, the *Dragon King*) — a Rook that may also step one
  square diagonally.
- **Promoted Bishop** (+B, the *Dragon Horse*) — a Bishop that may also step one
  square orthogonally.

King and Gold never promote.

## Drops

When you capture a piece it **flips to your colour and goes to your hand**
(a promoted piece reverts to its unpromoted type). On your turn, instead of
moving a piece on the board, you may **drop** a piece from your hand onto any
empty square, where it arrives **unpromoted**. Restrictions:

- **No pawn on a file that already holds one of your unpromoted pawns** (*nifu*,
  the two-pawns rule).
- **A pawn or lance may not be dropped on the last rank**, and **a knight may not
  be dropped on the last two ranks** (it would have no move).
- **A pawn may not be dropped to give immediate checkmate** (*uchifuzume*).
  (Dropping a pawn to give *check* is fine — only an immediate mate is illegal.)
- A drop may not leave your own king in check.

## Winning, check, and draws

You may not make any move that leaves your own king in check. **Checkmate wins**
(the side to move with no legal move — including no legal drop — loses).

**Repetition (*sennichite*):** if the same position (board, both hands, and side
to move) occurs a fourth time, the game is a **draw**.

### Documented simplifications

- The **perpetual-check** exception to sennichite (a player who gives continuous
  check through the repetition loses rather than drawing) is **not** implemented —
  a four-fold repetition is always scored a draw here.
- **Impasse / jishogi** (the both-kings-in-the-promotion-zone entering-king
  endgame decided by a piece-point count) is **not** implemented; such games run
  to repetition or the ply cap. These endings are rare in casual play.
- A hard ply cap also forces a draw in the extremely rare event a game runs very
  long, guaranteeing termination.

## Notation

A board move is a path like `7,2>7,3`; append `=+` to promote (the app shows a
**Promote / Don't promote** picker when both are legal). A drop is written
`P@4,4` ("drop a pawn"); in the app you click a piece in your reserve tray, then
an empty square.
