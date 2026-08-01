# Ūnane

*A game by Mark Steere, April 2026.* Pronounced **ooh-NAH-nay**.

Ūnane is played on a **Kōnane board** — a rectangular grid of pits, each holding
one stone — which starts completely filled with a checkerboard of black and
white stones. The name fuses *una* (Spanish for "one") with *Kōnane*, and the
game is a tribute to that ancient Hawaiian game: a checkerboard start, very
short-range captures, and extremely simple rules.

This package offers boards of **W columns × (W−1) rows** with W even, so at
least one dimension is even as the rule sheet requires. The default is **8×7**.

## The board and the setup

Every pit holds a stone, in a strict checkerboard. The **top-left pit is
black**.

```
8x7, the standard board (Black = #, White = O)

  # O # O # O # O
  O # O # O # O #
  # O # O # O # O
  O # O # O # O #
  # O # O # O # O
  O # O # O # O #
  # O # O # O # O
```

**Black moves first.** Passing is not allowed.

**Pie rule.** On his first turn White may, instead of playing a stone, **switch
colours and become Black**, claiming Black's opening move as his own. Play then
continues with the other player, now White, to move. The offer is available on
that one turn only.

## Your turn

Each turn you do **exactly one** of the following, with exactly one stone of
your own colour — never both:

### Capture

Move one of your stones onto an **orthogonally adjacent** enemy stone, in any
direction. The enemy stone is captured **by replacement**: it leaves the board
and yours takes its pit.

Captures are one step only. Diagonals do not count, and there is no long-range
move — in the diagram below Black (`#`) can capture any of the whites marked
`*`, but not the one marked `x`, which is only diagonally adjacent.

```
  . O . . .        . * . . .
  O # O . .   ->   * # * . .
  . O O . .        . * x . .
  . . . . #        . . . . #
```

### Removal

Take one of your own stones off the board — but only a stone with **no
orthogonal adjacency to an enemy stone**. Friendly neighbours are fine, and a
diagonally adjacent enemy is fine; only an orthogonally adjacent enemy stone
forbids the removal.

```
  . . # # .        . . * * .
  # O # . .   ->   x O x . .
  . # # . .        . x * . .
  . O . . .        . O . . .
```

Both stones marked `*` in the top row are removable even though they touch each
other, and the upper-left one is removable even though a white stone sits
diagonally next to it. The three marked `x` each touch a white stone
orthogonally.

Because a capture is by replacement and a removal simply takes a stone off,
**exactly one stone leaves the board every turn**.

## Object of the game

You want your stones to form **one single orthogonally connected group** (a lone
stone counts as a group). Only friendly stones connect — empty pits do not link
anything, and diagonals do not connect.

The group counts are checked **after every turn**, so **you can win on your
opponent's turn as well as on your own**:

- if the player who just moved has exactly one group, **he** wins;
- otherwise, if the player who did *not* move has exactly one group, **he**
  wins.

The first clause is the rule sheet's tie-break — "*If, after your turn, there is
only one friendly group and only one enemy group, you win*" — so a turn that
unifies both armies at once is won by the mover.

Note that the sheet's summary sentence names both armies, but its Figure 4
(captioned "Black wins") shows **Black with one group and White with two**, so
the requirement is on *your own* stones alone. This package implements the
figure.

## Things that cannot happen

- **You can never be stuck.** Every stone you own gives you a turn: it either
  touches an enemy stone (so you can capture it) or it does not (so you can
  remove it). Only a player with no stones at all would have no legal turn.
- **You can never run out of stones.** Being reduced to *one* stone means having
  exactly one group, which ends the game immediately, so nobody ever reaches
  zero.
- **The game cannot loop, and cannot be drawn.** One stone leaves the board
  every turn and nothing is ever added, so no position can recur. Play must end
  no later than the turn that reduces someone to a single stone: at most
  `W×H − 3` stone-removing turns, plus the one optional pie swap (which removes
  nothing) — `W×H − 2` plies in all. There is **no ply cap and no repetition
  rule** in this implementation, because neither is needed.

