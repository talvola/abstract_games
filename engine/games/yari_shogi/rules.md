# Yari Shogi (Spear Shogi)

Yari Shogi (槍将棋, "Spear Shogi") is a modern Shogi variant invented by **Christian
Freeling (1981)**. *Yari* means "spear", another name for the Shogi lance — and the
game's signature is that almost every piece is a forward-ranging spear: it slides
**any number of free squares straight forward** (like a lance), each with a small
extra one-step component, and each promotes to a form that *also* ranges straight
**backward**. Played on a **7×9** board (7 files × 9 ranks). Like Shogi, captured
pieces switch sides and can be **dropped** back into play. These are the rules **as
implemented** here. **Black (Sente, player 1)** sits at the bottom and moves first;
**White (Gote, player 2)** is at the top. "Forward" means toward the opponent.

## The pieces and how they move

The piece letters used in the move log (and the on-board labels in brackets):

| Letter | Piece | Label | Promotes to |
|---|---|---|---|
| G | **General** (royal) | G | — |
| P | **Pawn** (spear) | P | Yari Silver |
| N | **Yari Knight** | yN | Yari Gold |
| B | **Yari Bishop** | yB | Yari Gold |
| R | **Yari Rook** | yR | Rook |
| +P | **Yari Silver** (promoted Pawn) | yS | — |
| +N / +B | **Yari Gold** (promoted Knight / Bishop) | yG | — |
| +R | **Rook** (promoted Yari Rook) | +R | — |

- **General** — one square in any of the 8 directions (like a King). It is the
  **royal** piece: lose it (checkmate) and you lose. Does not promote.
- **Pawn** — one square straight **forward** only (captures the same way).
- **Yari Knight** — **ranges** (any distance) straight **forward**; *or* **jumps**
  "one square forward plus one square diagonally forward" (a narrow knight leap to
  the second rank ahead, either side — over any intervening piece).
- **Yari Bishop** — **ranges** straight **forward**; *or* steps one square
  **diagonally forward** (either side).
- **Yari Rook** — **ranges** straight **forward** *or* **sideways** (left/right). It
  cannot move backward until promoted.
- **Yari Silver** (promoted Pawn) — **ranges** straight **backward**; *or* steps one
  square **forward** (orthogonally or diagonally — the three forward steps).
- **Yari Gold** (promoted Knight or Bishop) — **ranges** straight **backward**; *or*
  steps one square **forward, sideways, or diagonally forward** (the five forward /
  lateral steps). (It does *not* step diagonally backward — its only backward power
  is the straight-back range.)
- **Rook** (promoted Yari Rook) — moves like an ordinary rook: any number of free
  squares along **any of the four orthogonal directions**.

(All directions are relative to the moving side; White's army is a 180° rotation of
Black's. The spear pieces are left/right symmetric.)

## Starting position

Each side has, on its **back rank** (from that player's left): **Yari Rook, Yari
Bishop, Yari Bishop, General, Yari Knight, Yari Knight, Yari Rook**. In front, the
next-but-one rank (the third rank) is a full row of **seven Pawns**. That makes
**14 pieces** per side (7 back-rank + 7 pawns). The General stands on the **centre
file**.

## Promotion

The **promotion zone** is the **three farthest ranks** from your side (the
opponent's pawn rank and beyond). A move that **starts in, ends in, or passes into**
the zone *may* promote at its end:

- **Pawn → Yari Silver**, **Yari Knight → Yari Gold**, **Yari Bishop → Yari Gold**,
  **Yari Rook → Rook**. The General never promotes.
- Promotion is optional, **except** when the unpromoted piece could never move again:
  a **Pawn** or **Yari Bishop** reaching the **last rank**, or a **Yari Knight**
  reaching either of the **last two ranks**, **must** promote.

A promoted piece that is captured **reverts** to its unpromoted type in the captor's
hand. A dropped piece always arrives **unpromoted** and must move again to re-promote.

## Drops

When you capture a piece it **flips to your colour and goes to your hand**. On your
turn, instead of moving, you may **drop** a piece from your hand onto any empty
square (Generals are never captured/dropped). Restrictions:

- **Nifu:** you may not drop a Pawn onto a file that already holds one of your own
  **unpromoted** Pawns.
- A **Pawn** or **Yari Bishop** may not be dropped on the **last rank**, and a
  **Yari Knight** may not be dropped on either of the **last two ranks** (in each
  case it would have no move).
- A **Pawn** may not be dropped to give **immediate checkmate** (the *uchifuzume*
  rule; a Pawn drop that gives only **check** is fine).
- A drop may not leave your own **General** in check.

## Winning, check, and draws

You may not make any move that leaves your own General in check. **Checkmate wins** —
the side to move with no legal reply (including no legal drop) loses.

If the same position (board, both hands, side to move) recurs a fourth time the game
is a **draw** (sennichite). A hard ply cap also forces a draw if a game runs very
long, guaranteeing termination. The perpetual-check exception is **not** implemented
(a four-fold repetition is always a draw here).

## Notation

A board move is a path like `3,2>3,5`; append `=+` to promote (the app shows a
**Promote / Don't promote** picker when both are legal). A drop is written `B@3,4`
("drop a Yari Bishop"); in the app, click a piece in your reserve tray, then an empty
square.

## Sources & interpretation

Rules verified against the Wikipedia "Yari shogi" article and corroborating
descriptions (chessvariants.com, gambiter). Interpretation notes:

- The **Yari Knight's** "one forward + one diagonally forward" jump is implemented as
  a leap to the square two ranks ahead and one file to the side (either side),
  jumping over any intervening piece — matching the betza notation **ffN** plus the
  straight-forward range **fR**.
- The **Yari Gold** (promoted Knight/Bishop) ranges straight backward and steps to
  the five forward/lateral squares; it has **no diagonal-backward step** (its
  backward power is purely the straight-back range), per the source's description of
  the Gold "covering the whole backward file it occupies".
- **Mandatory-promotion** squares follow directly from "promote when the piece would
  otherwise be immobile": Pawn/Yari Bishop on the last rank, Yari Knight on the last
  two ranks.
