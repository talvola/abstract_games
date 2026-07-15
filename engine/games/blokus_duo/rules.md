# Blokus Duo

**Bernard Tavitian** — the two-player version of *Blokus* (Sekkoïa 2005; Mattel FWG43/R1984).
Rules below are **as implemented**, from the Mattel *Blokus Duo* (FWG43) and *Blokus* (R1983)
rulebooks.

## Board and pieces

- The board has **196 squares (14×14)**.
- Each player has **21 pieces** — every *free polyomino* of size 1 to 5:
  - **1** one-square piece, **1** two-square piece, **2** three-square pieces,
    **5** four-square pieces, **12** five-square pieces.
- Pieces may be **rotated and flipped** freely. (This is exactly why there are 21 of them:
  counting reflections as distinct would give 29.)
- The two **starting points** are marked on the board — the 5th row and 5th column in from
  opposite corners, on a diagonal.

Pieces are named with the standard polyomino letters, size-suffixed:
`I1` (single square), `I2`, `I3` `V3`, `I4` `L4` `N4` `O4` `T4`,
and the twelve pentominoes `F5 I5 L5 N5 P5 T5 U5 V5 W5 X5 Y5 Z5`.

## Play

1. Player 1 places one of their pieces on their starting point; Player 2 places one of theirs on
   the second starting point. **A player's first piece must cover their own starting point.**
2. Players then alternate, laying down **one piece per turn**:
   - **"Each new piece must touch at least one other piece of the same colour, but only at the
     corners."**
   - **"Pieces of the same colour cannot be in contact along an edge."**
   - **"There are no restrictions on how pieces of different colours may contact each other."**
   - Pieces may not overlap, and must lie entirely on the board.
3. Once placed, a piece **cannot be moved** for the rest of the game.
4. **"When a player is unable to place one of their remaining pieces on the board, that player
   must pass."** Passing is automatic here — the turn simply skips a blocked player, so you are
   never asked to pass by hand.
5. **"The game ends when both players are blocked from laying down any more pieces."** This
   includes a player who has placed all of their pieces.

## Scoring

Counted at the end, for each player:

- **−1 point per unit square** in your remaining (unplaced) pieces.
- **+15 points** if you placed **all 21** of your pieces.
- **+5 additional points** if you placed all 21 *and* the **last piece you placed was the
  one-square piece**.

So a player who places everything scores **+15**, or **+20** if they finished with the single
square. The rulebook's own worked example: a player who could not place two three-square pieces
and one four-square piece scores **−10**.

**Highest score wins.**

## Interpretations

The rulebooks leave two points open; this implementation resolves them as follows.

- **Ties are an honest draw.** Both rulebooks say only that "the player with the highest score is
  the winner" and say *nothing* about equal scores — but a tie is plainly reachable (both players
  stranding the same number of squares is ordinary). Rather than invent a tiebreak, an equal score
  is recorded as a **draw**.
- **The +5 requires the +15.** The rulebook wording is "+15 points if all of his/her pieces have
  been placed on the board **plus 5 additional bonus points** if the last piece placed on the
  board was the smallest piece". "Additional" reads as additive on top of the all-21 bonus, and
  the Duo rulebook's example scores such a player **+20** while its strategy tips say a player who
  places every piece "can gain up to 20 points". So the +5 is only awarded together with the +15,
  never on its own.
- **Which player starts on which point** is a free choice in the rulebook ("Player 1 places one of
  their pieces on **one of** the two starting points"). The two points are related by a 180°
  rotation of the board and nothing else about the game is asymmetric, so the choice is
  cosmetic; Player 1 is assigned the point at `e10` and Player 2 the point at `j5`.

## Notation

A move is `KEY:o@c,r` — the piece `KEY`, its orientation index `o`, anchored at cell `c,r`
(the piece's bottom-most, then left-most square — always a square the piece covers). In the app
you simply click a piece in your tray, pick an orientation, and click a highlighted square. The
move log shows e.g. `F5@e10`.
