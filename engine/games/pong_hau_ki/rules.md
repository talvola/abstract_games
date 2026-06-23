# Pong Hau K'i

Pong Hau K'i is a traditional two-player blocking game played in China and
Korea (the Korean equivalent is sometimes transliterated *Gnow* / *Ou-moul-ko-no*).
It is a tiny game of pure movement and blocking — no captures: you win by
manoeuvring your opponent into a position where neither of their stones can move.

## The board

The board has **five points** and **seven edges** (the counts given by
MathWorld and Wikipedia). It is drawn as a square of four corners plus a
central point:

- the four corners: top-left `tl`, top-right `tr`, bottom-left `bl`,
  bottom-right `br`;
- the centre `c`.

### Exact adjacency (7 edges)

- The centre `c` connects to **all four corners**: `c-tl`, `c-tr`, `c-bl`,
  `c-br` (4 edges).
- Three of the four sides of the square are edges: `tl-bl` (left side),
  `bl-br` (bottom side), `tr-br` (right side) (3 edges).
- The **fourth side — the top, `tl-tr` — is NOT an edge.** Exactly one pair of
  same-side corners is left unconnected.

That single missing edge is the whole game: it is what lets a player become
fully blocked, and so it is what creates Pong Hau K'i's characteristic dynamic.

```
    tl --------- tr      (top side tl--tr is NOT connected)
    | \         / |
    |   \     /   |
    |      c      |
    |   /     \   |
    | /         \ |
    bl --------- br
```

## Setup

Each player has **two stones**. Four of the five points start occupied,
leaving exactly **one empty point** (the centre):

- **Player 0** (Black) occupies the two top corners `tl` and `tr`.
- **Player 1** (White) occupies the two bottom corners `bl` and `br`.
- The **centre `c` starts empty.**

Player 0 moves first.

## Moving

On your turn you slide **one** of your two stones along an edge into the
**single empty point**. There are no captures and no other move types. Because
only one point is ever empty, every legal move moves a stone adjacent to that
empty point into it.

## Winning

A player who has **no legal move on their turn loses** — i.e. when both of that
player's stones are blocked (neither is adjacent to the empty point). The
opponent wins. There is no other terminal condition in normal play.

## Draw / termination safeguard

Pong Hau K'i is a well-known **frequent-draw** game: with best play from both
sides it is a draw, and play tends to cycle without anyone becoming stuck. To
guarantee the engine's termination requirement under random play, a **ply cap**
of 60 half-moves is included: if it is reached without anyone being stuck, the
game is declared a **draw**. This is a defensive no-progress rule, not part of
the traditional ruleset.

## Ruleset choices / notes

- **Which side of the square is the missing edge?** Authoritative sources
  (Wikipedia, the GamesCrafters/GamesmanUni catalogue) describe the graph as
  "the two corners on one side are not directly connected," and place the two
  players on opposite sides with the centre empty. The choice of *which* side
  is purely an orientation of the same 5-node / 7-edge graph. This package
  leaves the **top side (`tl-tr`) unconnected** and starts Black on the top
  corners, White on the bottom corners. The task brief mentioned the *bottom*
  corners being unconnected; that is the identical graph rotated 180°, so the
  game is unaffected. The load-bearing, verified facts — 5 points, 7 edges,
  centre joined to all corners, exactly one square side missing, two stones per
  player, one empty point at start, slide-to-empty, lose-if-you-cannot-move —
  are implemented as documented.

## Move notation

Moves are `from>to` paths of point ids, e.g. `tl>c` (top-left corner to the
centre) or `c>bl` (centre to the bottom-left corner).
