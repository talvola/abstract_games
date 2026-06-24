# Symple

**Designers:** Christian Freeling & Benedikt Rosenau (2010)
**Players:** 2 — *First player* (seat 0, shown as **Black**) and *Second player* (seat 1, shown as **White**).

Symple is a group / area game played on the intersections of a **Go board**. You
want as many of your stones on the board as possible while keeping the **number
of separate groups small** — each group costs you a penalty. Stones never move
and are never captured.

This page documents the rules **as implemented in this package**. The official
source is [Christian Freeling's Symple page on mindsports.nl](https://mindsports.nl/index.php/arena/symple/585-symple-rules)
(and [BGG](https://boardgamegeek.com/boardgame/106341/symple)).

## Board

An **odd-sized square** board of intersections — standard **19×19**, with a
**13×13** option. (Cells are addressed `col,row`, 0-indexed.) An even size entered
via options is bumped up to the next odd number.

## A turn — the signature mechanic

A **group** is a set of orthogonally-connected (up/down/left/right) like-coloured
stones; a single stone is a group. On your turn you do **exactly one** of:

1. **Place a new group.** Put one stone on a vacant cell that is **not
   orthogonally adjacent to any stone of your own colour**. (It may touch enemy
   stones.) This starts a brand-new group of size 1.

2. **Grow.** Add **exactly one stone to every one of your groups that can grow**.
   Each group grows by one stone placed on an empty cell orthogonally adjacent to
   it. Rules of growth:
   - **No group may grow more than one stone in a turn.**
   - A single placed stone that is orthogonally adjacent to **two or more of your
     own groups grows all of them at once** (a merge — they become one group, and
     none of them may grow again this turn).
   - You may **not** place a growth stone that would *also* touch a group that has
     **already grown** this turn (you can't grow the same group twice). The rules
     note: *if two groups are grown so that only the two newly-grown stones touch,
     the move is legal* — that case is allowed here, because two fresh growth
     stones touching does not re-grow either original group.
   - A group that is **completely surrounded** (no legal growth cell) simply does
     not grow — you "grow all *possible* groups".

You cannot place a new group **and** grow in the same turn — **except** the
balancing rule below.

## The balancing (pie-style) rule

The player who moves first has an edge. To compensate: **if, and only if, neither
player has grown yet, the second player (White, seat 1) may, in a single turn,
grow all of their groups and then place one new stone.** Once any growth has
occurred by either side, this combined turn is no longer available.

### Seat / colour note (an interpretation)

In the canonical rules **White moves first** and **Black** receives the balancing
turn. This platform's convention is that **seat 0 always moves first**. To keep
"the first player = seat 0", this package **swaps the colour labels**: seat 0 is
shown as **Black** and moves first; seat 1 is shown as **White** and receives the
balancing grow-and-place. The *mechanic* is faithful (the non-first player gets
the one-time grow+place); only the cosmetic colour names are swapped.

## End of the game and scoring

The game ends when the **board is full** (resignation, an option in the original,
is not modelled in the async / bot platform). 

**Score** for each player:

> **score = (number of your stones on the board) − P × (number of your groups)**

where **P** is an **even** penalty constant agreed beforehand. The original allows
P ∈ {4, 6, 8, 10, 12}; this package offers those as the **Group penalty P** option
with **default 8**. (The task brief floated "P = board side N"; the authoritative
source instead fixes P as an even agreed constant in 4..12, so this package
**overrides the P = N suggestion** and uses the source's even-constant rule.)

The player with the **higher score wins**. Because **P is even**, Symple is
effectively **drawless** in real play.

## Move encoding / UX

Stones are placed, so moves are cell ids:

- **New-group placement:** click one empty cell → move `"c,r"`.
- **Grow:** the **`grow`** action button enters grow-mode; then you click **one
  growth cell per still-ungrown group** in turn (the board offers only legal
  continuation cells, and the turn **auto-ends** once every growable group has
  grown). The second player's one-time combined turn is the **`grow_place`**
  button: grow everything, then place a new stone (or end via `end grow` if you
  decline / can't place).
- A **`pass`** appears only in the rare dead position where you have no placement
  and no growable group.

A full grow turn touches *every* group, so it is modelled as a **multi-step,
same-player turn** rather than a single fixed path — this keeps the move list
small (only the next group's options are offered) and lets the generic
click-to-move UI drive it unchanged.

## Termination safeguard

Every turn adds at least one stone to the board (a placement adds one; a grow only
starts if ≥1 group can grow), so the board fills in a bounded number of plies and
the game always terminates. As a defensive net there is a **hard ply cap** (4 ×
number of cells); reaching it resolves by score. This cap is a non-original
safety device and is not expected to trigger in real play.
