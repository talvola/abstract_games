# Shinjuu Shogi (真獣将棋)

**Shinjuu Shogi** ("true beast shogi") is Dr. Eric Silverman's own 11×11
drop-shogi variant, themed on the **Four Divine Beasts** of East-Asian myth —
the Azure/Blue Dragon, the White Tiger, the Vermillion Sparrow and the
Turtle-Snake (Black Tortoise) — and their attendant creatures. It plays like
modern shogi (captured pieces change sides and can be dropped back; you win by
checkmate) but with a completely new, richly asymmetric army.

*Official source:* Silverman's design notes and move guide —
<https://drericsilverman.com/2021/11/20/11x11-shogi-part-i-shinjuu-shogi/>
(move+promotion guide PDF: `shinjuu-shogi-guide.pdf`). This page describes the
rules **as implemented**.

## Board and goal

- **11×11 board.** Sente (Black, player 0) sits at the bottom and advances up
  the board; Gote (White) is the 180° mirror.
- **29 pieces a side**, of 16 distinct types.
- **Win by checkmate** of the single royal **King**, exactly as in modern shogi
  (a move that leaves your own King in check is illegal; a player with no legal
  move loses).
- **Drops:** captured pieces join the capturer's hand and may be dropped back
  (unpromoted) on any empty square, subject to the pawn rules below.
- Fourfold repetition, or a hard 600-ply cap, is an honest **draw**.

## Starting position

Files are numbered 1–11 from Black's left. Note the **deliberate left/right
asymmetry**: Blue Dragon, Turtle Snake and Old Kite on the left; White Tiger,
Vermillion Sparrow and Fierce Eagle on the right.

| Rank | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** (back) | Blue Dragon | Kirin | Phoenix | F. Leopard | Gold | **King** | Gold | F. Leopard | Phoenix | Kirin | White Tiger |
| **2** | · | Turtle Snake | · | Fragrant Eleph. | · | Great Standard | · | White Eleph. | · | Verm. Sparrow | · |
| **3** | Pawn | Pawn | Pawn | Old Kite | Pawn | Pawn | Pawn | Fierce Eagle | Pawn | Pawn | Pawn |
| **4** | · | · | · | Dog | · | · | · | Dog | · | · | · |

Per side: Blue Dragon ×1, White Tiger ×1, Kirin ×2, Phoenix ×2, Ferocious
Leopard ×2, Gold ×2, King ×1, Turtle Snake ×1, Vermillion Sparrow ×1, Fragrant
Elephant ×1, White Elephant ×1, Great Standard ×1, Old Kite ×1, Fierce Eagle
×1, Dog ×2, Pawn ×9 — 29 total.

## Promotion

- The **promotion zone is the far three ranks** (ranks 9–11 from your side).
- A move that **starts or ends** in the zone may promote the moved piece.
- Promotion is **optional**, **except** a Pawn reaching the last rank (where it
  could never move again) **must** promote.
- **The King and the Great Standard never promote.** Every other type does.
- Captured pieces always return to the board / hand **unpromoted**.

## The pieces

Notation: *step* = one square (a leap, cannot be blocked at range 1); *jump* =
lands on a distant square, leaping over anything between; *slide* = any number
of empty squares in a line (blockable); *slide n* = at most *n* squares
(blockable). "Forward" is toward the enemy.

**Board labels.** The board shows short romaji codes (the platform convention;
the authentic kanji are given with each piece below). Base: `P` Pawn, `G` Gold,
`K` King, `FL` Ferocious Leopard, `Dg` Dog, `OK` Old Kite, `FE` Fierce Eagle,
`TS` Turtle Snake, `VS` Vermillion Sparrow, `Fg` Fragrant Elephant, `WE` White
Elephant, `BD` Blue Dragon, `WT` White Tiger, `Kr` Kirin, `Ph` Phoenix, `GS`
Great Standard. Promoted: `+P` Tokin, `FB` Free Boar, `CE` Copper Elephant, `MG`
Multi General, `BP` Bird of Paradise, `WH` Walking Heron, `Wk` Wizard Stork, `MW`
Mountain Witch, `GE` Great Elephant, `GB` Golden Bird, `DD` Divine Dragon, `DT`
Divine Tiger, `GD` Great Dragon, `WD` Wooden Dove.

### Base pieces

- **Pawn** (歩) — steps one square straight forward. → *Promoted Pawn* (と):
  moves as a Gold.
- **Gold General** (金) — steps one square forward, diagonally forward,
  sideways, or straight back (not diagonally back). → *Free Boar*.
- **King** (王) — steps one square in any of the 8 directions. *(royal; does not
  promote)*
- **Ferocious Leopard** (豹) — steps one square forward, straight back, or any
  of the four diagonals (not sideways). → *Copper Elephant*.
- **Dog** (犬) — steps one square straight forward, or diagonally **back**. →
  *Multi General*.
- **Old Kite** (古) — slides up to **2** squares straight (forward, back, left or
  right); also steps one square diagonally forward. → *Bird of Paradise*.
- **Fierce Eagle** (猛鷲) — steps one square forward or diagonally forward;
  slides up to **2** sideways; slides up to **2** diagonally **back**. →
  *Walking Heron*.
- **Turtle Snake** (玄) — slides any distance straight forward and diagonally
  forward; steps one square straight back; slides up to **2** diagonally back. →
  *Wizard Stork*.
- **Vermillion Sparrow** (朱) — slides any distance diagonally forward and
  straight back; steps one square straight forward; slides up to **2**
  diagonally back. → *Mountain Witch*.
