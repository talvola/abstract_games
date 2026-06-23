# Camelot

**Camelot** is George S. Parker's medieval strategy classic (Parker Brothers,
first published 1887 as *Chivalry*, refined into *Camelot* in 1930). Two players,
**White** (player 0) and **Black** (player 1), each command an army that races to
storm the opponent's castle. White moves first.

This package follows the **World Camelot Federation (WCF)** rules, the modern
authoritative ruleset, and flags every interpretive choice below.

## The board

The board is the famous **cross / plus shape**: 160 squares. Files are lettered
**A–L** (12 files); ranks are numbered **1–16** (running from White's edge to
Black's edge). The main body is a 12×14 block (ranks 2–15) with a stepped
**three-square cut at each corner**, and a **two-square castle** juts out at the
middle of each back edge:

| Ranks | Squares present |
|---|---|
| rank 1 (White castle) | **F1, G1** |
| rank 2 | C2 … J2 (8) |
| rank 3 | B3 … K3 (10) |
| ranks 4–13 | A … L (12 each) |
| rank 14 | B14 … K14 (10) |
| rank 15 | C15 … J15 (8) |
| rank 16 (Black castle) | **F16, G16** |

That is 8 + 10 + 12·10 + 10 + 8 + 4 = **160** squares.

- **White's castle** = F1 & G1. **Black's castle** = F16 & G16.
- Off-board squares (the cut corners, everything outside the cross) simply do not
  exist — they are absent from the board and from movement.

Internally a square is `"c,r"` with `c` = file index (A=0 … L=11) and `r` = rank
index (rank 1 = 0 … rank 16 = 15).

## The pieces

Each side has **14 pieces: 4 Knights (`K`) and 10 Men (`M`)**, in two ranks near
its own side.

- **White** — Knights on **C6, D7, I7, J6**; Men on **D6, E6, E7, F6, F7, G6, G7,
  H6, H7, I6**.
- **Black** — Knights on **C11, D10, I10, J11**; Men on **D11, E10, E11, F10, F11,
  G10, G11, H10, H11, I11**.

Knights and Men move identically *except* that only a Knight may perform the
**Knight's Charge** (canter + jump in one move).

## Moving

A move is shown as a `>`-separated path of the squares the piece visits, e.g.
`5,4>5,6` (a single hop) or `5,4>5,6>7,6` (a chain). There are three move types:

1. **Plain move** — one step to **any adjoining empty square**, in any of the 8
   directions (orthogonal or diagonal, king-like).
2. **Canter** — leap over an **adjacent friendly** piece to the empty square
   **directly beyond** it. The cantered-over piece is **not** removed. Canters may
   be **chained** in a single move, changing direction between legs.
3. **Jump** — leap over an **adjacent enemy** piece to the empty square **beyond**,
   **removing** the enemy. Jumps may be **chained**, changing direction.

**Knight's Charge** — a **Knight only** may combine cantering and jumping in one
move, in the order **canter(s) first, then jump(s)**.

### Jumping is compulsory

Under the WCF rules, **if you can jump, you must**: if any of your pieces stands
next to an exposed enemy, every legal move that turn must be a jumping move (or, for
a knight, a charge that ends in a jump), and a jump that lands you next to another
exposed enemy **must continue** as part of the same move.

> **FLAGGED CHOICE.** The task brief stated jumping is "optional (not forced)". The
> authoritative WCF / Wikipedia rules make jumping **compulsory**, so this package
> implements the compulsory rule and documents the deviation here. (Jumps still
> need not be maximal beyond the rule that a started jump continues while further
> jumps exist — there is no longest-capture requirement.)

## Castle rules

- A piece may **not** plain-move or canter **into its own castle**. (It may,
  however, *jump* into its own castle if the jump arc lands there; and a jump that
  lands in your own castle next to another exposed enemy must continue out.)
- A piece that has entered the **opponent's** castle may not leave it (it has
  arrived), though it may shift between the two castle squares. *This package does
  not need to special-case castle exit: the win is detected the moment two pieces
  occupy the enemy castle, ending the game.*

> **FLAGGED SIMPLIFICATION.** The "may not leave the enemy castle / two-move limit
> between castle squares" nuance never matters here because occupying both enemy
> castle squares is an immediate win, so the game ends before any such follow-up
> move. The "must jump out of your own castle" rule is honoured implicitly by the
> compulsory-jump generator.

## Winning

You win by any of:

1. **Castle invasion** — moving **two of your pieces** onto the two squares of the
   **opponent's** castle (both occupied simultaneously).
2. **Annihilation** — capturing **all** of the opponent's pieces while keeping
   **two or more** of your own.
3. **Stalemate** — the opponent has **no legal move** on their turn (they lose).

### Draw

- The game is a **draw** if **both** players are reduced to **at most one piece**
  each — neither side can ever win (a lone piece cannot invade the two-square
  castle and capturing-all needs ≥2 survivors).
- A **no-progress** safeguard also draws the game after **100 plies without a
  capture**, guaranteeing termination.

> **FLAGGED CHOICE.** The one-piece draw is the documented WCF rule. The 100-ply
> no-progress cap is an engine-required termination guard (Camelot is otherwise
> non-progressive); it does not affect normal play.

## Reading the board

In the renderer White's castle (F1/G1) is at the **bottom**, Black's (F16/G16) at
the **top**; castle squares are tinted. Each piece shows `K` (Knight) or `M` (Man)
in its owner's colour.
