# King & Courtesan

**Mark Steere, May 2022.** Two players, no chance, no hidden information, **no draws**.

King & Courtesan is played on a checkerboard **turned 45 degrees**, so the first
"row" is a single square — the **home square** — the second row has two squares,
the third has three, and so on. Rows 2 through 5 (on 6x6) are filled with
**courtesans**; the home square holds the **king**, physically a stack of two
like-coloured checkers. Every square of the board is in play.

This package renders the board un-rotated, as a plain square grid: turn the
picture 45 degrees and you have Steere's diagram. Red's home is the bottom-left
corner, Blue's the top-right, and both are tinted. Each side owns the triangle
of squares within Manhattan distance `size − 2` of its own home corner; the long
middle diagonal starts empty.

```
6x6 setup            K / Z = king (a stack of two checkers)
                     c / b = courtesan
 .  b  b  b  b  Z    Red (seat 0, bottom-left) advances up and to the right;
 c  .  b  b  b  b    Blue (seat 1, top-right) advances down and to the left.
 c  c  .  b  b  b
 c  c  c  .  b  b    15 pieces a side on 6x6 (21 on 7x7, 28 on 8x8);
 c  c  c  c  .  b    the empty anti-diagonal is 6 squares (7, 8).
 K  c  c  c  c  .
```

## Goal

**Move your king onto the enemy home square, or capture the enemy king.**
That is the whole win condition. A *courtesan* on the enemy home square is
worth nothing.

## Play

Red moves first. Exactly one move per turn; passing is not allowed and never
necessary (see *Termination* below). There are three kinds of move.

**Non-capturing move.** Any piece — king or courtesan — steps to an adjacent
**empty** square in one of its **three forward directions**. On the rotated
board these are "forward-left", "forward-right" and "straight ahead"; in this
package's coordinates Red's are `(+1,0)`, `(0,+1)` and `(+1,+1)`, and Blue's are
the mirror image. There are no backward or sideways non-capturing moves.

**Capturing move.** Any piece steps onto an adjacent **enemy-occupied** square
in **any of the eight directions** — forward, sideways or backward — capturing
the enemy king or courtesan **by replacement** (the victim leaves the board).
You may never capture your own piece.

**Exchange move.** Your **king** transfers its top checker onto an adjacent
**friendly courtesan** in one of the **three forward directions**. King and
courtesan swap roles: the courtesan becomes the king and the old king square
becomes a courtesan. No piece leaves or enters the board and no square changes
hands — only the crown moves. Only the king can initiate an exchange, and only
forward.

Clicking is two clicks, `from` then `to`. The destination's contents decide
which of the three kinds of move it is — empty means a step, enemy means a
capture, your own courtesan means an exchange — so the notation is unambiguous.

## Termination — no draws, and no cycles

Steere states that draws cannot occur. That is provable, and the game is
**hard finite**: a cycle is impossible *even if both players want one*.

Write `n` for the number of pieces on the board, `A` for the sum over all pieces
of that piece's **advancement** (its Manhattan distance from its owner's home
corner), and `K` for the sum of the two kings' advancements. Then:

- a **capture** lowers `n` by one (`n` never rises — nothing ever enters the board);
- a **non-capturing step** leaves `n` alone and raises `A` by 1 or 2, since every
  such step is forward;
- an **exchange** leaves both `n` and `A` alone — the occupied squares are
  unchanged — and raises `K` by 1 or 2, since the crown moves forward.

So the triple `(−n, A, K)` increases **lexicographically on every single move**,
inside a finite range. No position can ever repeat. Counting each move type
against the range it consumes gives a hard ply bound of **755 on 6x6, 1225 on
7x7 and 1857 on 8x8**; the package carries that bound as a backstop only, and it
is dead code (see *Correctness anchors*).

Steere's essay on finitude (abstractgames.org/finitude.html) is a general design
piece and does **not** contain a proof for this game — it never mentions King &
Courtesan — so the argument above is this package's own.

**A player is never stuck**, so the "must move, cannot pass" rule is always
satisfiable. Also a theorem: look only at the king. Each of its three forward
squares is empty (a step), enemy-occupied (a capture), or friendly-occupied — and
a friendly piece is necessarily a courtesan, since a side has exactly one king,
so that is an exchange. Any on-board forward square therefore yields a legal
move, and all three are off-board only when the king stands on the enemy home
corner — at which point the game is already over.

## Interpretations

The rulebook is short and unusually complete; these are the only judgement calls.

1. **Board size is an option, not a second game.** The rulebook says "6x6 (or
   7x7...)", so the size is explicitly scalable. This package offers **6x6
   (default, the size Figure 1 illustrates), 7x7 and 8x8**. That exact set is
   not an extrapolation: **Ludii's implementation offers 6x6 / 7x7 / 8x8 and
   also defaults to 6x6.** (AbstractPlay's offers only 6 and 8 and defaults to
   8; the choice of default is cosmetic.)