On the smallest offered board (4×3) the game has been solved exhaustively
through this implementation: 84,587 reachable states, no draws, and — **with**
the pie rule — a second-player win. (With the swap suppressed the same board is
a first-player win, which is exactly what a working pie rule should do.)

## Playing here

- Click one of your stones, then click an adjacent enemy stone to capture it.
- To **remove** one of your own stones, click it and then **click it again**.
- White's pie-swap offer appears as a **Swap colours (pie rule)** button on
  White's first turn.
- The move log writes a capture as `b3xb4` and a removal as `-b3`.
- The bot uses a position evaluation based on the difference in group counts.
  It was measured through the bot that consumes it (MCTS, rollouts cut short so
  the evaluation is always reached) on the 6×5 board. Against the *same*
  evaluation with its sign flipped it wins **10-0**, which is what pins the
  direction. Against a constant-zero evaluation the gain is real but **modest
  and seed-dependent** — 29-11 on one set of seeds, 25-15 on an independent
  re-run (54-26 of 80 pooled). It is better than no evaluation at all; it is
  not a strong engine.

## Interpretive decisions

Everything below was decided from the official rule sheet
(`marksteeregames.com/Unane_rules.pdf`, revision of 2026-05-20), whose figures
were transcribed pit by pit.

1. **"One group" is about YOUR stones only.** The prose sentence *"If, after
   your turn, there is only one friendly group and only one enemy group, you
   win"* is symmetric in the two colours and, read literally as the whole
   condition, would make *"You can win on your turn or on your opponent's turn"*
   dead prose. **Figure 4** settles it: it is captioned "Black wins" and prints
   Black with one group and White with **two**. The sentence is therefore the
   tie-break for the both-at-once case, and it awards that case to the mover
   ("after **your** turn ... **you** win"). Note that Figure 4 exists only in
   the current (2026-05-20) revision of the rule sheet — the previous revision
   had three figures and no worked example of the object of the game.
2. **Only friendly stones connect.** The sheet says "one orthogonally
   interconnected group **of your color**" and never mentions empty points,
   where the same designer's *Narrows* explicitly says "via orthogonally
   connected paths of unoccupied points and/or friendly stones". Figure 4 alone
   cannot decide this (under the *Narrows* model both armies would be unified
   there and Black would still be the winner), so the prose and AbstractPlay's
   reference implementation carry it.
3. **Captures are one step, not a slide.** The sheet says "orthogonally
   ... adjacent". Figure 2 rules out diagonal and queen-style captures but
   happens to be blind to a rook-style slide (nothing in that figure is
   rook-visible that is not also adjacent), so the word "adjacent" carries it —
   and it contrasts pointedly with the same designer's *Narrows*, which spells
   out "separated from your stone by empty points only" when it does mean a
   slide.
4. **A removal is blocked only by an ORTHOGONALLY adjacent enemy stone.**
   Figure 3 marks as legal a black stone that touches a friendly stone and a
   black stone that touches a white stone diagonally, which rules out both the
   stricter readings.
5. **A player with no stones has not won** (no groups is not one group). This is
   unreachable, and is implemented to match AbstractPlay's reference code.
6. **The pie swap exchanges the colours**, so after a swap the seat that took
   the pie is Black and owns the army that opened the game. The board is
   otherwise untouched, and the swap removes no stone.

## Sources

- Official rule sheet: <https://www.marksteeregames.com/Unane_rules.pdf> — the
  revision implemented here has ModDate 2026-05-20 (md5
  `d520de357ab036f20629c514a6942340`). The only copy in the Internet Archive is
  the earlier 2026-05-07 revision, which has no Figure 4.
- BoardGameGeek: <https://boardgamegeek.com/boardgame/472126/unane>
