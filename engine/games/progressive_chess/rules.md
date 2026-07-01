# Progressive Chess (Italian rules)

Progressive Chess (Italian: *Scacchi progressivi*) is standard chess with one big
twist: instead of one move per turn, each player plays a **series** of moves that
grows by one every turn.

## The progression

- Turn 1: **White** plays **1** move.
- Turn 2: **Black** plays **2** moves.
- Turn 3: **White** plays **3** moves.
- Turn 4: **Black** plays **4** moves.
- ...and so on: the series length of turn *N* is *N*.

You play your moves one at a time; while it is still your series the board simply
stays on your side and you keep moving. When your series is spent, it becomes the
other player's turn (with one more move than you just had).

## Movement

All pieces move exactly as in standard chess. **Castling**, **en passant** and
**pawn promotion** (to Q/R/B/N) are all allowed and use the normal rules. A move
is entered as a from-cell to-cell path (e.g. `e2>e4`); a promotion appends the
piece, e.g. `e7>e8=Q`.

## The check rules (this is what makes it Italian)

1. **A check may be given only on the *last* move of a series.** Putting the
   enemy king in check on any earlier move of your series is illegal. (On turn 1,
   which is a single move, that one move *is* the last move, so White may check.)
2. **You may never leave your own king in check** after any of your moves — not
   even between your own moves. Every sub-move must be fully legal with respect to
   your own king.
3. **If you are in check at the start of your turn, you must escape the check on
   your very first move.** If you cannot, it is checkmate.

### Checkmate and "progressive checkmate"

You are **checkmated** if it is the start of your series, you are in check, and you
have **no legal first move** that gets you out of check.

Because a first move of a multi-move series may not give check (rule 1), a special
case arises: if the *only* ways to escape the check would themselves deliver
check, all of them are illegal — so you have no legal first move and you lose by
**progressive checkmate**, even though a "get out of check" move exists on the
board.

### Stalemate

If at the start of your turn you are **not** in check but have **no legal first
move**, the game is a **draw** by progressive stalemate.

### Finishing your series

You must keep making moves while a legal move exists. If part way through your
series you run out of legal continuations (for example, every remaining move would
give check on a non-final move), your **turn simply ends early** — this is *not* a
loss. Only being unable to make the *first* move while in check is checkmate.

## Draws (as implemented)

Besides stalemate, the game is drawn by:

- the fifty-move rule (100 half-moves with no capture and no pawn move),
- threefold repetition of the position (including whose turn and how far into the
  series it is),
- a hard move cap to guarantee the game ends.

Insufficient-material is **not** an automatic draw here: with a long series of
moves a mate can be forced with very little material.

## Implementation notes / interpretations

- **En passant across a series.** The right to capture en passant is preserved
  only when the pawn's double-step was the **last** move of the previous series
  (so the opponent may take it on the first move of theirs). A double-step made
  earlier in a series does not leave an en-passant target.
- Stalemate is scored as a **draw**, following the Italian convention. (Some
  variants score progressive stalemate as a loss; this package does not.)

The implemented rules follow Wikipedia's "Progressive chess" article and
chessvariants.com; the Italian ruleset is used.