2. **Entering the enemy home square by capture or by exchange also wins.** The
   rulebook says "get your king into the enemy home square" without restricting
   *how*. All three routes are treated identically, which is also what
   AbstractPlay does.
3. **The ply cap ends the game as a draw.** It is proven unreachable (see
   above); it exists so that a future bug ends the game rather than hanging.
   Fabricating a winner there would be dishonest, and a fake tiebreak in a
   "can't happen" branch is exactly the class of bug this project has shipped
   before.
4. **Simultaneous win conditions cannot conflict.** A move that captures the
   enemy king *and* lands your king on the enemy home square (capturing the
   enemy king while it sits on its own home) awards the same player the win by
   either reading, so no precedence rule is needed.
5. **"Adjacent" means the eight king-neighbours of the un-rotated grid.** On the
   rotated board these are the four edge-sharing and four corner-touching
   squares; the rulebook's "three forward directions" are the two forward edges
   plus the forward corner, exactly as Figure 2 draws them.

## How this differs from what we already ship

Not a clone of anything in the library. **Breakthrough** is also a forward-only
race on a square board, but its pieces are identical, it captures *only*
diagonally forward, it has no distinguished piece and it is won by reaching a
whole rank. **Kings' Valley** has a royal piece and a goal square, but pieces
slide until blocked and never capture. **Jeson Mor** is a chess variant with
knights and a central goal square. **Five Field Kono**, **Halma** and
**Conspirateurs** are pure race games with no capture at all. What is peculiar
to King & Courtesan is the combination of a 45-degree board with triangular
home territories, an *asymmetric* move set (three directions to step, eight to
capture), a dual win condition, and the **exchange** — a move that changes
nothing on the board except which piece is royal.

## Correctness anchors

Measured on this implementation:

- **Setup** matches Figure 1 exactly: 15 pieces a side on 6x6 (king + 14
  courtesans), 21 on 7x7, 28 on 8x8, with the `size`-square anti-diagonal empty.
- **Opening move counts** 22 (6x6), 26 (7x7), 30 (8x8), frozen in `selftest.py`.
- **Differential vs. AbstractPlay `gameslib`** (`courtesan.ts`, a second
  rule-enforcing implementation; AGPL, used as an oracle only, no code copied):
  **4,924 positions and 152,329 legal moves compared with zero divergence**
  across 80 games on 6x6 and 8x8, half of them driven by each engine, comparing
  legal-move *cell-pair sets*, the full board, side to move, game-over and
  winner at every ply. Re-run with
  `AP_GAMESLIB=<clone> python3 _diff_gameslib.py --games 40`. AbstractPlay
  exposes only sizes 6 and 8, so 7x7 has no oracle there.
- **A third implementation agrees**: Ludii's `King And Courtesan.lud`
  (`ludii.games/lud/games/King%20And%20Courtesan.lud`, coded by Michael
  Amundsen, dated 2022) independently reproduces the setup (`expand` the home
  corner by `size − 2` orthogonal steps, with a second checker stacked on the
  corner to make the king), the three-forward/eight-capture split, the exchange
  (move the king's top checker forward onto a friendly piece), and both win
  conditions — including that the piece on the enemy home square must be a
  *stack of two* for the win to count. It carries **no repetition or draw rule
  at all**, and it offers **6x6, 7x7 and 8x8** — so the 7x7 board, unavailable
  in AbstractPlay, is corroborated after all.
- **Seat symmetry**: the two armies are congruent under the 180° rotation that
  swaps the seats, and `selftest.py` conjugates the *whole engine* under it —
  move sets, `apply_move`, `returns`, `is_terminal` and `heuristic` — at every
  ply of random games at every size. Consequently random play is ~50/50 by
  seat (measured 49.8 % / 50.9 % / 51.4 % to seat 1 over 1,500 games per size);
  any apparent turn-order skew in a small sample is noise, not a setup or
  mirroring bug.
- **Ply cap never fires**: over 600 random games (200 per size) the longest was
  **11.7 %** of the derived bound; the longest seen anywhere in testing was 182
  plies on 8x8 against a bound of 1857. Every random game ended decisively.
- **Never stuck**: 39,589 random positions, every one with a legal move, and in
  every one the *king itself* had one — the theorem above, checked empirically.
- **A decisive result outranks the ply counter**: 75 real terminal positions
  re-scored with the counter poisoned to the cap, the cap + 1 and 10^9.

## Source

Official rulebook: <https://www.marksteeregames.com/King_and_Courtesan_rules.pdf>
(Copyright © 2022 Mark Steere; he explicitly permits programming the game).
BGG: <https://boardgamegeek.com/boardgame/413118/king-and-courtesan>.

The rule sheet has had exactly **two** revisions, both from May 2022 (Wayback
digests `INBT3OCC…` and `Q3ZTLIHH…`). Their extracted text is byte-identical
and the only difference is a checker-alignment touch-up in Figure 1 — so there
is no earlier ruleset to reconcile.
