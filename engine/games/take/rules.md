# Take

**Take** (Japanese 竹 *take*, "bamboo") is a two-player abstract designed by **Mark Steere** in **February 2024**, with a material contribution to the design by **Michael Amundsen**. Steere calls it "a long sought (by me) **free-form Tanbo** — that is, new seeds can be added."

Red and Blue grow monocoloured groups on a hexagonal board that starts completely full of neutral brown **clods**. A group that can no longer be grown is **bounded**, and every bounded group — yours as much as your opponent's — is swept off the board the instant it becomes bounded. **Remove all enemy stones to win.**

## Board

A regular hexagon of hexagonal cells (a "hexhex") of side *n*. The **size** option offers sides 2 (7 cells), 3 (19), 4 (37), **5 (61, the default)** and 6 (91). Every figure in Steere's rule sheet uses side 3; side 5 is AbstractPlay's board. Steere's sheet just says "hexagonal board of any size".

Cells are named by axial coordinates `q,r`, with the board being every `(q, r)` such that `|q|`, `|r|` and `|q+r|` are all at most *n*−1. Rows (constant `r`) are horizontal — pointy-top hexes, exactly as the rule sheet draws them.

**Every cell begins occupied by a clod:** a neutral brown stone belonging to neither player. In this implementation a clod is drawn as a **brown cell**, so the renderer's legal-placement dots stay visible (see *Ruleset choices* below).

## Play

**Red moves first.** On your turn you place exactly one stone of your colour. Two kinds of placement exist:

| | may be placed on | friendly stones it must touch |
|---|---|---|
| **Seed** | a **clod** cell only (the clod is removed) | **zero** |
| **Growth** | any **clod** cell (clod removed) or any **bare** cell | **exactly one** |

A **bare** cell is one holding neither a stone nor a clod — a cell whose clod has already been eaten. **A seed can never be placed on a bare cell**: seeding *is* the act of replacing a clod.

So the test on any stone-free cell is:

```
clod cell : friendly neighbours <= 1     (0 = seed, 1 = growth)
bare cell : friendly neighbours == 1     (growth only)
```

### Groups

A **group** is a maximal set of same-coloured stones connected through the six hex directions. Because a growth stone touches **exactly one** friendly stone, groups can never merge and a growth stone always joins exactly one existing group; a seed starts a brand-new group of one.

### Bounded groups

> **BOUNDED GROUP** — Monocolored group which cannot be expanded with the placement of an adjacent, like-colored stone.

Written out: a group **G** of colour *c* is **bounded** when **no** stone-free cell next to **G** could legally take a *c*-coloured stone. Since any cell next to **G** already has at least one *c*-neighbour, the clod rule (`<= 1`) and the bare rule (`== 1`) collapse into the same condition, and the definition reduces to:

> **G is bounded ⟺ every stone-free cell adjacent to G has two or more stones of G's colour beside it (counting the whole board, not just G).**

That last parenthesis is the subtle part, and it has two faces. The easy one is a cell blocked twice over by a *single* group: in Figure 1 the bare cell `2,-1` touches `1,-1` and `2,-2`, both of them stones of Red's one big group, so no red stone may ever be placed there. The sharp one is a cell blocked by **two different red groups at once** — Figure 1 contains no such cell, but Figure 2a does, and that is what decides the figure (see below).

### Group removal

> **GROUP REMOVAL** — If your placement bounds any groups, including the group expanded by your placement, immediately remove all groups so bounded, concluding your turn.

All bounded groups are identified on the board **as it stands right after your placement**, and then **all are removed at once**. The removals are **simultaneous**, not sequential — and Figure 2 of the rule sheet proves it (see below). Both colours are swept; your own doomed group gets no protection.

Unlike Tanbo there is **no "current root" precedence**: in Tanbo, self-bounding your just-grown root removes *only* that root. In Take everything bounded goes together.

## Object of the game

> To win, you must remove all enemy stones from the board. If your placement eliminates all red and blue stones, you win. If your placement eliminates all friendly stones while enemy stones remain on the board, you lose.

Three outcomes, all decided by *your own* placement:

1. it clears the last enemy stone → **you win**;
2. it clears every stone of both colours → **you win**;
3. it clears your last stone while enemy stones survive → **you lose**.

**There are no draws**, and no player is ever stuck — see *Termination* below.

## High Churn variant

> Each cell of the board is initially covered by a brown **tile** instead of a brown stone. To place a seed, remove an unoccupied tile and replace it with the seed. Other than seeds, stones can be placed subject to the adjacency rules described above, but by placing on a cell with no tile and no stone or by placing on top of an unoccupied tile.

