# Wa Shogi (和将棋)

**Wa Shogi** is a large traditional Shogi (Japanese chess) variant in which every
piece is named for an animal or bird. Two players — **Black** (Sente, moves first,
bottom of the board) and **White** (Gote, top) — play on an **11×11** board with
**27 pieces per side**. The goal, as in Shogi, is to **checkmate the enemy Crane
King** (or leave the opponent with no legal move).

This package implements the **classic drop-less ruleset** — see *Drops* below.

## Movement

Every move geometry is stated from the mover's point of view; **forward** means
toward the enemy. "Step" = one square (may not jump unless noted). "Ranges" =
slides any distance until blocked. Diagonal moves that are blocked stop like any
slider. Board coordinates are `col,row` with `0,0` at Black's near-left corner.

### Unpromoted pieces

| Piece | Label | Move |
|-------|-------|------|
| **Crane King** *(royal)* | CK | Steps one square in any of the 8 directions. |
| **Cloud Eagle** | CE | Ranges straight forward/backward; slides **1–3** squares diagonally forward; steps one square sideways or diagonally backward. |
| **Flying Falcon** | FF | Ranges on all four diagonals; steps one square forward. |
| **Swallow's Wings** | SW | Ranges sideways; steps one square forward or backward. |
| **Treacherous Fox** | TF | Steps one square in the four diagonals or straight forward/backward — and may **jump to the second square** in any of those six directions. |
| **Running Rabbit** | RR | Ranges straight forward; steps one square in the four diagonals or straight backward. |
| **Violent Wolf** | VW | Steps one square in the four orthogonals or diagonally forward (6). |
| **Violent Stag** | VS | Steps one square in the four diagonals or straight forward (5). |
| **Flying Goose** | FG | Steps one square forward, backward, or diagonally forward (4). |
| **Flying Cock** | FC | Steps one square sideways or diagonally forward (4). |
| **Strutting Crow** | SC | Steps one square forward or diagonally backward (3). |
| **Swooping Owl** | SO | Steps one square forward or diagonally backward (3). |
| **Blind Dog** | BD | Steps one square sideways, straight backward, or diagonally forward (5). |
| **Climbing Monkey** | CM | Steps one square forward, backward, or diagonally forward (4). |
| **Liberated Horse** | LH | Ranges straight forward; steps **1–2** squares straight backward. |
| **Oxcart** | OX | Ranges straight forward only. |
| **Sparrow Pawn** | SP | Steps one square straight forward. |

Note that several pieces move identically but promote differently: the
**Strutting Crow** and **Swooping Owl**, and the **Flying Goose** and
**Climbing Monkey**.

### Promotion

The **promotion zone** is the **three farthest ranks** (the opponent's rows 8–10
for Black; rows 0–2 for White). A piece may promote when a move **begins in,
ends in, or moves within** the zone. Promotion is optional, **except** a Sparrow
Pawn or Oxcart reaching the farthest rank must promote (it would otherwise have no
move). The **Crane King, Cloud Eagle and Treacherous Fox do not promote.**

| Piece | Promotes to | Promoted move |
|-------|-------------|---------------|
| Sparrow Pawn | **Golden Bird** (GB) | Gold general: 4 orthogonals + diagonally forward. |
| Swallow's Wings | **Gliding Swallow** (GS) | Ranges in all 4 orthogonal directions (a rook). |
| Flying Falcon | **Tenacious Falcon** (TcF) | Ranges 4 diagonals + straight forward/backward; steps sideways. |
| Oxcart | **Plodding Ox** (PO) | Steps one square in any of the 8 directions. |
| Liberated Horse | **Heavenly Horse** (HH) | Knight jumps forward and backward (±1,±2). |
| Violent Wolf | **Bear's Eyes** (BE) | Steps one square in any of the 8 directions. |
| Violent Stag | **Roaming Boar** (RB) | Steps one square in any direction except straight backward. |
| Flying Cock | **Raiding Falcon** (RF) | Ranges straight forward/backward; steps sideways or diagonally forward. |
| Flying Goose | **Swallow's Wings** (SW) | As the Swallow's Wings above. |
| Blind Dog | **Violent Wolf** (VW) | As the Violent Wolf above. |
| Climbing Monkey | **Violent Stag** (VS) | As the Violent Stag above. |
| Strutting Crow | **Flying Falcon** (FF) | As the Flying Falcon above. |
| Swooping Owl | **Cloud Eagle** (CE) | As the Cloud Eagle above. |
| Running Rabbit | **Treacherous Fox** (TF) | As the Treacherous Fox above (steps + jump-to-second-square). |

## Setup

Black's pieces (White mirrors by a 180° rotation):

- **Rank 1** (row 0), left to right: Oxcart, Blind Dog, Strutting Crow, Flying
  Goose, Violent Wolf, **Crane King**, Violent Stag, Flying Cock, Swooping Owl,
  Climbing Monkey, Liberated Horse.
- **Rank 2** (row 1): Flying Falcon (file 1), Swallow's Wings (file 5), Cloud
  Eagle (file 9).
- **Rank 3** (row 2): Treacherous Fox (file 3), Running Rabbit (file 7), and a
  Sparrow Pawn on every other file (files 0,1,2,4,5,6,8,9,10).
- **Rank 4** (row 3): a Sparrow Pawn on files 3 and 7 (in front of the Fox and
  the Rabbit) — 11 Sparrow Pawns in all.

## Drops

Historical descriptions of Wa shogi make **no mention of drops**, so this
implementation uses the **drop-less** ruleset: **captured pieces are removed from
play** and there is no reserve. (A modern *with-drops* variant is also played, in
which captures switch sides and re-enter from hand as in ordinary Shogi; that
alternative is not implemented here.)

## Ending the game

A player who is checkmated — or who has no legal move — **loses**. To guarantee
termination the engine also declares a **draw** at a hard ply cap (400 plies) or
on fourfold repetition.

## Moves (notation)

A move is the path string `fromCol,fromRow>toCol,toRow`, with `=+` appended to
promote (e.g. `4,7>4,8=+`). There are no drop moves.

*Rules as implemented; primary source: the English Wikipedia "Wa shogi" article.*
