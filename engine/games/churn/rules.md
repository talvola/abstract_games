# Churn

**Mark Steere, December 2024.** Two players, Red and Blue, on a hexagonal board of
hexagonal cells, initially empty. Red moves first and the game uses the **pie rule**.

This page describes the rules **as implemented here**. The official sheet is
[Churn_rules.pdf](https://www.marksteeregames.com/Churn_rules.pdf).

## The board

A *hexhex* — a hexagon made of hexagons. Cells are named like `a1`: the row letter
counted up from the bottom row, then the cell's position in that row from the left.

The rule sheet allows a hexagon of **any** size and also irregular ("limping")
hexagons, but adds one hard constraint: *"Only boards with an odd number of cells
should be used, to prevent ties."* Every board offered here has an odd cell count,
so **a tie is impossible** — see *Why there are no draws* below.

## A turn

A **group** is a connected set of same-coloured stones — one stone is already a
group. Only *your own* groups ever matter; enemy stones are irrelevant to what you
are allowed to do.

On your turn you place exactly one stone of your colour on an empty cell. **You do
not get a free choice of cell.** In priority order:

1. **If you can place in isolation — that is, on a cell with no friendly stone next
   to it — you must do so.** Sitting next to *enemy* stones is fine; only friendly
   neighbours count.
2. **Otherwise you must form the smallest group you possibly can.** For each empty
   cell, work out the size of the group the stone would end up in: that is
   `1 + the total size of every friendly group the cell touches` — so a cell that
   welds two friendly 3-groups together makes a group of 7. Only the cells that
   *minimise* that number are legal.

Then, **if your stone joined a group** (i.e. it was not isolated):

3. **Remove every one of your groups that is smaller than the group you just
   formed.** *Strictly* smaller — a friendly group of exactly the same size stays,
   and the new group is never removed. Removals reach the whole board, not just the
   neighbourhood of your placement, and they happen all at once. Your opponent's
   stones are never touched.

That concludes your turn. Growing therefore *costs* you stones, which is where the
name comes from: the position turns over and over.

## Object

**Once the board has filled, at the conclusion of a turn, whoever owns the majority
of the stones on the board wins.**

The words *at the conclusion of a turn* are load-bearing, and the sheet spells the
consequence out: *"If your placement causes the board to be filled, you still have to
finish your turn by removing all friendly groups smaller than your newly formed
group."* So filling the last hole does **not** freeze the count — your own removal
happens first, and it may re-open holes and hand the game to your opponent. Figure 4
of the rule sheet is exactly that trap: Red's placement fills the board 10 stones to
9, the forced removal of Red's lone stone brings it back to 9-9 with one hole, and
Blue's forced reply fills that hole without losing anything and wins 10-9.

## Boards offered here

Churn was "designed to have an extreme churn rate", and the game length grows
explosively with the board. These are **measured** here under uniform-random play:

| Board | Cells | Mean turns per game | Games measured |
| --- | ---: | ---: | ---: |
| **Side 2** (toy) | 7 | 8.1 | 3,000 |
| **Side 3** — the designer's recommendation, and the default | 19 | 69.9 | 2,000 |
| **Limping 3,4,3,4,3,4** — the irregular board the sheet names | 27 | 203.7 | 300 |
| Side 4 *(not offered)* | 37 | 658 | 300 |
| Side 5 *(not offered)* | 61 | **7,404** | 60 |
| Side 6 *(not offered)* | 91 | 84,788 | 4 |
| Side 7 *(not offered)* | 127 | 1,239,914 | 3 |

The measured side-5 mean of **7,404 turns** matches the designer's own published
figure of *"about 7,400 turns to complete a game of Churn on a size 5 board"* almost
exactly — an end-to-end check on the whole ruleset that no single rule test can give.
(Side 7 measures 1.24 million against the sheet's "about 950,000"; with only three
games, whose individual results ranged from 979k to 1.52M, that is the same ballpark.)

**Only the three short boards are shipped.** A side-4 game is ~660 turns and a side-5
game over 7,000: that is not a game you can play by correspondence, and it would keep
the bot thinking for hours. The designer's recommended size 3 is the default. Move
generation is cheap on every shipped board (one flood fill plus a constant amount of
work per empty cell), and the average number of legal moves is small — 3.7 on side 3,
with a third of all turns having only one legal placement at all.

## The pie rule

Red places the first stone. Blue may then either place normally **or** take the
**Swap colours (pie rule)** action: Blue adopts Red's opening stone as a blue stone
and hands the move back to Red. Nothing else changes — Churn treats both colours
identically, so simply recolouring the stone is exactly equivalent to the two players
trading seats. Seat 1 is always Blue and seat 0 is always Red, before and after.

The swap is available only on Blue's first turn.

## Why there are no draws

A hexhex of side *n* has 3*n*² − 3*n* + 1 cells, and 3*n*(*n*−1) is always even, so
that count is **always odd**. The limping board offered here has 27 cells, also odd.
The game only ends on a **full** board, so the two stone counts can never be equal and
there is always a winner. (The code still reports an honest draw if it ever saw an
equal full board, rather than inventing a tie-break — but on these boards that branch
cannot be reached.)

## Why the game always ends

The sheet asserts that "Churn is naturally finite" without proof. Here is one.

Take the multiset of **your own** group sizes, written in descending order, and
compare such lists lexicographically (with a list counting as smaller than any
extension of itself: `(5,3)` < `(5,3,1)`). Your opponent never touches your stones, so
this list changes **only on your own turns** — and on every one of them it strictly
increases:

- **An isolated placement** appends one more `1` at the very end of the list, which is
  a strict extension, hence larger.
- **A placement that joins groups**: let *s* be the size of the group you form. Every
  group you merged was smaller than *s* and at least one group was merged, so your old
  list reads `A` (your groups of size ≥ *s*) followed by a non-empty tail whose first
  entry is < *s*. After the removals your new list is exactly `A` followed by *s*. The
  two agree on `A` and then *s* beats that tail entry — larger again.

Those lists are partitions of the numbers 0…*N* for a board of *N* cells, a **finite**
totally ordered set, so neither player can take more than a bounded number of turns and
play cannot go on forever. **This game therefore ships with no move limit and no
repetition rule at all.** (The derived bound is astronomically loose — real games are
thousands of times shorter — but it is derived from the board's own cell count rather
than pinned to a guess, and the single pie-swap ply, which places no stone, is counted
separately.)

An exhaustive solve of the smallest board (side 2, 7 cells) confirms it directly: the
reachable game graph contains **no cycle at all**, every line ends on a full board with
a strict majority, and the longest possible game is 9 plies (10 if the pie is taken).
That solve also gives the board's value: **without** the pie the first player wins;
**with** the pie the second player wins, which is what the strategy-stealing argument
demands of any correctly implemented pie rule in a draw-free game.

## Notes on this implementation

- Moves are cell ids (`q,r` axial); the move log shows the algebraic cell name, with
  `-3` appended when that placement swept three of your own stones off the board.
- The two placement clauses are one rule in the code: "minimise the size of the group
  the placement would form". An isolated placement forms a group of 1, which is the
  smallest value possible, so clause 1 is exactly the case where the minimum is 1.
- The board-full test is applied **after** the removals, which is the only reading
  under which the sheet's Figure 4 is a win for Blue.
- **No bot heuristic ships with this game.** The MCTS bot only ever consults an
  evaluation when a random rollout is cut short, which on the default board happens on
  27.9% of plies (measured over 14,104 plies at the shipped `max_rollout=50`). Two
  candidates were then measured **head-to-head through the actual bot** (20 games each,
  seats alternated): a stone-count balance scored **0.350** against no evaluation at
  all — i.e. it made the bot *worse* — and a largest-group balance scored **0.600**,
  against a no-evaluation-versus-itself control that came out at **0.450**, so 0.600 is
  inside the noise of a 20-game match. Churn's position turns over so fast that a
  snapshot of the board says almost nothing about the eventual majority. Shipping
  nothing, with the measurement that justifies it, is the honest result.
- **The rule sheet has been silently revised.** The live PDF (md5 `ccfa0adc…`,
  internal ModDate 2025-03-16) replaces the original December 2024 sheet
  (md5 `4d63728b…`, ModDate 2024-12-27). Figures 1 and 2 are unchanged; **Figures 3
  and 4 were completely redrawn**, and the OBJECT paragraph gained the parenthetical
  about finishing your turn — the revision exists precisely to nail down the ordering
  described above. The design notes also revised the side-5 estimate from "about
  8,500 turns" to "about 7,400" (the measurement here, 7,404, backs the new number).
  This package implements the current sheet, and its tests check the superseded
  figures too.
