# Sho Shogi (小将棋, "small / old shogi")

Sho Shogi is the 16th-century form of shogi and the **immediate predecessor of
the modern game**. It is played on the same 9×9 board with the same setup, but
with two differences: an extra **Drunk Elephant** sits in front of each king,
and there are **no drops** — captured pieces leave play for good. (Historically,
the Emperor Go-Nara removed the Drunk Elephant around the same time the drop rule
was introduced, giving rise to shogi as it is played today.)

These are the rules **as implemented** here. Sente (Black, player 1) sits at the
bottom and moves first; Gote (White, player 2) is at the top.

## Pieces and how they move

Each side has 21 pieces: a King (K), a **Drunk Elephant (DE)**, a Rook (R), a
Bishop (B), two Golds (G), two Silvers (S), two Knights (N), two Lances (L), and
nine Pawns (P). "Forward" is toward the opponent. Every piece except the Drunk
Elephant moves exactly as in modern Shogi:

- **King** — one square in any direction.
- **Rook** — any distance orthogonally. **Bishop** — any distance diagonally.
- **Gold** — one square orthogonally or one square forward-diagonally (six
  squares; not the two back-diagonals).
- **Silver** — one square diagonally or one square straight forward (five).
- **Knight** — jumps to the two squares two-forward-and-one-to-the-side (only
  forward; it jumps over pieces).
- **Lance** — any distance straight forward.
- **Pawn** — one square straight forward (captures the same way it moves).
- **Drunk Elephant (DE, 酔象)** — one square in any direction **except straight
  backward** (the seven king-steps minus the backward one).

## Setup

The back rank is `L N S G K G S N L` (King centred). On the second rank, the
**Bishop** stands on the same file as the knight on the player's left, the
**Rook** on the same file as the knight on the player's right, and the **Drunk
Elephant** on the king's file, directly in front of the king. The nine Pawns
fill the third rank.

```
9  8  7  6  5  4  3  2  1
L  N  S  G  K  G  S  N  L   ← White's back rank (row 9)
.  R  .  .  DE .  .  B  .
P  P  P  P  P  P  P  P  P
.  .  .  .  .  .  .  .  .
.  .  .  .  .  .  .  .  .
.  .  .  .  .  .  .  .  .
P  P  P  P  P  P  P  P  P
.  B  .  .  DE .  .  R  .
L  N  S  G  K  G  S  N  L   ← Black's back rank (row 1)
```

## Promotion

The **promotion zone** is the farthest three ranks from your side. A piece that
**moves into, out of, or within** the zone *may* promote at the end of that move.
Promotion is optional **except** where the piece could otherwise never move
again, where it is mandatory: a Pawn or Lance reaching the last rank, or a Knight
reaching the last two ranks.

Promoted pieces:

- **Promoted Pawn/Lance/Knight/Silver** (+P, +L, +N, +S) all move like a **Gold**.
- **Promoted Rook** (+R, *Dragon King*) — Rook plus one diagonal king-step.
- **Promoted Bishop** (+B, *Dragon Horse*) — Bishop plus one orthogonal king-step.
- **Promoted Drunk Elephant** (+DE) becomes a **Crown Prince (CP, 太子)** — it
  moves like a **King** and, crucially, **becomes a second royal piece** (see
  below). Promoting the elephant is always optional.

King and Gold never promote.

## No drops

There is **no hand and no drop rule** — captured pieces are removed from play
permanently. (The drop, the two-pawns rule and drop-mate are all later Shogi
innovations that do not exist here.)

## Winning: dual royalty, check and mate

A player has one or two **royal** pieces: the King, plus a **Crown Prince** if
the Drunk Elephant has promoted. The objective is to **capture all of your
opponent's royals**.

- **Check** is defined on the royals collectively: you are "in check" only when
  **every** one of your royal pieces is attacked. So while both a King and a
  Crown Prince are on the board, an attack on just one of them is *not* check —
  you may legally leave that royal to be captured. You must capture **both** to
  win this way.
- A move that would leave you in check (all royals attacked) is **illegal**.
- If the side to move has **no legal move** — the sole remaining royal is
  checkmated, or the player is stalemated — that player **loses** (as in shogi).

### The bare-king rule

The game can **also** be won by **baring** the opponent — capturing all of their
non-royal pieces so that only their King (and/or Crown Prince) remains. As an
exception, a player who has just been bared may **secure a draw** if, on their
immediately following move, they can bare the opponent in return (a *mutual
bare*). This is a documented feature of the historical/reconstructed ruleset
(Steve Evans' reconstruction on chessvariants.com); in practice the game is
almost always decided by checkmate first.

## Draws

- **Repetition (sennichite):** if the same position (board + side to move)
  occurs a fourth time, the game is a **draw**.
- A **mutual bare** (see above) is an honest draw.
- A hard ply cap also forces a draw in the rare event a game runs very long,
  guaranteeing the game terminates.

### Documented simplifications / interpretations

- The **perpetual-check** prohibition (Wikipedia notes a player may not give
  perpetual check) is **not** implemented; a fourfold repetition is always
  scored a draw here.
- The "illegal move loses immediately" convention is moot — the app only ever
  offers legal moves.
- The exact historical rules of Sho Shogi are not fully known; the game follows
  the reconstruction of both sources below (based on the contemporary larger
  Chu and Dai Shogi), and where the two agree it is followed exactly.

## Notation

A board move is a path like `7,2>7,3`; append `=+` to promote (the app shows a
**Promote / Don't promote** picker when both are legal). There are no drops.

## Sources

- Wikipedia, *Sho shogi* — https://en.wikipedia.org/wiki/Sho_shogi
- chessvariants.com, *Sho Shogi* (Steve Evans' reconstruction) —
  https://www.chessvariants.com/shogivariants.dir/shoshogi.html
