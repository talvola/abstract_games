# Avalanche Chess

Invented by **Ralph Betza (1977)**. A *Recognized Chess Variant* on
chessvariants.com and one of the most popular games of the NOST postal
chess-variant circuit. Rules implemented from the authoritative page
[chessvariants.com/mvopponent.dir/avalanche.html](https://www.chessvariants.com/mvopponent.dir/avalanche.html),
cross-checked against Wikipedia's *Avalanche chess* article — the two agree on
every point below.

## Rules as implemented

Orthodox chess (standard setup, castling, promotion, checkmate/stalemate,
fifty-move and threefold-repetition draws), with these changes:

1. **Each turn has two parts.** First a regular move, legal by orthodox rules.
   Then you must **push one enemy pawn one square straight forward** — *its*
   forward, i.e. toward you and toward its promotion rank. The push is never a
   capture (the square ahead must be empty) and is never a double step.
2. **The push is obligatory** — unless, after your regular part, the opponent
   has *no* pawn with an empty square directly ahead; then your turn is the
   regular move alone. (Your regular move can create or destroy pushes, e.g.
   by blocking a pawn or capturing the last one.)
3. **The regular part alone must leave your king safe.** "One cannot place
   with the first part of a move one's king in check, or leave it in check,
   planning to undo the check with a pawn move."
4. **A self-checking push loses instantly.** "When a player advances a pawn,
   such that this places his king in check, he loses the game … *even when he
   checks or mates his opponent in that turn*." A push can expose your own
   king (the pushed pawn attacks a new pair of squares, or its old square
   opens an enemy line). Such pushes are **legal moves that lose on the spot**
   — implemented exactly as the source words it, so a player whose every
   available push self-checks is lost even if the regular part delivered mate.
   (Wikipedia states the same rule from the other side: "If every legal pawn
   move forward gives check, then the opponent wins immediately.") Careful:
   the UI will let you click a losing push.
5. **Push-promotion: the pawn's OWNER chooses the piece.** A pawn pushed to
   its last rank promotes, and "the owner of the pawn decides in what type of
   piece it is promoted" — as a separate choice (Q/R/B/N buttons) made at the
   start of the owner's turn, before their own regular move. "When this means
   a check to the player advancing the pawn, he loses": if the chosen piece
   checks the pusher, the pusher loses immediately (so the owner will always
   pick a checking piece when one exists).
6. **There is no en passant capture** (pawn double steps still exist; a pushed
   pawn has left its home rank and so loses its own double step).
7. A push may give **discovered check to the opponent** (vacating the pushed
   pawn's square can open one of your lines); check and mate are evaluated on
   the position after the *complete* turn — a push can even block or unblock
   what would otherwise be mate.

Checkmate and stalemate are orthodox and are judged at the start of a turn:
no legal regular move while in check loses; while not in check it is a draw.
Draws: fifty-move rule, threefold repetition, insufficient material, and a
600-ply safety cap. (Pushes are pawn advances, so the fifty-move clock resets
nearly every turn while pawns can still move.)

## Variant option

**Balanced Avalanche** (Alessandro Castelli, documented on the same page):
identical, except White's very first turn has **no push**, reducing White's
large opening advantage. Selectable via the *Variant* dropdown.

## Move encoding

- Compound turn: a 4-cell path `from>to>pushFrom>pushTo`, e.g.
  `4,1>4,3>6,6>6,5` = *1.e4 / push g6*. Click your move's from/to, then the
  enemy pawn and its square ahead.
- No push available: the plain 2-cell `from>to`.
- Your own pawn promoting on the regular part: trailing `=Q/=R/=B/=N`
  (standard picker).
- Push-promotion choice (by the pawn's owner, at the start of their turn):
  the bare moves `=Q` / `=R` / `=B` / `=N`, shown as buttons.

## Correctness anchors (asserted in selftest.py)

- **Opening: 160 turns** = 20 orthodox moves × 8 pushes (no White first move
  blocks a black pawn's advance square — those squares are on rank 6 — and no
  push can self-check at ply 1).
- **After 1.a3 / push a6: 152** = 19 × 8 — Black's orthodox 20 minus a7-a6/a5
  and minus Nb8-a6 (blocked by the pushed pawn), plus a6-a5 and Ra8-a7.
- **After 1.Nf3 / push e6: 209** = 30 regulars (the freed e7 square adds
  Qe7/f6/g5/h4, Be7-a3, Ke7, Ne7… net +10, minus the e-pawn's lost double
  step) × 7 pushes (f2 is blocked by the knight on f3), **minus 1** because
  the regular Bf8-a3 itself lands on a3 and blocks the a2-a3 push.
- **perft(2) = 27,488** (frozen regression value for this implementation).
- Rule positions: mandatory vs unavailable push, self-check push = immediate
  loss (and blocking the only push to avoid it), owner's push-promotion
  choice with the pusher-checked loss, discovered check by a push, absence of
  en passant, threefold repetition.
