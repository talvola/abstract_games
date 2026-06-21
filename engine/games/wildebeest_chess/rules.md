# Wildebeest Chess

R. Wayne Schmittberger's large-board chess variant (1987), played on an
**11×10** board (11 files **a–k**, 10 ranks **1–10**). It adds two *leapers* so
that each side balances its three long-range *riders* (queen + two rooks... and
two bishops) against three leapers (two knights, two camels) plus a compound of
each family — the wildebeest.

## Objective
Checkmate the opponent's king.

## The new pieces
- **Camel (C)** — a **(1,3) leaper**: it jumps to a square 1 away on one axis and
  3 on the other (a 2×4 rectangle), leaping over anything in between. Like a
  bishop it is **colour-bound** (it never changes square colour).
- **Wildebeest (W)** — moves as **a knight *or* a camel**: any (1,2) or (1,3)
  leap. It is the only piece that can reach every square of the board.

All other pieces (King, Queen, Rook, Bishop, Knight, Pawn) move exactly as in
orthodox chess.

## Board & starting position
The opening array is **point-symmetric** (a 180° rotation maps one army onto the
other), with the kings facing each other on the **f-file** and pawns on the
mover's second rank:

```
   a  b  c  d  e  f  g  h  i  j  k
10 r  n  c  c  w  k  q  b  b  n  r     <- Black back rank (rank 10)
 9 p  p  p  p  p  p  p  p  p  p  p     <- Black pawns
 ...
 2 P  P  P  P  P  P  P  P  P  P  P     <- White pawns
 1 R  N  B  B  Q  K  W  C  C  N  R     <- White back rank (rank 1)
```

- **White rank 1:** R N B B Q K W C C N R
- **Black rank 10:** R N C C W K Q B B N R

So White's king is on **f1**, queen on **e1**, wildebeest on **g1**, camels on
**h1/i1**; Black's king is on **f10**, queen on **g10**, wildebeest on **e10**,
camels on **c10/d10**. (Source: Wikipedia / The Chess Variant Pages.)

## Pawns (as implemented)
- A pawn advances **straight forward any number of empty squares, as long as the
  destination stays in its own half of the board** (White: ranks 1–5; Black:
  ranks 6–10). From its starting rank a pawn can therefore step 1, 2, 3 or 4
  squares; deeper in its own half it has fewer options; once it must cross the
  midline it advances **one square at a time**.
- A pawn **captures one square diagonally forward** (it cannot capture straight
  ahead), and **promotes** on reaching the far rank.
- **En passant (multi-square):** when a pawn makes a multi-square advance, an
  enemy pawn that could have captured it on *any square it passed over* may do so
  — moving diagonally onto that skipped square and removing the advanced pawn —
  but **only on the immediately following move**.

> Note on sources: descriptions of the Wildebeest pawn vary (some phrase it as a
> graduated "first move ≤3, then ≤2, then 1" rule). This package uses the
> equivalent, cleaner **"any distance within your own half"** formulation
> (Wikipedia), which yields the same reachable squares from the opening and needs
> no per-pawn move-count bookkeeping.

## Castling — omitted
This package **does not implement castling**. Wildebeest Chess's authentic
castling rule on the wide 11-file board (how far the king slides, and exactly
where the rook lands) is poorly and inconsistently sourced, so rather than ship a
subtly-wrong rule we leave castling out — consistent with the platform's other
wide variants (Grand Chess, Courier Chess), which also omit it. Everything else
(the leapers, the multi-step pawn, en passant, promotion, check/mate) is faithful.

## Promotion
A pawn reaching the last rank promotes — **only to a Queen or a Wildebeest**
(your choice). Promotion is mandatory.

## Winning & draws
- **Checkmate wins.**
- **Stalemate** is, by default, a **draw** (orthodox handling, matching this
  task's brief). The *authentic* Schmittberger rule makes **stalemate a win for
  the stalemating side**; that variant is available via the **Stalemate** option
  (set it to *"Wins for the stalemating side"*).
- The game is also drawn by the **fifty-move rule**, **threefold repetition**,
  **insufficient material**, or a safety **ply cap** (to guarantee termination).

## Documented choices (where sources differ)
1. **Pawn advance:** implemented as "any distance while staying in your own
   half" (Wikipedia) rather than the graduated count-based phrasing; identical
   from the start, simpler to reason about.
2. **En passant:** implemented for the multi-square advance on *every* skipped
   square, available the next move only.
3. **Castling:** omitted (uncertain authentic rule on an 11-wide board — see the
   Castling section above).
4. **Stalemate:** defaults to **draw**; the authentic **stalemate-wins** rule is
   selectable as an option.

Source / further reading: <https://en.wikipedia.org/wiki/Wildebeest_chess>