The single difference: **only a seed consumes a tile.** A growth stone placed on a tiled cell sits **on top of** the tile, and when that stone is later swept away the tile is still there. In the base game a clod is eaten by *any* placement and never comes back.

The consequence is exactly what the name says: tiles deplete far more slowly, so fresh seeds keep being available and the board turns over and over. In this implementation a tiled cell is brown whether or not a stone stands on it; measured against random play the High Churn game runs roughly **1.6–1.9× longer** than the base game on the same board.

Object and removal rules are identical in both versions.

## The rule sheet's figures, worked

All three figures are reproduced as assertions in `selftest.py`, transcribed from the PDF's vector geometry rather than by eye.

**Figure 1** (side 3, Red to move) marks Red's four legal placements. The board holds 12 stones, 5 clods and 2 bare cells; the red dots are `0,-2` (a **seed** — a clod with no red neighbour), `-1,-1`, `-2,2` (clods with exactly one) and `2,0` (a **bare** cell with exactly one). The three cells with no dot are excluded for named reasons: `1,-2` and `0,2` are clods with **two** red neighbours, and `2,-1` is bare with two.

**Figure 2a → 2b** (base game). Red seeds `0,2`. That one stone bounds **three** groups at once: two red (the `-2,0 / -2,1 / -1,1` chain, plus the seed itself) and one blue (`-1,0 / 0,0 / 1,0 / 1,1`) — eight stones. It works because the seed lands on the blue group's *only* remaining growth cell, and because it gives `-1,2` and `0,1` a second red neighbour, killing the red chain's last two growth cells.

This figure also **pins the simultaneity of removal.** Both `-1,2` and the red chain touch the seed. If the chain were removed *first*, `-1,2` would fall back to exactly one red neighbour, the seed would no longer be bounded, and it would survive — contradicting Figure 2b, where it is gone. So the bounded set must be computed before anything is taken off.

**Figure 3a → 3b** (High Churn). Red grows onto the bare cell `1,1`, which was the blue group `2,-1 / 1,0 / 0,0`'s only growth cell. The three blue stones come off and their cells **revert to bare tiles** — the picture of tile persistence.

## Termination — proved, with no ply cap and no repetition rule

Let **K** be the number of clods (or tiles) still on the board, **G** the number of groups, and **U** the number of stone-free cells. The triple **(K, G, U)** strictly decreases *lexicographically* on **every single ply**:

- a placement that eats a clod/tile lowers **K**;
- otherwise the stone is a growth stone on a cell that keeps (or never had) a clod, so **K** is unchanged and **no new group is created**. If the ply removes any group, **G** drops. If it removes none, a stone was added, so **U** drops.

With `0 <= K, G, U <= C` (*C* = cell count), play is finite — a crude derived ceiling of `(C+1)³` plies. **The game therefore ships with no ply cap, no repetition rule and no draw**; nothing in the implementation can decide an outcome by a counter. An exhaustive solve of the side-2 board confirms the reachable game graph is a directed acyclic graph: a position can never repeat. Random play on the standard side-5 board averages ~119 plies (base) and ~220 (High Churn); over 250 random games on the largest and longest configuration (side 6, High Churn) the average was 381 and the longest **518** — far below the conformance harness's 3,000-ply ceiling, so no `max_random_plies` override is needed either.

**Nobody can ever be stuck**, either. Removing bounded groups can never *bound* a surviving group: if a stone-free cell `X` witnessed that group **G** could grow (exactly one friendly neighbour, and that neighbour inside **G**), then after the sweep `X` is still stone-free and that neighbour — a stone of **G**, which was not removed — is still standing. So no group is ever bounded at the start of a turn, and a player who still owns a group always has a legal placement. A player who owns none has already lost. The only turns on which a player owns nothing are plies 1 and 2, when the board is still full of clods and every cell takes a seed.

## Ruleset choices made in this implementation

