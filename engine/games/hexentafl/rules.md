# heXentafl

**Kevin R. Kane, 2020.** Published by [nestorgames](https://nestorgames.com) and
Kanare_Abstract. A hexagonal member of the Hnefatafl (tafl) family: an
asymmetric siege in which a King and a handful of defenders try to break out
past twice their number of attackers.

Implemented from the publisher's rule sheet
`nestorgames.com/rulebooks/HEXENTAFL_EN.pdf`, cross-checked against the
designer's own pages ([nxsgame.com/hexentafl.html](https://nxsgame.com/hexentafl.html)
and his [2019 announcement post](https://nxsgame.wordpress.com/2019/09/26/hexentafl/)).

## Board and setup

The board is a hexagon of hexes, **4 hexes per side** (37 cells) by default, or
**5 per side** (61 cells) with the *Hex grid* option. The centre cell is the
**throne**; the six cells at the points of the hexagon are the **corners**.

**Seat 0 are the Defenders** — the **King** on the throne plus three men — and
they **move first**. **Seat 1 are the Attackers**, six men, one on each corner.

```
         A            A  attacker          On the 4x4 board the three
      .     .         D  defender          defenders stand on every OTHER
   .     .     .      K  King              neighbour of the throne, each one
A     .     .     A                        on the straight line out to a
   .     D     .                           corner.  This is the starting
.     .     .     .                        position's only asymmetry.
   .     K     .
.     D     D     .
   .     .     .
A     .     .     A
   .     .     .
      .     .
         A
```

On the **5x5** board there are six defenders — one on *every* neighbour of the
throne — and twelve attackers: one on each of the six corners and one on each
corner of the inner 4-per-side hexagon.

## Moving

One piece per turn.

- Every piece **except the 4x4 King** slides like a rook along the three hex
  lines: any number of cells, to an empty cell, without jumping.
- On the **4x4** board the **King moves exactly one cell** in any direction. On
  the **5x5** board he slides like everybody else.
- Only the King may **stop** on the throne. A man may slide **over** the empty
  throne, and the King may move back onto it.
- The corners are ordinary cells — the attackers start on them, and either side
  may move onto them.

## Capturing

Captures are **active**: only the piece that has just moved sets them off, so a
man that moves *in between* two enemies is safe. Any friendly piece — the King
included — may serve as the far side of a sandwich. There are three cases.

1. **A man on an ordinary cell** is captured when it is caught between the piece
   that just moved and another friendly piece on the **opposite** side.
2. **A man on a corner** cannot be sandwiched at all — a corner has no pair of
   opposite cells on the board. It is captured instead when both of the
   **rim cells flanking it** (the two of its three on-board neighbours that lie
   along the board's edges, 120° apart) hold enemies, one of them the piece that
   just moved. The corner's third, *inward* neighbour plays no part.
3. **The King on the throne** is harder to take: he is captured only when
   attackers stand on **three mutually non-adjacent sides** of the throne — the
   arrangement in the sheet's *The Throne* figure. Two opposite attackers, or
   three side by side, are not enough.

The King **off** the throne is an ordinary target for case 1. A King standing on
the rim with one side off the board therefore cannot be taken along that axis.

Neither an empty corner nor the empty throne is "hostile": unlike most square
tafl games, no *cell* ever assists a capture here.

## Winning

- The **Defenders win** the moment the King stands on any of the six corners.
- The **Attackers win** by capturing the King.
- A side that has **no legal move loses**.
- A position (board plus side to move) occurring for the **third time** is a
  **draw**, as is the hard ply cap described below. A decisive result always
  outranks both.

## Options

| Option | Choices | Default |
| --- | --- | --- |
| Hex grid | 4x4 (37 cells) · 5x5 (61 cells) | 4x4 |
| Moves first | Defenders · Attackers | Defenders |

The sheet recommends playing **in sets of two games, swapping sides**.

## Interpretations

The sheet is one page and leaves several things open. Every decision below is
named with the artefact that settled it.

- **"Pieces are captured by surrounding them on two sides" — which two?**
  *Opposite* sides. Settled by the sheet's King-capture figure, whose two white
  pieces are exactly opposite about the King. Two enemies 120° apart do not
  capture.
- **Corner capture — which cells?** The two **rim** neighbours. The corner
  figure shows precisely that pair with the third (inward) neighbour left empty.
  Note what that figure *cannot* do: it shows that the rim pair suffices, but it
  cannot by itself rule out "**any** two of the three". The rim-pair reading is
  the one *both* independent implementations take — AbstractPlay's
  `hexentafl.ts` and, five years earlier, the SkudPaiSho version the designer
  himself endorsed and linked (see Sources), which excludes exactly the corner
  neighbour that is adjacent to the capturing piece. It is also the reading
  under which the corner rule is the same 120° pincer as the throne rule; both
  readings are listed in `selftest.py` with the constructed positions that
  separate them.
- **"He must be surrounded on three sides" (King on the throne) — which three?**
  Three **mutually non-adjacent** sides. The sheet's *The Throne* figure draws
  exactly that arrangement, and the phrase "as shown below" makes the figure
  normative. Measured discriminating power of that figure: it kills "two
  opposite sides" and "three consecutive sides" outright, but it **cannot**
  separate "three non-adjacent sides" from the looser "any three of the six",
  because the drawn arrangement satisfies both. The tie is broken outside the
  figure, by two implementations that are independent of each other: AbstractPlay's
  `hexentafl.ts` (2024), and the SkudPaiSho version (2019) that the designer
  endorsed and linked from his own blog and BGG posts, whose source carries the
  comment *"King on Throne captured by 3 non-adjacent Attackers"* and tests the
  two alternating triples explicitly. The observable difference: under the implemented rule, **four
  attackers standing side by side around the throne do not capture the King**
  (five or six always do).
- **Is the empty throne, or an empty corner, hostile?** No. The sheet gives
  neither a capturing role, and the AbstractPlay implementation agrees.
- **May a man pass over the empty throne?** Yes; only *stopping* there is
  forbidden ("only the King may occupy the throne"). The King may re-enter it.
- **What happens to a side with no legal move?** The sheet is silent, and so is
  the AbstractPlay implementation — where a stuck side is a hard deadlock with
  no playable move and no result. We follow the rest of the tafl family in this
  library (Hnefatafl, Tablut, Brandub, Ard Ri) and make it a **loss** for the
  side that cannot move. It is genuinely reachable: about 0.7% of random 4x4
  games end this way, always with the attackers stuck.
- **Repetition.** The sheet has no repetition rule. We adopt threefold
  repetition = draw, matching the AbstractPlay implementation. It is what
  guarantees the game ends: the state space is finite, so play that never
  stopped would have to repeat some position three times.
- **Who moves first?** The sheet says "the **defenders usually move first**, but
  either works", and the 2019 announcement says flatly "the defenders move
  first". Defenders is the default; the other order is a dropdown option.

## Termination

Threefold repetition already guarantees the game ends, so the hard **ply cap**
is a backstop against a bookkeeping bug rather than a rule. It is derived from
the game's own numbers rather than pinned: every capture is irreversible, so a
game contains at most `men + 1` capture-free epochs (`men` = 9 on the 4x4 board,
18 on the 5x5), and each epoch is allowed `2 × 2 × cells` plies — 1480 plies in
total for the 4x4 board, 4636 for the 5x5.

**The cap is not outcome-load-bearing**: across 8,000 random games (6,000 on the
4x4 board, 2,000 on the 5x5) the longest ran 711 plies, under half the 4x4 cap,
and none ended by the cap at all. `selftest.py` asserts that no random game
reaches it, while separately checking that the cap *does* draw when forced onto
a position, so it is not dead code either.

For reference, random 4x4 games end 58% by the King escaping, 41% by his
capture, 0.7% by a stuck side (always the attackers) and 0.03% by repetition.

## How this differs from the library's other tafl games

| | board | King's move | hostile cells | King captured by | King escapes to |
| --- | --- | --- | --- | --- | --- |
| **heXentafl** | hexhex, 37/61 cells | 1 step (4x4) / rook (5x5) | **none** | 2 opposite, or **3 non-adjacent on the throne** | any of **6 corners** |
| Hnefatafl (Copenhagen) | 11×11 square | rook | corners + empty throne | all 4 sides | 4 corners |
| Tablut | 9×9 square | rook | empty throne | all 4 sides | any edge cell |
| Brandub | 7×7 square | rook | corners + empty throne | all 4 sides | 4 corners |
| Ard Ri | 7×7 square | rook | empty throne | all 4 sides | any edge cell |

Beyond the geometry, heXentafl is the only one of the five with **no hostile
cells at all**, the only one whose King is captured by a **two-piece** sandwich
away from his throne, and the only one with a **special corner-capture rule** —
a consequence of the hex board, where a corner cell has no pair of opposite
neighbours.

## Sources

- `nestorgames.com/rulebooks/HEXENTAFL_EN.pdf` — the publisher's rule sheet
  (2020), the authority for everything above, including the 5x5 board.
- [nxsgame.com/hexentafl.html](https://nxsgame.com/hexentafl.html) — the
  designer's page; same rules text, 4x4 only.
- [nxsgame.wordpress.com/2019/09/26/hexentafl/](https://nxsgame.wordpress.com/2019/09/26/hexentafl/)
  — the original 2019 announcement. It is 4x4 only and merely speculates that
  the game "should scale up in size easily to larger boards, although at that
  scale the king might need to be allowed to move more than one space at a
  time"; the 5x5 board with a rook-moving King is a 2020 addition made for the
  nestorgames edition.
- [BGG 321175](https://boardgamegeek.com/boardgame/321175/hexentafl), and the
  designer's own [rules thread](https://boardgamegeek.com/thread/2286206/),
  which documents how the 5x5 King's move was decided: on 2019-10-17 he posted
  that the 5x5 version was online and asked players to "help determine the
  king's move", noting "there are arguments to be made that the king should move
  2 spaces … and also that the king should just move the same as a pawn". The
  2020 rule sheet settled it on the third option — the rook move implemented
  here — so the 5x5 King is a published decision, not an inference.
- [SkudPaiSho](https://skudpaisho.com/) — the online implementation the designer
  announced and thanked the author for on his blog and on BGG; source at
  [github.com/thejambi/SkudPaiSho](https://github.com/thejambi/SkudPaiSho)
  (`js/hexentafl/HexentaflBoard.js`). Written in 2019, five years before and
  wholly independently of AbstractPlay's, it is the second implementation
  agreeing on the throne and corner readings above. Used as an adjudicator only.
