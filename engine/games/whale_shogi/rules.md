# Whale Shogi (Kujira Shogi, 6×6)

Whale Shogi (鯨将棋 *Kujira Shōgi*) is a Shogi variant invented by R. Wayne
Schmittberger in 1981, played on a **6×6** board with a **whaling-themed** army.
It is broadly similar to Judkins Shogi, but every piece — and the promotion rule
— is different. **Capture the opponent's White Whale to win.**

## The army (12 pieces a side)

Each player has a **White Whale**, a **Porpoise**, a **Humpback**, a **Grey
Whale**, a **Narwhal**, a **Blue Whale**, and **six Dolphins**. All moves below
are described from that player's own point of view (moves flip for the opponent).

| Piece | Symbol | Move |
|-------|:------:|------|
| **White Whale** | W | One square in any of the 8 directions (like a king). It is the **royal** piece — losing it loses the game. |
| **Porpoise** | P | One square **sideways** (left or right) only. |
| **Killer Whale** | K | Any distance **orthogonally** (like a rook) **plus** one square in any **diagonal** direction. (A promoted porpoise — never starts on the board.) |
| **Humpback** | H | One square in any of the **four diagonal** directions, **or** one square straight **backward**. |
| **Grey Whale** | G | Any distance straight **forward**, **or** any distance **diagonally backward**. |
| **Narwhal** | N | **Jumps** to the second square straight ahead (leaping over any piece), **or** one square straight **backward** or **sideways**. |
| **Blue Whale** | B | One square straight **forward** or **backward**, **or** one square **diagonally forward**. |
| **Dolphin** | D | One square straight **forward**. Only while it stands on the **farthest rank** it may instead slide any distance **diagonally backward**. |

A piece may not move onto or through a square occupied by a friendly piece (the
Narwhal is the sole leaper). Moving onto an enemy piece captures it.

## Setup

```
B N P W G H     ← White (Gote), top
d d d d d d
. . . . . .
. . . . . .
D D D D D D
H G W P N B     ← Black (Sente), bottom
```

From each player's own view the back rank is, left to right,
**Humpback – Grey Whale – White Whale – Porpoise – Narwhal – Blue Whale**
(the White Whale sits just left of centre), with the six Dolphins on the rank in
front. The two armies are a 180° rotation of each other. **Black (Sente) moves
first.**

## Capturing, drops and promotion

Captured pieces are **kept in hand** and, on a later turn, may be **dropped**
onto any empty square (facing their new owner) instead of moving a piece — exactly
as in Shogi. A drop may not itself capture.

**There is no promotion zone.** The only promotion is the **Porpoise**, and it
promotes **only at the moment it is captured**: it enters the capturer's hand as a
**Killer Whale** and can only ever be dropped (and thereafter played) as a Killer
Whale. A captured Killer Whale stays a Killer Whale. No other piece ever promotes.

**Dolphin drop restrictions** (these apply to Dolphins only — every other piece
drops without restriction, including onto the last rank):

1. A Dolphin may not be dropped onto the **farthest rank**.
2. A Dolphin may not be dropped onto a file that already holds **two** of your own
   Dolphins (at most two Dolphins per file).
3. A Dolphin may not be dropped to deliver **immediate checkmate** (the
   *uchifuzume* rule).

## Winning and draws

Capturing the opponent's **White Whale wins** — in practice this means
**checkmate** (leaving the opponent no way to save their White Whale). A player
with no legal move loses. Fourfold repetition of a position is a **draw**, and a
ply cap guarantees the game terminates.

## Notation

As in Shogi: a board move is `from>to` (e.g. `4,0>4,2`); a drop is `L@c,r` (e.g.
`K@2,3`). Coordinates are `col,row` with `0,0` at Black's bottom-left. There is no
promotion suffix (promotion happens only on capture).

## Deviations / interpretations

- The three drop restrictions are documented as **Dolphin-specific** on Wikipedia
  and are implemented that way (the *uchifuzume* / drop-checkmate ban applies only
  to Dolphin drops, mirroring Shogi's pawn-only rule).
- The win condition "capture the White Whale" is realised, as in the Shogi engine,
  as checkmate/stalemate: a side with no legal reply that can save its White Whale
  loses. Kings are never literally captured on the board.
