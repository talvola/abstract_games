# Dobutsu Shogi (Animal Shogi / どうぶつしょうぎ)

A tiny introductory Shogi for children, designed by professional Shogi player
**Madoka Kitao** (2008). It is played on a **3×4** board with four animals a side,
and it is a fully *solved* game (perfect play is a draw). All the Shogi DNA is
here — **captured pieces switch sides and drop back in** — compressed to a board a
child can learn in a minute.

This page documents the rules **as implemented**.

## Board & seats

- **3 files (columns) × 4 ranks (rows).**
- **Black (Sente)** sits at the bottom (row 0) and advances toward higher rows;
  **White (Gote)** sits at the top (row 3). **Black moves first.**

## The animals

Letters used on the board: **L** Lion, **G** Giraffe, **E** Elephant, **C** Chick,
**H** Hen (a promoted Chick). All animals are single-step movers.

| Piece | Moves |
|-------|-------|
| **Lion (L)** — the royal | One square in **any of the 8 directions** (like a chess King). |
| **Giraffe (G)** | One square **orthogonally** (up / down / left / right) — a Wazir / one-step rook. |
| **Elephant (E)** | One square **diagonally** (the 4 diagonals) — a Ferz / one-step bishop. |
| **Chick (C)** | One square **straight forward** only (a Shogi pawn). |
| **Hen (H)** — promoted Chick | One square in **6 directions**: forward, both forward-diagonals, left, right, and straight back — i.e. "any way except diagonally backward" (a Shogi **gold general**). |

## Setup

From each player's **own** perspective: **Elephant on the left, Lion in the
centre, Giraffe on the right**, with a **Chick directly in front of the Lion**.
The two armies are a 180° rotation of each other.

```
 G  L  E      ← White (Gote), row 3   (G=file0, L=file1, E=file2)
 .  C  .                  row 2
 .  C  .                  row 1
 E  L  G      ← Black (Sente), row 0  (E=file0, L=file1, G=file2)
```

## Promotion

Only the **Chick** promotes. When a Chick **reaches the farthest rank** (the
enemy's home row), it **promotes to a Hen** — this is mandatory (a Chick has no
move from the last rank, so it always promotes on arrival). A Hen that is captured
reverts to a plain Chick in the captor's hand. No other animal promotes.

## Drops (captured animals)

When you capture an enemy animal it **switches to your side** and goes into your
**hand** (the reserve tray). On a later turn you may **drop** a held animal, in
place of a board move, onto **any empty square** — written `L@c,r` and placed via
the reserve tray in the UI. Dobutsu's drops are deliberately **simpler than
Shogi's**:

- **No two-pawns (nifu) rule** — you may have any number of Chicks on a file.
- **A Chick may be dropped on any empty square, including the last rank** — it just
  cannot move from there (and a dropped Chick is **never** promoted; it drops as a
  plain Chick).
- A captured Hen re-enters your hand as a Chick.
- (As in Shogi, you may not leave **your own Lion in check** — so a drop, like any
  move, must be legal.)

## How to win

There are **two** ways to win; whichever happens first on a player's move ends the
game immediately.

1. **Catch** — **capture the enemy Lion.**
2. **Try** — move **your own Lion onto the enemy's home rank** (the farthest row),
   *provided the Lion is not in check there* — i.e. the opponent cannot capture it
   on the reply. Because a player may never move their Lion into check, a Lion that
   successfully steps onto the enemy home row is by definition safe, so reaching
   that rank wins on the spot.

### The Try rule, precisely (highest-risk interpretation)

The "Try" (named after the rugby term) is the part the generic Shogi core does not
provide, so it is worth stating exactly what is implemented:

> Your Lion reaching the enemy's back rank wins **immediately at the end of your
> move, as long as your Lion is not in check on that square** (it cannot be
> captured by the opponent's next move).

Equivalently: a Lion sitting on the opponent's home rank is always a *completed,
safe* Try — the engine never lets a Lion move into check, so it cannot have arrived
there unsafely. If the opponent could have captured the Lion on arrival, the Lion
move was illegal in the first place and the Try does not occur.

This matches the standard published rule ("advance your Lion to the far row,
provided doing so does not put it in check"). Sources differ only in wording
("not in check" vs. "the Lion cannot be captured next turn") — these are
equivalent under the rule that you may never move your own Lion into check, which
is what is implemented.

## Draws & termination

The game is a draw on **fourfold repetition** of a position (the inherited Shogi
core's repetition rule) and there is a hard **ply cap (200)** so a game always
terminates — Dobutsu games are very short in practice.

## Notation

Board moves are `from>to` (e.g. `1,1>1,2`); a Chick reaching the last rank appends
`=+` (promotion to Hen, e.g. `1,2>1,3=+`). Drops are `L@c,r` (e.g. `G@1,1`).
Coordinates are `file,rank` with file 0 = leftmost, rank 0 = Black's home row.

## Source

Primary source: Wikipedia, *Dōbutsu shōgi*
(<https://en.wikipedia.org/wiki/D%C5%8Dbutsu_sh%C5%8Dgi>). The opening has exactly
**4** legal moves; the game has been strongly solved (≈1.57 billion reachable
positions).