- **Fragrant Elephant** (香象) — slides any distance diagonally **forward**;
  slides up to **2** in every other direction (straight forward/back, sideways,
  diagonally back). → *Great Elephant*.
- **White Elephant** (白象) — slides any distance diagonally **back**; slides up
  to **2** in every other direction. → *Golden Bird*.
- **Blue Dragon** (青) — slides any distance straight forward, straight back, and
  diagonally forward-**right**; slides up to **2** sideways. → *Divine Dragon*.
- **White Tiger** (白虎) — slides any distance sideways (left and right) and
  diagonally forward-**left**; slides up to **2** straight forward/back. →
  *Divine Tiger*.
- **Kirin** (麒) — steps one square diagonally (all four), **and jumps** exactly
  2 squares straight (forward, back, left or right). → *Great Dragon*.
- **Phoenix** (鳳) — steps one square straight (all four), **and jumps** exactly
  2 squares diagonally (all four). → *Wooden Dove*.
- **Great Standard** (大旗) — slides any distance straight (all four) and
  diagonally **forward**; slides up to **2** diagonally back. *(does not
  promote)*

### Promoted forms

- **Free Boar** (奔猪, ← Gold) — slides any distance forward, diagonally forward,
  and sideways; steps one square straight back.
- **Copper Elephant** (銅象, ← F. Leopard) — slides any distance straight
  forward/back; steps one square sideways or on any diagonal.
- **Multi General** (雑, ← Dog) — slides any distance straight forward and
  diagonally back.
- **Bird of Paradise** (時鳥, ← Old Kite) — slides any distance straight forward,
  diagonally forward (both), and straight back.
- **Walking Heron** (歩鷺, ← Fierce Eagle) — slides any distance straight
  forward/back; slides up to **2** sideways and diagonally forward.
- **Wizard Stork** (仙, ← Turtle Snake) — slides any distance forward, diagonally
  forward and diagonally back; steps one square straight back.
- **Mountain Witch** (母, ← Verm. Sparrow) — slides any distance diagonally
  forward, straight back and diagonally back; steps one square straight forward.
- **Great Elephant** (大象, ← Fragrant Eleph.) — slides any distance straight
  (all four), sideways and diagonally back; slides up to **2** diagonally
  forward.
- **Golden Bird** (金翅, ← White Eleph.) — slides any distance straight
  forward/back; slides up to **2** sideways and diagonally back; **on a forward
  diagonal it slides freely and may leap over up to 3 pieces.**
- **Divine Dragon** (神龍, ← Blue Dragon) — slides any distance straight
  forward/back, sideways-right, and diagonally forward-right; slides up to **2**
  sideways-left.
- **Divine Tiger** (神虎, ← White Tiger) — slides any distance sideways, straight
  forward and diagonally forward-left; slides up to **2** straight back.
- **Great Dragon** (大龍, ← Kirin) — **sideways: either slide any distance, or
  jump 2 or 3 squares** (over intervening pieces); slides up to **2** straight
  forward/back; slides up to **3** diagonally back.
- **Wooden Dove** (鳩槃, ← Phoenix) — steps one square straight (all four); **on
  each diagonal, jumps to the 3rd square (over whatever lies between), then may
  optionally slide 1 or 2 more squares.**

## Special-move summary (from the guide)

- **Kirin** jumps 2 squares orthogonally; **Phoenix** jumps 2 squares
  diagonally.
- **Golden Bird** may leap over up to 3 pieces when sliding forward-diagonally.
- **Wooden Dove** jumps 3 squares diagonally, then optionally slides 1–2 more.
- **Great Dragon** may jump 2 or 3 squares left/right, **or** slide unlimited
  left/right — not both in one move.

## Drops

Standard modern-shogi drops. A captured piece enters your hand unpromoted and
may later be dropped (unpromoted) onto any empty square, with these
restrictions — which apply **only to the Pawn** here (there is no Lance or
Knight in this set):

- **No two unpromoted Pawns on the same file (nifu).**
- **No Pawn drop on the last rank** (it could never move).
- **No pawn-drop checkmate (uchifuzume).**

Any other piece may be dropped on any empty square, including the last rank.

## Interpretations

The move geometry above was read square-by-square from Silverman's move guide
PDF. A few points required interpretation and are flagged here for future
review (they are implemented as described):

1. **Bounded ("slide 2/3") slides are blockable, not jumps.** Where a piece
   reaches exactly 2 (or 3) squares in a direction, and the guide draws no jump
   marker, it is implemented as a normal slide of limited length (an
   intervening piece blocks it). Only pieces the guide explicitly marks as
   jumpers (Kirin, Phoenix, Golden Bird, Wooden Dove, Great Dragon) can leap.

2. **Golden Bird's "leap over up to 3 pieces":** implemented as a
   forward-diagonal slide that may pass over up to three pieces of **either
   colour**, landing on any empty square or capturing an enemy so long as no
   more than three pieces were leapt to reach it.

3. **Wooden Dove:** jumps to the **3rd** diagonal square (squares 1 and 2 are
   leapt over regardless of contents; it cannot be blocked there). If that
   square holds an enemy it is captured and the move ends; if it is empty the
   Dove may optionally continue sliding 1 or 2 more squares (blockable). It has
   **no** 1- or 2-square diagonal move.

4. **Great Dragon's sideways move:** the reachable squares are the union of a
   normal (blockable) slide and jumps to the squares exactly 2 and 3 away
   (which ignore intervening pieces). The guide's "not both" note only means a
   single move is one or the other; since every destination is a single move,
   the union is exact.

5. **Army symmetry:** Gote's army is the 180° rotation of Sente's (standard
   shogi point-symmetry), preserving the designed left/right asymmetry.
