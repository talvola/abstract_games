# Marseillais Chess

**Marseillais Chess** is chess in which **each player makes two moves per turn**.
It appeared in Marseille in the 1920s. This module implements the **Balanced
Marseillais** ruleset — the standard, tournament-accepted version (introduced by
Robert Bruce in 1963 and famously endorsed by Bobby Fischer).

## The turn structure (Balanced)

- **White's very first turn is a single move.**
- **Every turn after that is two moves.**

So play proceeds:

> White · **Black Black** · **White White** · **Black Black** · **White White** · …

Balancing the opening removes White's otherwise near-winning double-tempo (in the
unbalanced game White's two opening moves can be crushing). In this platform a
turn is simply several sub-moves in a row: the same player keeps moving until the
turn's move budget is spent, then it becomes the opponent's turn. You will see
"*N* moves left this turn" in the status line.

During your turn you may move **the same piece twice** or **two different pieces**.

## Making moves

Moves are identical to standard chess (click a piece, then its destination).
Promotion offers a Q/R/B/N picker. Castling is the king's two-square move (the
rook follows automatically) and **counts as a single one of your two moves**.

## Check rules (the heart of Marseillais)

These are what make the variant tactical and sharp:

1. **Your king may never be left in check after *either* of your sub-moves.** You
   cannot move your king into check on your first move and then out of it on your
   second — every sub-move must leave your own king safe.
2. **Giving check ends your turn immediately.** If your *first* move gives check,
   you do **not** get your second move.
3. **If you are in check at the start of your turn, you must escape the check on
   your first move.**

### Checkmate and stalemate

- **Checkmate** is *ordinary*: you are in check and have **no move that gets your
  king to safety**. Because giving check ends the opponent's turn, your opponent
  can never actually capture your king — so mate is simply "in check and cannot
  get out on your first move." Checkmate loses the game.
- **Stalemate** — no legal move while **not** in check — is a **draw**.
- Draws also occur by the fifty-move rule, threefold repetition (the repeated
  position includes whose turn it is and how many sub-moves remain), and
  insufficient material.

## En passant

- A pawn that advanced two squares — on **either** sub-move of a turn — may be
  captured *en passant* by the opponent.
- An en-passant capture must be made on the **first** sub-move of the capturing
  turn.
- **Implementation note / simplification:** because *en passant* must be played
  on the first sub-move, at most one pawn can be captured *en passant* per turn.
  The rare case of two enemy pawns both double-stepping in one turn and *both*
  being captured *en passant* in the reply is **not** supported.

## The classic (unbalanced) alternative

In the original **unbalanced** Marseillais chess, **White also makes two moves on
the first turn** (order: White White · Black Black · …). This version is generally
considered close to winning for White — hence the balanced rule above became
standard. This module ships **only the Balanced version**.

## Faithfulness summary

Implemented exactly per the standard Balanced Marseillais rules:
one-move White opening then two-move turns; king never in check between your
moves; giving check ends the turn; must escape check on the first move; ordinary
checkmate; stalemate/50-move/repetition/insufficient-material draws; castling as a
single move. En passant is supported with the one documented simplification above.
