# Goro Goro Shogi (5×6)

Goro Goro Shogi is Shogi compressed onto a **5×6** board with a small, slow army
— no long-range pieces at all. *Goro goro* is a contraction of *go roku*
("five-six"), naming the board; the game is also sold as **Goro Goro Dōbutsu
Shogi** (the lion, dogs, cats and chicks of the animal-shogi family). All the
standard Shogi rules apply, including **drops**, so see the Shogi rules for full
detail; this page lists only what differs.

## Pieces

Each side has **eight** pieces:

- **King (K)** ×1, **Gold general (G)** ×2, **Silver general (S)** ×2, and
  **Pawn (P)** ×3.

There is **no rook, bishop, knight or lance**. Every piece moves exactly as in
Shogi:

- **Gold**, **Silver**, **King** and **Pawn** move as in Shogi (the Pawn is a
  single forward step).

## Setup

```
S G k G S     ← White (Gote), top    (row 5)
. P P P .                            (row 4)
. . . . .                            (row 3)
. . . . .                            (row 2)
. P P P .                            (row 1)
S G K G S     ← Black (Sente), bottom (row 0)
```

Each side's back rank runs **Silver–Gold–King–Gold–Silver** with the **King
centred** and the two Silvers on the outside corners. The **three Pawns** sit on
the central three files of the rank directly in front of the back rank. The back
rank is symmetric (its own 180° rotation), so both armies share the same order.
**Black (Sente) moves first.**

## Promotion

The **promotion zone is the far two ranks** (rows 5–6 from your side — the
opponent's back two ranks). A piece that moves into, out of, or within the zone
may promote. A Pawn reaching the **last rank** *must* promote. Promotions:
**Silver → +S** and **Pawn → +P**, each then moving like a **Gold**. **Gold and
King never promote** (and being Golds already, there is nothing else on the board
that can).

## Drops, captures, winning, draws

Identical to Shogi: a captured piece switches colour and goes to your hand, to be
dropped (unpromoted) on a later turn, subject to the two-pawns (*nifu*),
last-rank and drop-mate (*uchifuzume*) rules. **Checkmate wins.** A four-fold
repetition is a **draw**, and a ply cap guarantees termination.

## Variant: Goro Goro Plus

Select **`variant` = `plus`** for **Goro Goro Plus**. The board (5×6), army on the
board, and setup are unchanged, but **each side additionally starts with a Lance
and a Knight in hand**, droppable from the very first move. This is the version
playable on PyChess/lishogi (Fairy-Stockfish `gorogoroplus`).

- The two reserve pieces move exactly as in Shogi: the **Lance** slides straight
  forward, the **Knight** jumps to the two forward-knight squares.
- They obey the usual drop restrictions: a Lance may not be dropped on the last
  rank, a Knight not on the last two ranks (nowhere it could ever move).
- When they reach the promotion zone they promote to a **Gold** (`+L` / `+N`).

`classic` (the default) is the original game, unchanged.

## Notation

As in Shogi: board moves are `from>to` (append `=+` to promote), drops are
`L@c,r`.
