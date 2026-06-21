# Tanbo

**Tanbo** (Japanese for "rice paddy", 田んぼ) is a Go-family **root-pruning** game designed by **Mark Steere** in 1993 and re-released in April 2026 with a denser starting position. Two players, **Black** and **White**, take turns growing their own "roots" while roots that can no longer grow are pruned off the board. The goal is to annihilate your opponent.

## Objective
**Annihilate your opponent.** When all of the roots of one colour have been removed, the player of the other colour **wins**. You can win on either player's turn.

## Board & setup
An **N×N** grid of intersections (the **size** option: 9, 11, or 13; **11** is the default — Steere's examples include 7×7, 11×11, 15×15 and rectangular boards; the traditional board is 19×19).

The board starts **densely seeded** with single black and white stones, thoroughly interspersed, with **one empty point between stones**. In this implementation the seeds sit on the **even sublattice** — every intersection `(c, r)` with both `c` and `r` even — coloured as a checkerboard: the seed at `(c, r)` is **Black** if `(c/2 + r/2)` is even, otherwise **White**. On 11×11 that is **36 seeds, 18 black and 18 white**. Each seed is an isolated single-stone **root**. **Black moves first.**

## Roots
A **root** is a maximally-connected, single-colour group of stones (4-orthogonal adjacency — up/down/left/right; diagonals do **not** connect). A root may be a single stone. **Roots never merge, and new roots are never created** — every move grows exactly one existing root.

The **current root** is the root you grew on your current turn.

## Play — placing a stone
On your turn you place **one** stone of your colour on an empty point that is orthogonally adjacent to **exactly one** of your own on-board stones.

- Adjacent to **zero** of your stones → illegal (you can only extend your own roots).
- Adjacent to **two or more** of your stones → illegal.

Because the new stone touches exactly one of your stones, it joins **exactly one** of your roots: the current root.

## Bounded roots
A root is **bounded** if it is so hemmed in that it cannot grow — there is **no empty point adjacent to exactly one stone of that root and not adjacent to any other stone of that root's colour**. (Equivalently: there is no legal placement its owner could make that would enlarge it.)

## Pruning (capture)
After you place your stone:

1. **Current-root capture.** If your placement has **bounded your current root**, you must immediately remove your **current root** — and only it — concluding your turn.
2. **Non-current-roots capture.** Otherwise, you must immediately remove **every other root** (of **either** colour) that is now bounded, concluding your turn.

So a current-root capture takes precedence: when your own just-grown root is bounded, only it is removed, even if some other root happens to be bounded at the same moment.

## Winning
The instant **all** of one colour's roots have been removed, the other colour **wins**.

A player who, on their turn, has **no legal placement** — no root they can still grow — **loses** (equivalently, the last player able to keep a root alive wins). In practice the game almost always ends by annihilation first.

## Ruleset choices made in this implementation
- **Starting layout — the 2026 dense opening.** Steere updated Tanbo in April 2026 from its original sparse 1993 position (16 stones on a 19×19 board) to a much denser one, "thoroughly interspersed, with one empty point between stones," keeping the rules otherwise identical. This package uses that dense opening: single-stone seeds on the even sublattice with checkerboard colouring (see **Board & setup**). This is the layout shown in Steere's Figure 1.
- **Self-capture is legal and mandatory, not forbidden.** Steere's rules make the **current-root capture** an obligatory consequence of a self-bounding placement (his Figure 3), *not* an illegal move. We follow Steere exactly: the only restriction on a move is the placement rule ("adjacent to exactly one of your own stones"); if that placement bounds your own root, your root is removed and your turn ends. There is therefore **no separate "no suicide" prohibition** — a self-bounding move is always available and is simply resolved by removing your own current root. (This is the faithful reading; some informal descriptions phrase it as "you may not bound your own root," but Steere's published Figure 3 explicitly shows and requires the self-removal.)
- **"Bounded", not "zero liberties".** Unlike ordinary Go, removal is driven by whether a root can still **grow**, not by liberties. A root with empty neighbours can still be bounded if none of those empties is a legal growth point (e.g. each touches two stones of its colour), and these two notions genuinely differ — so this package computes bounded-ness directly.
- **No passing; guaranteed termination.** There is no pass. Every move grows a root by one stone or prunes a root; the game cannot loop, and a player with no legal move loses. A hard ply cap (4000) is included purely as a conformance safety net and is unreachable in real play (full games run a few hundred plies on 11×11).
- **Board parity.** Tanbo boards are odd-sided; an even `size` is bumped up by one to keep the seeding symmetric.
- **Coordinates.** Moves are `c,r` (0-indexed column,row). The move log uses Go-style column letters (skipping `I`) with row numbers counted from the bottom.

## Credits
Tanbo is © Mark Steere. The official rule sheet (linked as the "official source") is at marksteeregames.com. Steere's note permits free publication and programming of Tanbo provided the name and rules are unchanged and the game is attributed to him.
