# Checkless Chess

Standard chess on an 8×8 board, with a single added restriction on giving check.

## The one new rule
**You may not make a move that gives check to the opponent's king — *unless* that move is checkmate.**

So the only check you are ever allowed to deliver is a mating check. Any other checking move is illegal and is simply not offered. This applies to *every* kind of check, including a **discovered check** or a **double check**: if the move leaves the opponent in check and it is not mate, the move is forbidden.

## Consequences
- The enemy **king becomes a powerful piece**: because you can't check it, it can safely walk into squares that *would* be attacked, and march up the board.
- **Mating is harder**: you can't use checks to chase or reposition the enemy king, so you must arrange the mate in one stroke.

## Everything else is standard
- Pieces move exactly as in standard chess (king, queen, rook, bishop, knight, pawn).
- **Castling** (king- and queen-side, with the usual "not through, into, or out of check" rules), **en passant**, the pawn **double-step**, and **promotion** to Q/R/B/N all work normally.
- **Checkmate** wins. **Stalemate** (no legal move while not in check) is a draw — and note this now also covers the case where your only king-safe moves would each give a non-mating check: with no legal move and not in check, it is stalemate.
- Drawn also by the **fifty-move rule**, **threefold repetition**, and **insufficient material**.

## Implementation notes (rules as implemented)
- A move is legal iff it is legal in ordinary chess (your own king ends up safe) **and** it does not leave the opponent in check unless that check is checkmate.
- **"Is it checkmate?"** is judged by the *ordinary-chess* definition: the check is mate iff the opponent has no ordinary-chess move that gets their king to safety. In particular, an escape that itself gives check back (a *cross-check*) **does** count as a legal escape, so such a position is **not** mate and the original checking move is therefore illegal. (Some sources describe an alternative "cross-checks don't count" reading; this implementation uses the standard-mate definition.)
- Castling is entered as the king's two-square move; the rook follows automatically. Promotion shows a Q/R/B/N picker.
