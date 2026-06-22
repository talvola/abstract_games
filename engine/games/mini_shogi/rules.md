# Mini Shogi (5×5)

Mini Shogi (Gotenshogi), devised by Shigenobu Kusano in 1970, is Shogi compressed
onto a **5×5** board. All the Shogi rules apply — including **drops** — so see the
Shogi rules for the full detail; this page lists only what differs.

## Pieces

Each side has just **six** pieces, all on the home rank plus one pawn:

- King (K), Gold (G), Silver (S), Bishop (B), Rook (R), and one Pawn (P).

There are **no Lances or Knights**. The pieces move exactly as in Shogi (Gold and
the promoted minor pieces move like a gold; the promoted Rook/Bishop gain the
king's other steps).

## Setup

```
R B S G k     ← White (Gote), top
. . . . p
. . . . .
P . . . .
k G S B R     ← Black (Sente), bottom
```

Each side's King starts in a **corner**, with the home rank running King–Gold–
Silver–Bishop–Rook, the two armies rotated 180° from each other, and one Pawn in
front of each King. **Black (Sente) moves first.**

## Promotion

The **promotion zone is only the single farthest rank** (rank 5 from your side). A
piece that moves into that rank may promote (a Pawn reaching it must). Otherwise
promotion works exactly as in Shogi.

## Drops, captures, winning, draws

Identical to Shogi: a captured piece switches colour and goes to your hand, to be
dropped (unpromoted) on a later turn, subject to the two-pawns (*nifu*), last-rank
and drop-mate (*uchifuzume*) rules. **Checkmate wins.** Repetition (the same
position four times) is a **draw**, and a ply cap guarantees termination. The
perpetual-check and impasse refinements are simplified exactly as in the Shogi
package.

## Notation

As in Shogi: board moves are `from>to` (append `=+` to promote), drops are
`L@c,r`.
