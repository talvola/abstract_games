# Shatar (Mongolian Chess)

Shatar is the traditional chess of Mongolia, a direct descendant of medieval
shatranj. It looks like chess — same board, almost the same army — but wins are
governed by a unique classification of checks: not every mate wins.

## Board and setup

8×8 board, orthodox chess array with the Bers on the queen's square:
R N B J K B N R with a rank of pawns — except that the **obligatory opening
moves 1.d4 d5 are already played**: the game legally *must* begin with each
side advancing its queen's pawn two squares, so (following Fairy-Stockfish)
this position is the starting position and White is on move. White (player 0)
moves first.

## Pieces

- **Noyon (King, K)** — as in chess. **No castling.**
- **Bers (J)** — the queen: moves like a chess **rook, or one square
  diagonally** (shogi's promoted rook / dragon king).
- **Terge (Rook, R)**, **Teme (Bishop, B)**, **Mori (Knight, N)** — exactly as
  in chess.
- **Khuu (Pawn, P)** — one square straight forward, captures one square
  diagonally forward. **No double step** (the pre-played d-pawns made the
  game's only double step) and **no en passant**. On reaching the last rank a
  pawn **must promote to a Bers**.

## Checks: shak, tuk, zod

- A check by the **Bers, Rook or Knight** is a **shak**.
- A check by the **Bishop** is a *tuk*; a check by a **Pawn** is a *zod*.

## Winning and drawing

- **Checkmate wins only "with shak"**: the mate must come at the end of an
  *unbroken series of checks* (the mating check itself counts) that contained
  **at least one shak**. Example: knight check, then pawn check, then a bishop
  mate = win, because the series contained a shak. If the opponent gets a move
  while *not* in check, the series restarts.
- **Niol**: a mate whose check series contained no shak (bishop/pawn checks
  only) is a **draw**.
- **Forbidden knight mate**: a mate whose final check is delivered *only* by a
  knight is illegal — delivering it **loses** (the mated player wins). This
  follows Fairy-Stockfish; see "Interpretations" below.
- **Robado**: the moment either player is reduced to a **lone king**, the game
  is an immediate **draw** — even if the baring capture would otherwise be
  mate.
- **Stalemate is a draw.**
- Draws also by **threefold repetition**, the **50-move rule** (100 halfmoves
  with no pawn move or capture), and a hard 600-ply cap (termination backstop).

## Interpretations / deviations (as implemented)

This implementation follows **Fairy-Stockfish's `shatar` variant** exactly (it
was verified move-for-move and result-for-result against it), which encodes
the traditional ("old") rules described by Wikipedia and chessvariants.com:

- **Prescribed opening**: Wikipedia notes some sources let the *e*-pawn open
  instead; Fairy-Stockfish (and this implementation) bakes the mandatory
  1.d4 d5 into the initial position.
- **Knight mate**: the sources say a knight "cannot deliver mate".
  Fairy-Stockfish resolves what happens if it is played anyway: the mater
  *loses*. We match that. (Note the knight still counts as a *shak* checker
  earlier in a check series.)
- **Bare king**: old shatar rules make baremate a draw; Fairy-Stockfish ends
  the game immediately as a draw when either side is bared, and so do we.
  ("Modern" shatar — knight mates allowed, queen-Bers — is not implemented.)
- **Promotion**: only to a Bers (the old "half-power/all-power tiger"
  distinction is not implemented, matching Fairy-Stockfish).
- The traditional *tuuxəi* scoring of consecutive checks is a wager/komi
  custom, not a game rule, and is not implemented.

## Sources

- [Wikipedia: Shatar](https://en.wikipedia.org/wiki/Shatar)
- [chessvariants.com: Shatar — Mongolian Chess](https://www.chessvariants.com/oriental.dir/shatar.html)
- [Fairy-Stockfish `shatar` variant](https://github.com/fairy-stockfish/Fairy-Stockfish) (differential oracle)
