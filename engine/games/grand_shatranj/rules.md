# Grand Shatranj

Joe Joyce's 10×10 all-short-range chess (2006): the power pieces of early
shatranj strengthened with extra short moves instead of ever becoming sliders.
This is the author's primary **"Grand Shatranj D"** setup.

## Board & setup (10×10)

- **Rank 1 / rank 10:** a **Lightning War Machine (W)** in each corner (a1, j1 / a10, j10).
- **Rank 2 / rank 9**, files b–i: **N O J K M H O N** (kings on the e-file for both sides).
- **Rank 3 / rank 8:** ten pawns.

## Pieces

- **King (K)** — royal; one step in any direction. May not move into check.
- **Jumping General (J)** — one step in any direction, **or** a jump of exactly 2 squares orthogonally or diagonally (may leap over anything).
- **Minister (M)** — steps 1 or jumps 2 squares **orthogonally**, or leaps like a knight.
- **High Priestess (H)** — steps 1 or jumps 2 squares **diagonally**, or leaps like a knight.
- **Knight (N)** — standard chess knight.
- **Oliphant (O)** — a double elephant-rider: moves **once or twice in a straight diagonal line**, each leg a 1-square step or a 2-square jump (so 1–4 squares total). Jumped-over squares may be occupied, but an intermediate *landing* square must be empty — capture is by replacement and ends the move.
- **Lightning War Machine (W)** — the orthogonal twin of the Oliphant: one or two wazir-steps / 2-square jumps along a single **orthogonal** line (1–4 squares).
- **Pawn (P)** — steps 1 forward, captures 1 diagonally forward. **No double step, no en passant.**

## Promotion

- A pawn may promote only to a piece type its owner has **lost**.
- Promotion is **optional on the 9th rank** and **mandatory on the 10th**.
- A pawn reaching the 10th rank with no lost piece available stays a pawn ("stranded") and may **move or capture one square sideways** along the back rank each turn; once a piece type has been lost, any later sideways move may carry a promotion.

## Winning & draws

- **Checkmate** wins.
- **Baring** wins: capturing your opponent's last man (leaving the bare king) wins — *unless* the bared king can immediately capture your own last man in reply, in which case the game is a **draw** (implemented by declaring the draw at once, since the counter-capture is the bared side's only non-losing option).
- Stalemate, threefold repetition, 50 moves without a capture or pawn move, and king-vs-king are **draws**. A long-game ply cap also scores a draw.

## Implementation notes / interpretations

- The **"R" variant** (standard rooks in the corners instead of War Machines) and the optional pawn-double-step rule from the source page are **not implemented** — this is the primary "D" game as described by the author.
- A stranded pawn promotes **via a sideways move** once a piece is available; the source's "may promote immediately" (in place, without moving) is not offered, and a stranded pawn is allowed to keep declining promotion while shuffling.
- The counter-bare exception is resolved immediately as a draw rather than playing out the forced capture.

Source: <https://www.chessvariants.com/rules/grand-shatranj>
