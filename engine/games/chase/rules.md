# Chase

Tom Kruszewski, TSR 1985/87. Two players, Red (moves first) and Blue.

## Board & setup

A 9×9 array of hexagons: rows **A** (bottom, Red's home) to **I** (top, Blue's
home), 9 hexes per row. The board is a **cylinder**: column 9 is adjacent to
column 1 in every row. The central hex **E5** is the **Chamber** (gold).
Pieces are dice; the shown face is the die's **speed**. Each player starts
with nine dice on their home row at speeds **1 2 3 4 5 4 3 2 1** (total 25)
and one die off the board. A player's on-board speeds must always total 25;
a player reduced to **four or fewer dice in play** (max 4×6 = 24) **loses**.

## Movement

On your turn move one die in a straight hex line **exactly its speed**.
Moving off the left/right edge **wraps around**; a die that runs into the top
or bottom edge **ricochets** like a billiard ball (never back along its path,
never along the edge). A die may never pass over any piece, of either colour,
or over the Chamber. In the UI: click the die, its first step, then the
destination (the first step picks the direction).

- **Landing on an enemy die** captures it.
- **Landing on a friendly die bumps it** one hex onward in the same billiard
  direction; if that hex holds another friendly die the bump chains on.
  A bumped die wraps and ricochets like a mover; bumping into an enemy die
  captures it and ends the move. A move whose bump chain would push any die
  **into the Chamber is illegal**.
- **Landing in the Chamber** splits the die: two dice exit onto the two hexes
  adjacent to the point of entry, the speed split as evenly as possible with
  the **larger half exiting LEFT** of the direction of travel ("Large =
  Left"); the extra die comes from off the board — the only way captured dice
  re-enter play. A speed-1 die does not split (it exits left); a player who
  already has the maximum **ten** pieces in play does not split either (the
  mover exits left at full speed). Chamber exits may land on pieces, bumping
  or capturing as usual.

## After a capture

The victim must restore their on-board total to 25 **before their move**: the
lost speed is added to their **lowest**-speed die, capped at 6, any overflow
continuing to the next-lowest, and so on. When several dice tie for lowest
**the owner chooses** which receives the points — the UI asks you to click
one of the tied dice; forced steps are applied automatically.

## Exchange

Instead of moving, two **adjacent same-colour dice** may redistribute their
combined speed between them (each die must stay 1–6, and the pair must
actually change). Click one die, then the other, then pick the second die's
new value. This costs the whole turn.

## End of the game

You **win** by reducing your opponent to four or fewer dice in play. This
implementation adds (platform termination guarantee — Chase can cycle):
a **draw** after 100 consecutive plies without a capture or Chamber move, or
at a hard 600-ply cap; and a player with no legal move loses (practically
unreachable).

## Implementation notes & sources

Rules follow the complete rules writeup in **Abstract Games magazine issue 9**
(Spring 2002), pp. 13–17/21/29, by Clark D. Rodeffer and João Neto — including
the worked movement examples and both printed problems, which this package's
selftest replays. Cross-checked against Wikipedia and Steffan O'Sullivan's
SOS' Gameviews review. Interpretations: (1) bumping a die into the Chamber is
**illegal** (explicit in AG9; O'Sullivan's summary instead allows a bumped die
to trigger a Chamber move — AG9 is followed, and the designer-co-credited 2018
nestorgames rulebook confirms it verbatim: "You cannot bump a die into the
fission chamber. A move that would cause this to happen is illegal");
(2) when a Chamber split's two exits both land on pieces, the left exit is
resolved first, then the right; (3) rows B/D/F/H are drawn half a hex to the
left (the magazine's whole-hex diagram convention for the physical board's
split half-hexes).
