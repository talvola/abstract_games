# Los Alamos Chess

A simplified 6×6 chess (Stein & Wells, MANIAC I, 1956) — the first chess-like game played by a computer.

## Objective
Checkmate the opponent's king.

## Board & setup (6×6)
Back rank: **R N Q K N R** (no bishops). Pawns on the second rank. White moves first.

## Differences from standard chess
- 6×6 board, **no bishops** (the queen still moves in all eight directions).
- **No castling**, **no double pawn step**, and therefore **no en passant**.
- Pawns promote on the far rank to **Queen, Rook, or Knight**.

## Winning & draws
Checkmate wins; stalemate is a draw. A no-progress rule and a ply cap also force a draw to guarantee the game ends.
