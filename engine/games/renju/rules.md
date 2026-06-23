# Renju

**Renju** is professional Gomoku: five-in-a-row on a **15×15** board, with extra
restrictions (handicaps) on the first player to offset Black's first-move
advantage. Player 0 is **Black** and moves first; player 1 is **White**.

This package implements the **base Renju forbidden-move ruleset only**. It does
**not** implement opening rules (no swap, no "Soosõrv"/"Taraguchi" opening, no
restriction on Black's first stone beyond the forbidden moves below). See
*Ruleset choices* at the end.

## How to play

- On your turn, place one stone on any **empty** cell. Stones never move or get
  captured (placement only, exactly like Gomoku).
- Cells are `col,row` (0-indexed); a move is a single empty cell.

## Winning — the five-vs-overline asymmetry

The win condition is **asymmetric** between the two players:

- **White wins with FIVE OR MORE in a row** (horizontal, vertical, or either
  diagonal). An **overline** (six or more white stones in a row) **wins for
  White**. White has **no** restrictions of any kind.
- **Black wins ONLY with an EXACT FIVE in a row.** A Black **overline** (six or
  more in a row) is **NOT a win** for Black — in fact it is a *forbidden move*
  (see below), so making one loses the game for Black.

## Black's forbidden moves

After Black places a stone, if that move creates **any** of the following — and
the move does **not** simultaneously make an exact five — Black **loses the game
immediately** (scored as a win for White):

1. **Double-three (3-3)** — the move makes **two or more open threes**.
2. **Double-four (4-4)** — the move makes **two or more fours**.
3. **Overline** — the move makes a row of **six or more** Black stones.

### The "five takes precedence" rule

An **exact five always wins for Black**, even when the same move would otherwise
be a forbidden move. So if Black's move simultaneously makes an exact five *and*
(say) a double-four or an overline, the **five-win takes precedence** and Black
wins. Forbiddenness is only evaluated when the move did **not** make an exact
five. (Note: a move that makes a *six-in-a-row* does not make an exact five, so a
pure overline with no separate exact-five line is a forbidden loss.)

## Exact definitions used (the crux)

These follow the standard **Renju International Federation (RIF)** recursive
definitions. All shapes below are about **Black** stones only (White is
unrestricted).

- **Five**: exactly five Black stones in an unbroken row. (Six or more is an
  overline, not a five.)

- **Four**: a configuration of Black stones along a line such that a **single**
  Black move on that line would complete an **exact five**. A move "makes a
  four" along a direction if, after the move, there is at least one empty point
  on that line whose addition makes an exact five through the placed stone. A
  **straight four** (open four, the shape `_BBBB_`) has **two** completing
  points but counts as a **single** four. **Double-four** = the move creates
  fours along **two or more distinct directions**.

- **Open three**: a configuration of **exactly three** Black stones along a line
  that can be developed, by a **single** Black move at an empty point on that
  line, into a **straight four** (`_BBBB_`, two completing points). A three has
  at most three stones in its run, so a configuration that is **already a four**
  (a straight four `_BBBB_` or any run of four) is a **four**, *never* an open
  three — only the still-three shapes (e.g. `_BBB_` and the broken three
  `_BB_B_`) count. The developing stone must actually **extend this three**
  into the open four (lengthening the placed stone's line to four), not merely
  recomplete a pre-existing four. **Double-three** = the move creates open
  threes along **two or more distinct directions**. (A **four-three** — one four
  and one open three, e.g. a straight four crossing an open three — is therefore
  a *legal* and strong move, **not** a forbidden double-three.)

- **Recursive legality (RIF):** an open three only counts toward a double-three
  if the developing point (the stone that turns the three into a straight four)
  is itself a **legal** Black point — i.e. placing there is not itself a
  forbidden move that destroys the shape. This is checked **recursively** (with
  a small depth bound for the rare deeply nested cases). Likewise, a five always
  overrides forbiddenness, so the completing point of a four is never blocked.

## Termination

The game terminates automatically. A win (five, or a Black forbidden-loss, or a
White overline) ends it; otherwise a completely full board (≤ 225 placements)
with no decisive line is a **draw**.

## Ruleset choices (documented)

- **No opening rules.** Only the base forbidden-move handicap is implemented, as
  requested. Black's first move is unrestricted (apart from the forbidden-move
  rules, which a single stone can never trigger).
- **Forbidden move = legal-but-losing.** A Black forbidden move is offered as a
  *playable* move that **loses immediately**, rather than being filtered out of
  the legal-move list. This keeps the game tree well-formed and matches how
  Renju scores a forbidden move (it ends the game as a loss for Black).
- **Faithfulness flag on open-three detection.** The recursive open-three /
  straight-four detection is the genuinely subtle part of the RIF ruleset and
  the most likely source of edge-case disagreement between implementations
  (different engines handle deeply nested recursion and "false threes" slightly
  differently). This package implements the standard recursive RIF definition
  with a depth bound; common shapes (open threes, broken threes `_BB_B_`,
  straight fours, and the textbook double-three/double-four/overline positions)
  are handled correctly, but exotic deeply nested positions may differ from a
  particular reference engine. The exact-five, overline, and double-four rules
  are exact; the double-three (open-three) detector is the documented
  approximation point.
