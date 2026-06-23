# Catchup

*Catchup* (a.k.a. *Catch-Up*) is a group-building game for two players, designed
by **Nick Bentley** (2010). It is famous for its tiny ruleset and its elegant
self-balancing "catch-up" mechanism: whenever you pull ahead, you hand your
opponent extra material.

## Board

A **hexagon of hexagons** ("hexhex") of **side 5 = 61 cells**. Cells use axial
coordinates `q,r` (with the implied cube coordinate `s = -q-r`); a cell is on
the board iff `max(|q|, |r|, |s|) ≤ 4`. Each cell has up to **six** neighbours.

The two players are **Black** (player 0, moves first) and **White** (player 1).
Stones are placed on empty cells, never move, and are never captured.

## Groups and score

A **group** is a maximal set of connected, same-colour stones (connected = a
chain of 6-adjacent neighbours). A single lone stone is a group of size 1.

A player's **score** at any moment is the size of their **largest group**
(0 before they have placed any stone, 1 after their first stone).

## How many stones you place — the catch-up rule

This is the heart of the game. A turn places stones of your own colour on
distinct empty cells:

1. **The very first move of the game places exactly ONE stone** (Black, one
   stone).
2. On every later turn you normally place **1 or 2 stones** (your choice).
3. You **MAY place up to 3 stones** if your opponent, on their immediately
   preceding turn, **increased their score** AND their score is, at the start
   of your turn, **greater than or equal to your score**. In other words: when
   the opponent just pulled level with or ahead of you by growing their biggest
   group, you get to *catch up* with an extra stone.

You never have to use the extra stone — when allowed 3 you may still place 1 or
2. You also place fewer than the cap only if the board can't fit more (near the
very end).

> **Ruleset note / canonical wording.** This package implements the canonical
> rule as stated by Nick Bentley and used by Little Golem:
> *"On your turn, you may place 1 or 2 stones, or up to 3 if your opponent's
> score increased on their last turn and is, at the beginning of your turn,
> greater than or equal to your score."* The original mindsports phrasing
> describes the trigger as the opponent creating a group **larger than the
> largest group of either colour** that existed at the start of their turn; for
> the per-player "score = your own largest group" reading used here the two
> coincide in normal play, and this version is the one Bentley documents
> directly. Either way the intent is identical: you get the extra stone exactly
> when the opponent has just grown their lead/tie.

A move is encoded as a `>`-separated path of the placed cell ids, e.g.
`0,0>1,-1` (two stones) or `0,0>1,-1>2,-2` (three stones); a single-stone turn
is just `0,0`.

## End of the game and winning

The game ends when **the board is full** (all 61 cells occupied). Then:

- The player with the **larger largest group wins**.
- **Tie-break:** if both largest groups are the same size, compare the two
  players' **second-largest** groups; if still tied, the third-largest, and so
  on, until a pair differs. The owner of the larger group in that pair wins.

Because every cell ends up owned and the comparison walks down the full sorted
list of group sizes, **Catchup cannot end in a draw** (the two players own
different numbers of cells parity-permitting, and even with equal cell counts
the sorted group-size sequences cannot be identical — see Bentley's proof).

## Strategy in one line

Growing your biggest group is good, but doing so often *gifts* your opponent a
third stone next turn — so the tension is between racing ahead and not handing
over too much tempo.

Official source: Nick Bentley's design notes (see the BGG page linked in-app).