- **Total annihilation is a win for the mover — the reference implementation disagrees.** Steere is explicit: *"If your placement eliminates all red and blue stones, you win."* AbstractPlay's `gameslib` `take.ts` awards that position to the **opponent** (its `checkEOG` tests `reds.length === 0` before `blues.length === 0`, so when both are empty the first branch fires and the wrong player is credited). The position is reachable — 3 of 300 random side-5 games, 2 of 300 in High Churn, and about 40% of random side-2 games — so this is a real divergence, adjudicated in the rule sheet's favour. It is also the **only** divergence: a 100-game differential against `gameslib` over 11,904 plies (five board sizes × both variants × both sides driving) found identical legal-move sets and identical per-cell board contents at every single ply, and identical winners on every game that did not end in total annihilation.
- **"Remove all enemy stones" means *remove*.** After Red's very first placement Blue has no stones on the board, but nothing has been removed and the game obviously is not over. The win test therefore requires that the opponent **had** at least one stone before your placement. That guard bites on ply 1 and never again (from ply 2 on, a side with no stones has already lost).
- **A bounded group is judged against the whole board, not just against itself.** Because the placement rule counts *all* friendly neighbours, a cell adjacent to your group can be blocked by a second group of your own colour. This is what makes Take's endgame sharp, and **Figure 2a** is where the rule sheet shows it: `0,1` and `-1,2` are each blocked by one stone of Red's `-2,0/-2,1/-1,1` chain *plus* the freshly placed seed at `0,2` — two different red groups — which is precisely why the seed and the chain bound each other and both come off. (Figure 1's `2,-1` is only the easier same-group case: `1,-1` and `2,-2` belong to one and the same red group.)
- **Removal is simultaneous.** Forced by Figure 2 (see above); `gameslib` agrees.
- **No draw, no ply cap, no repetition rule.** All three are *proved* unnecessary rather than assumed, and the smallest board is solved exhaustively to confirm. Steere's sheet says nothing about a player unable to place, because it cannot happen.
- **Clods are drawn as brown cells, not brown discs.** The rule sheet draws a base-game clod as a brown *stone* and a High-Churn tile as a brown *hexagon*. The web renderer suppresses its legal-move dot on any cell that carries a piece — and in Take nearly every legal placement lands on a clod — so a clod disc would hide the move hints exactly where they matter. Rendering both as a brown cell keeps every hint visible and makes the two variants read consistently: brown means "there is brown stuff here", with a stone drawn on top when one stands on a High-Churn tile.
- **No bot heuristic, deliberately — and measured, not assumed.** The obvious candidate is the stone-count balance. It carries no usable signal: over 300 random games the sign of the balance at 80% of the way through the game agreed with the eventual winner 50/140 times on side 4 (**0.357** — *anti*-correlated) and 69/144 on side 5 (0.479); the group-count balance gave 0.538 / 0.486. Measured through the actual consumer, `MCTSBot` (side 4, `max_rollout=8` so the eval is reached on essentially every rollout, seats alternated), a `tanh` stone-balance evaluation won only **8 of 31** games against the same bot with no evaluation at all (one-sided binomial p ≈ 0.004) — i.e. it is not merely useless but actively *harmful*. That fits the game: a big group is a big liability, because the more stones it has the more cells there are that can be blocked. So this package ships **no** `heuristic`, and the MCTS bot falls back to its draw evaluation at the rollout cutoff.
- **Board sizes.** Sides 2–6 are offered. Side 2 (7 cells) is a solved toy included because it is the package's exhaustive correctness anchor (a **second-player win** in both variants); side 3 is the rule sheet's figure board; side 5 is the default and AbstractPlay's board.
- **Move notation.** A move is the axial cell id `q,r`. The move log reads e.g. `Red 0,2 seed ×8 (incl. 4 own)` — the cell, whether it was a seed, how many stones the placement swept off and how many of those were your own.

## Take vs Tanbo (the package's closest neighbour)

Take is Steere's own "free-form Tanbo", and the two are genuinely different games:

| | **Tanbo** (1993/2026) | **Take** (2024) |
|---|---|---|
| Board | N×N square grid, 4-orthogonal | hexhex, 6 neighbours |
| Start | densely seeded with single stones | **completely full of neutral clods** |
| New groups | **impossible** — every move grows an existing root | **seeds** create new groups all game (this is the whole point) |
| Placement cell | any empty point | a **clod** (seeds and growth) or a **bare** cell (growth only) |
| Neutral material | none | clods / tiles, a depleting resource that gates seeding |
| Self-bounding | **current-root precedence**: only your own root is removed | no precedence — every bounded group of both colours goes at once |
| Stuck player | loses | **cannot happen** (proved) |
| Variant | — | High Churn (tiles survive the stones on them) |

Mechanically the shared skeleton is "place adjacent to exactly one friendly stone; a group that cannot grow is removed". Everything that shapes actual play — where new material comes from, whether you can open a new front, and whose groups die together — differs.

## Credits

Take is © 2024 Mark Steere; Michael Amundsen contributed to the design. The official rule sheet (linked as the "official source") is at [marksteeregames.com](https://marksteeregames.com/Take_rules.pdf). Steere's note permits free publication and programming of Take provided the name and rules are unchanged and the game is attributed to him.
