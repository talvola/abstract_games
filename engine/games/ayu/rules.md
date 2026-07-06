# Ayu — "Attach Your Units"

By **Luis Bolaños Mures** (2011). Official rules: [mindsports.nl](https://mindsports.nl/index.php/arena/ayu/724-ayu-rules). This page describes the rules **as implemented** here.

Two players, Black and White, on the points of an odd-sized square grid (default **11×11**; 9/13/15 selectable). *Adjacent* always means **orthogonally** adjacent. A **unit** is a *singleton* (a stone with no like-coloured neighbour) or a *group* (a set of like-coloured, adjacent stones).

## Setup

The board starts filled with interleaved singletons — 30 per player on 11×11: Black on the odd-numbered ranks at files b, d, f, h, j; White on the even ranks at files a, c, e, g, i, k. No stone starts adjacent to a friend; the corners are empty. **Black moves first.**

## Moving

On your turn you **must** make exactly one of these moves:

1. **Singleton step** — move a friendly singleton to an adjacent empty point.
2. **Group extrusion** — take a stone from a friendly group and place it on a *different* empty point adjacent to that **same group** (the group minus the moved stone). All stones that were joined in a single group before the move must still be joined after it — the group may be split *during* the move, but never left split.

A move may **join** the moved unit to another friendly unit (they become one group). Units are never captured or removed.

**The distance rule:** every move must **reduce the distance between the moved unit and the closest friendly unit**. The distance between two units is the length of the shortest path of adjacent **empty** points between them — the number of moves one would need to join them (stones of either colour block the path).

*Interpretation note:* following the official Dagaz implementation on mindsports.nl, this package enforces the rule as: the moved unit's **new closest distance must be strictly smaller than its old closest distance**, and a move that *joins* the moved unit to another friendly unit is always legal. (This is provably the same as "get closer to one of the currently-closest friendly units", the phrasing on other rules pages: a single move can shorten any unit-pair distance by at most 1, so the closest distance can only drop via a unit that was already closest.) A unit with **no** friendly unit reachable through empty points cannot move at all.

## Object

**If you cannot make a move on your turn, you win.** This normally happens when you have attached all your stones into a single group (with no second friendly unit to approach, no move is legal) — but being completely locked in by the opponent also counts, so beware of over-enclosing.

## Draw

If a **position repeats with the same player to move**, the game is a draw (only possible through mutual cooperation). A generous hard move cap (8×n×n plies) additionally guarantees termination.

## Pie rule

With the pie option on (default), after Black's first move White may play **swap** instead of a regular move: the players change sides, and the (new) White player moves next.

## Notation

Moves are `from>to` clicks — select one of your stones, then a highlighted destination. `swap` appears as a button on White's first turn.

*Sources: [official rules](https://mindsports.nl/index.php/arena/ayu/724-ayu-rules) and the mindsports [Dagaz implementation](https://mindsports.nl/index.php/dagaz/836-ayu) (used to pin down the distance-rule reading and the starting pattern); cross-checked against [rmwinslow.com](https://games.rmwinslow.com/rules/abstract-ayu.html). [BGG](https://boardgamegeek.com/boardgame/114484/ayu).*
