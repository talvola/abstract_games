# King of the Hill

A chess variant: ordinary chess, with one extra, faster way to win.

## Objective
Win by **either**:
- **Checkmate** — the opponent's king is attacked and cannot escape (as in standard chess); or
- **King of the hill** — move your own king onto one of the four central squares **d4, d5, e4 or e5**. The instant your king arrives there by a legal move, the game ends and you win.

## Board & setup
The standard chess array on an 8×8 board: pawns on the second rank, R N B Q K B N R behind them. White is player 1 and moves first; Black is player 2. The four central squares are highlighted as "the hill".

## Play
Every piece moves exactly as in standard chess (king, queen, rook, bishop, knight, pawn), with all the special rules:
- **Castling**, king- and queen-side (usual rights, and the "not through, into, or out of check" restrictions).
- **En passant** capture.
- **Pawn double-step** from the starting rank, and **promotion** to Q/R/B/N on the last rank.

The set of legal moves is **identical to standard chess** — the centre win changes only *when the game ends*, never *which moves are allowed*.

## Winning & draws
- **Checkmate** wins, as usual.
- **King of the hill** wins: the moment your king is on d4, d5, e4 or e5 at the end of your move, you win immediately. Because a king may never move into check, the centre square must be reached by a normal *legal* king move (you cannot run your king into the centre through a check).
- **Stalemate** (no legal move while not in check) is a draw.
- Also drawn by the **fifty-move rule**, **threefold repetition**, and **insufficient material**.

## Ruleset choices (as implemented)
- The four hill squares are exactly **d4 / d5 / e4 / e5** (engine 0-based coordinates: cols 3–4, rows 3–4). This matches the chess.com / Lichess "King of the Hill" variant.
- The centre win is checked **after** each move: a king sitting on the hill at the start of the side-to-move's turn ends the game in favour of the king's owner. Reaching the hill always takes priority over anything else (it can only be reached by a legal, non-self-check move, so it is never in conflict with being checkmated/stalemated on the same move).
- All draw and termination rules are inherited unchanged from the standard-chess core (`agp.chesslike`), including a hard ply cap to guarantee termination.

## In this implementation
- Castling is entered as the king's two-square move; the rook follows automatically. Promotion shows a Q/R/B/N picker. The hill squares are highlighted on the board.
