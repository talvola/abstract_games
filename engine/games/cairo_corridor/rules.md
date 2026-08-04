# Cairo Corridor

A placement game for 2 players by **Markus Hagenauer** (rules © 2012), published
by **nestorgames** in 2013 (rulebook © Néstor Romeral Andrés). The board is a
**Cairo pentagonal tiling** — the paving pattern of several streets in Cairo, and
the dual of the snub square tiling.

These are the rules **as implemented here**, taken from the publisher rulebook
`nestorgames.com/rulebooks/CAIROCORRIDOR_EN.pdf`.

## The board

72 pentagons, arranged as a 6 × 6 grid of two-pentagon **blocks**. A block holds
either a *West | East* pair (side by side) or a *North / South* pair (one above
the other), and the two kinds alternate like a checkerboard, which is what
produces the Cairo tiling's four pentagon orientations.

Every pentagon has at most 5 neighbours. **"Adjacent" means sharing an EDGE, not
just a corner** — the four pentagons that meet at a cross-shaped corner point are
*not* all adjacent to one another.

Cell ids are `x,y`: `x` = 0…11 numbers the half-columns from the left, `y` = 0…5
numbers the block rows from the **bottom**. A move is a single cell id.

## Play

Players alternate. On your turn, place one pentagon of your colour on **any empty
cell**, subject to a single restriction:

> After the placement there must still be at least one **Corridor** — a group of
> connected *empty* cells that links all four sides of the board.

A placement that would destroy the last Corridor is illegal. There is never a
pass: as long as the game is not over, some placement is legal.

## End of the game and scoring

The game ends when **only one Corridor is left and no more pentagons can be
placed adjacent to it** — that is, when every cell of the Corridor is one whose
occupation would break it.

**The player with more pentagons adjacent to the Corridor wins.** A pentagon is
counted once, however many Corridor cells it touches.

If both players have the same number, the game is a **draw** (see
*Interpretations*).

## Board display

| Colour | Meaning |
|---|---|
| pale yellow | Corridor cells that are already locked in — placing there is illegal |
| pale green | Corridor cells you may still place on |
| grey | a **dead zone**: empty cells cut off from the Corridor. Legal to place on, but they touch nothing that scores |
| red / blue | the two players' pentagons |

This is the same colour language the rulebook's figures use (its Example 3 prints
the still-playable areas in pink, green and blue, and the locked Corridor in
yellow).

## Options

| Option | Choices | Notes |
|---|---|---|
| Board size | 4 (32 pentagons), **6 (72 — the published board)**, 8 (128) | |
| Equal scores | **Draw (rulebook)**, Last player to place loses | see below |

## Interpretations

The rulebook is one page, so a few things had to be pinned down. Each decision
below names the artefact that settled it.

1. **"A clear path of connected cells linking the 4 sides"** is read as: *one
   connected group of empty cells that touches the North, South, West and East
   borders*. Only one such group can ever exist (a group joining North to South
   separates West from East, and this tiling has no diagonal crossings), so "the
   Corridor" is always well defined. All three rulebook figures confirm this
   reading exactly: in each, the printed Corridor is precisely the connected
   empty group touching all four sides.

2. **You may place on ANY empty cell**, including cells in a dead zone, provided
   a Corridor survives. The rulebook says "on an empty cell of the board", with
   the Corridor as the only restriction, and its end condition is qualified —
   "no more pentagons can be placed *adjacent to it*" — a qualifier that is only
   needed if placements further away are possible. The Japanese edition
   (`CAIROCORRIDOR_JP.pdf`) translates the same two sentences.
   Board Game Arena corroborates it from a second implementation: its help page
   says the yellow cells mark the *illegal* moves, and that "these illegal
   pentagons will eventually form the final corridor". That can only be true if
   dead-zone cells are **legal** — a dead cell never joins the Corridor, so if
   it were illegal the yellow set would not converge on the Corridor at all.
   The AbstractPlay implementation instead restricts placement to cells of the
   current Corridor. That restriction appears in neither rulebook, and it is not
   a corner case: dead-zone cells are about a tenth of the legal moves offered
   in random play, at least one is available on roughly two thirds of all turns,
   and about 70% of finished games still have an empty dead zone.

   The **box contents do not settle this**, although they are a good termination
   anchor. The smallest Corridor on the 72-pentagon board is 12 cells, so at most
   72 − 12 = **60 placements = 30 + 30** can ever be made, matching the published
   component list ("30 black pentagons, 30 red pentagons") to the piece; that is
   why no piece-supply rule is needed. But the bound is the *same under both
   readings*: `selftest.py`'s 60-placement witness game never places outside the
   Corridor, and AbstractPlay's own restricted implementation accepts all 60 of
   its moves and ends 30 + 30. The piece count is blind to this question.

3. **A tie is a draw.** The rulebook says only "the player with more pentagons
   adjacent to the Corridor is the winner" and never mentions equal scores —
   and ties are not rare (about 10–15% of random games). Board Game Arena's help
   page and AbstractPlay both add "in case of tie, the last player to play loses
   the game"; that rule is available as the **Equal scores** option, but the
   default follows the printed rulebook and scores a tie as an honest draw.

4. **The running score** shown in the caption before the game ends counts the
   pentagons beside the Corridor cells that are already locked in. The rulebook
   only defines the score at the end, where this is exactly its definition
   (every Corridor cell is locked in by then).

5. **Who moves first** is not stated; the rulebook's own three example positions
   are not even consistent about it. Seat 0 (Red) moves first here. Nothing in
   the rules distinguishes the colours.

## Termination

Every move fills one empty cell and cells are never emptied, so a game is at most
72 plies (in fact at most 60) and can never repeat a position. There is no ply
cap and no repetition rule.

## Source

* Rulebook: `https://nestorgames.com/rulebooks/CAIROCORRIDOR_EN.pdf`
  (md5 `c7ba67c41953c11214466ecd762ee6ad`; byte-identical to the Wayback captures
  of 2021-01-15 and 2024-07-19, so the sheet has never been revised. A Japanese
  edition, `CAIROCORRIDOR_JP.pdf`, translates the same text.)
* BoardGameGeek: <https://boardgamegeek.com/boardgame/137173/cairo-corridor>
  (2013 Golden Geek Best Abstract Board Game nominee)
