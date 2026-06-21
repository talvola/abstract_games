# Three-Check Chess

Standard chess on an 8×8 board, with one extra way to win: **deliver three checks**.

## Objective
Win by either of:
- **Checkmate** the opponent's king (as in normal chess), **or**
- **Giving check three times** in total over the course of the game.

The two are tracked independently — most games are decided by the third check long before a checkmate.

## Board, setup & movement
Identical to standard chess. Pawns on the second rank, `R N B Q K B N R` behind them. White is player 1 and moves first; Black is player 2. All pieces move exactly as in standard chess, including:

- **Castling**, king- and queen-side (with the usual rights and "not through, into, or out of check" restrictions).
- **En passant** capture.
- **Pawn double-step** from the starting rank, and **promotion** to Q/R/B/N on the last rank.

Because movement is unchanged, the set of legal moves in any position is exactly the same as in standard chess (opening move counts: 20, 400, 8902 at depths 1/2/3).

## The check counter
Each side has a counter, shown in the caption as `checks W:n B:n`.

- A move **gives check** when it leaves the opponent's king attacked after the move is complete. Each such move adds **one** to the moving side's counter — regardless of *how* the check is delivered (direct, discovered, or double check all count as exactly **one**).
- The moment a side's counter reaches **3**, that side wins immediately. This takes priority even over a position that would otherwise be a draw (e.g. a move that simultaneously gives the third check and reaches a repetition still wins).
- A checkmate is also a check, so a mating move both ends the game by mate and would be the third such check in a game already at two checks — either way the mating side wins.

## Winning & draws
- **Three checks** wins. **Checkmate** wins.
- **Stalemate** (no legal move while not in check) is a draw.
- Also drawn by the **fifty-move rule**, **threefold repetition**, and **insufficient material** — *unless* a side has reached three checks, which always wins first.

## Ruleset choices made in this implementation
- A **double check counts as one check**, not two (this is the standard Three-Check / chess.com convention). The counter is incremented per *move that leaves the enemy king in check*, not per attacking piece.
- The check counters are part of the saved game state and round-trip through serialization.
- All draw rules from standard chess are retained, but the three-check win is evaluated first.

## Entering moves
Castling is entered as the king's two-square move; the rook follows automatically. Promotion shows a Q/R/B/N picker.
