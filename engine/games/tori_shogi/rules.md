# Tori Shogi (Bird Shogi)

Tori Shogi (鳥将棋, "Bird Shogi") is a 19th-century Japanese Shogi variant
(traditionally attributed to 1828) played on a **7×7** board where every piece is
a bird. Like Shogi, captured pieces switch sides and can be **dropped** back into
play as your own. These are the rules **as implemented** here. **Black (Sente,
player 1)** sits at the bottom and moves first; **White (Gote, player 2)** is at
the top. "Forward" means toward the opponent.

## The birds and how they move

The piece letters used in the move log (and the on-board labels in brackets):

| Letter | Bird | Label | Promotes to |
|---|---|---|---|
| P | **Phoenix** (鳳凰, hō-ō) — the royal piece | Ph | — |
| S | **Swallow** (燕, tsubame) — the "pawn" | Sw | Goose |
| F | **Falcon** (鷹, taka) | Fa | Eagle |
| C | **Crane** (鶴, tsuru) | Cr | — |
| H | **Pheasant** (雉, kiji) | Pt | — |
| L | **Left Quail** (左鶉, sa-uzura) | LQ | — |
| R | **Right Quail** (右鶉, u-uzura) | RQ | — |
| +S | **Goose** (鵝, gan) — promoted Swallow | Go | — |
| +F | **Eagle** (鵰, washi) — promoted Falcon | Ea | — |

- **Phoenix** — one square in any of the 8 directions (like a King). It is the
  **royal** piece: lose it (checkmate) and you lose. Does not promote.
- **Swallow** — one square straight **forward** only (and captures the same way).
- **Falcon** — one square in any direction **except straight backward** (7 squares).
- **Crane** — one square to any of the **four diagonals** or straight **forward /
  backward** (6 squares; never sideways).
- **Pheasant** — **jumps to the second square straight forward** (leaping over any
  piece in between), or steps one square **diagonally backward** (either side).
- **Left Quail** — **ranges** (any distance) straight forward *or* diagonally
  backward-**right**; and steps one square diagonally backward-**left**.
- **Right Quail** — the mirror image: **ranges** straight forward *or* diagonally
  backward-**left**; and steps one square diagonally backward-**right**.
- **Goose** (promoted Swallow) — jumps to the **second** square diagonally
  **forward** (either side) or the **second** square straight **backward**.
- **Eagle** (promoted Falcon) — **ranges** diagonally forward or straight backward;
  steps **one or two** squares diagonally backward; and steps one square straight
  forward or sideways.

(All directions are relative to the moving side; White's army is a 180° rotation
of Black's, so each Left Quail faces a Left Quail across the board.)

## Starting position

Each side has, on its **back rank** (from that player's left): **Left Quail,
Pheasant, Crane, Phoenix, Crane, Pheasant, Right Quail**. A **Falcon** sits one
square in front of the Phoenix (the centre file). The next rank is a full row of
**seven Swallows**, and there is **one extra advanced Swallow** offset one file
from centre (Black's on file c, White's on file e — they are mirror images).
That makes **8 Swallows and 13 pieces** per side.

## Promotion

The **promotion zone** is the **two farthest ranks** from your side (the opponent's
Falcon rank and the back rank). Only the **Swallow** and the **Falcon** promote;
all other birds never promote. A move that **starts in, ends in, or passes into**
the zone *may* promote at its end:

- **Swallow → Goose**, **Falcon → Eagle**.
- Promotion is optional, **except** a Swallow reaching the **last rank** (where it
  could never move again) **must** promote.

A promoted bird that is captured **reverts** to its unpromoted type in the captor's
hand. A dropped bird always arrives **unpromoted**.

## Drops

When you capture a bird it **flips to your colour and goes to your hand**. On your
turn, instead of moving, you may **drop** a bird from your hand onto any empty
square (Phoenixes are never captured/dropped). Restrictions:

- **Swallow nifu (Tori variant):** you may not drop a Swallow onto a file that
  already holds **two** of your **unpromoted** Swallows. *Unlike standard Shogi,
  Tori permits **two** Swallows in a file — only a **third** is forbidden.*
- A **Swallow** may not be dropped on the **last rank** (it would have no move).
- A **Swallow** may not be dropped to give **immediate checkmate** (the
  *uchifuzume* analogue; giving plain **check** by a Swallow drop is fine).
- A drop may not leave your own **Phoenix** in check.

## Winning, check, and draws

You may not make any move that leaves your own Phoenix in check. **Checkmate
wins** — the side to move with no legal reply (including no legal drop) loses.

If the same position (board, both hands, side to move) recurs a fourth time the
game is a **draw** (sennichite). A hard ply cap also forces a draw in the rare
event a game runs very long, guaranteeing termination. The perpetual-check
exception to sennichite is **not** implemented (a four-fold repetition is always a
draw here).

## Notation

A board move is a path like `3,1>4,1`; append `=+` to promote (the app shows a
**Promote / Don't promote** picker when both are legal). A drop is written `F@3,3`
("drop a Falcon"); in the app, click a bird in your reserve tray, then an empty
square.

## Sources & interpretation

Rules verified against the Wikipedia "Tori shogi" article and corroborating
descriptions (pychess, gambiter). Two points worth flagging:

- **The advanced Swallow** is placed off-centre (Black file c / White file e) so
  the position is a true 180° rotation; sources agree each side starts with exactly
  8 Swallows (7 on the swallow rank + 1 advanced).
- **The Swallow drop-mate ban** is implemented by direct analogy to Shogi's
  *uchifuzume*; sources state Swallows may not be dropped to give immediate
  checkmate, which this matches.
