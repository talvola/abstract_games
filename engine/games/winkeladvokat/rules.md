# Winkeladvokat

*Roland Siegers, Schmidt Spiele 1986. Also published as **L'avocat du diable**
(Devil's Advocate); reworked by Siegers on a hex board as **Cabale**
(Goldsieber, 1999).* Two players.

Your client is facing a life sentence. Every clever **detour** through the legal
code is another argument for the defence — and the better your arguments, the
lighter the sentence. Most points wins.

## The board

An 8x8 board printed with four concentric rings of point values:

- the outer ring is worth **2**,
- the next ring **4**,
- the next **8**,
- the central four squares **16**.

The four corners are blank colour-coded **start squares** and are worth
**nothing**. At two players the blue and red corners are used; they are
diagonally opposite. Here **Red** starts on **a1** and **Blue** on **h8**
(files a-h left to right, ranks 1-8 bottom to top). The board is symmetric, so
which of the two diagonally opposite corners each player takes makes no
difference.

Each player has one **Avocat** (shown as a large **A**) and **25 Article §
tokens** (plain discs in their colour).

## A turn

On your turn you do **one** of two things.

### 1. Move your Avocat — the DETOUR (Winkelzug)

Move your Avocat like a rook: **one or more empty squares** horizontally or
vertically, then **turn 90 degrees** and continue **one or more empty squares**
in the perpendicular direction. Every square it passes over, the square it turns
on and the square it stops on must be **empty** — Articles of either colour and
the other Avocat all block it.

The square where it turns is the **detour square** (Winkelfeld). You **must**
place one of your Article tokens there. The number printed on that square counts
towards your score at the end of the game.

Click your Avocat, then the turn square, then the destination.

### 2. Capture — instead of moving your Avocat

One of your Articles may **jump an orthogonally adjacent enemy Article** into
the empty square directly beyond it, exactly as in draughts. The jumped Article
is removed from the board and kept by you. Jumps are **horizontal or vertical
only — never diagonal**.

**Chain jumps are allowed but never compulsory**, and there is no
"must-take-the-most" rule. After a jump, if the same Article can jump again you
may either jump on or press **Stop capturing** to end your turn. Nothing forces
you to capture at all.

Avocats can neither capture nor be captured, and they block both the jumped
square and the landing square.

## End of the game

The game ends **the moment the player to move cannot move their Avocat** — it is
hemmed in by Articles, by the edge of the board, or by both. (It does not have
to be surrounded on all four sides: an Avocat with a free neighbour but no legal
90-degree continuation is stuck just the same.) Being immobilised is not a loss
in itself; the scores decide.

Each player scores:

- the numbers printed on the squares occupied by their own Article tokens, plus
- **1 point for every enemy Article they captured**.

The higher total wins. **An equal total is a genuine draw.**

## Implementation notes / interpretations

The German Schmidt Spiele instruction sheet is the source of truth here; the
French Schmidt/jeuxsoc translation agrees with it on every point. Where the
sheet is silent, this package makes the following choices — all documented so a
future reading can be checked against them.

- **Leg lengths.** The sheet says "eine beliebige Anzahl an unbesetzten Feldern"
  for both legs, and the French translation renders the second leg as "d'une ou
  plusieurs cases". Both legs are implemented as **at least one square**, which
  is what figure Abb. 1 draws (2 + 2), what *Abstract Games* #23 states ("one
  Rook move followed by another Rook move perpendicular to the first"), and what
  Don Kirkby's derived *Domino Runners* spells out ("Each part must move at
  least one space"). A straight rook move with no turn is therefore not a legal
  Avocat move.
- **Jump directions.** The rules only say "wie im Damespiel" (as in draughts).
  Figure Abb. 2 shows a **vertical** jump on a board with no chequered pattern;
  the printed board itself is a grid of **octagons** separated by small diamonds
  at the crossings, so two squares only ever share an edge orthogonally (there
  is no diagonal contact); and *Domino Runners* states "You may not jump
  diagonally". Jumps are orthogonal only.
- **Capture is a whole turn.** "Ein Spieler kann *anstelle der Bewegung seines
  Advokatensteins* auch gegnerische Paragraphensteine schlagen" — instead of
  moving the Avocat (French: "Au lieu de déplacer son avocat, un joueur peut
  prendre un pion article à son tour de jouer"). This is the one genuine
  ruleset call in the package, and there **is** evidence the other way: the
  numbered caption of Abb. 2 / Figure 2 in *both* publisher sheets runs
  "① the Avocat makes a detour → ② an Article is placed on the detour square →
  ③ that Article has jumped the opposing Article ④", which reads as one turn,
  and the *Abstract Games* #23 cover note ("If this piece can jump … then the
  player may do so") and Don Kirkby's derived *Domino Runners* both chain them
  explicitly. The figure is a **composite illustration of both rules on one
  diagram** — it never says "in the same turn" — whereas the body text of the
  rules is unambiguous, so the body text wins and a capture is a turn of its
  own. Any of your Articles may capture, not just a freshly placed one.
- **Jumped Articles are removed immediately**, so within one chain the same
  Article cannot be jumped twice and a vacated square can be landed on again.
- **The end condition is evaluated for the player to move**, at the start of
  their turn. (The sheet's "sobald *ein* Spieler nicht mehr ... ziehen kann"
  could also be read as ending the game the instant *any* Avocat is trapped;
  in a two-player game the two readings differ only when a player traps their
  own Avocat, which then gives the opponent one extra turn.)
- **Running out of Article tokens ends the game too.** Placement on the detour
  square is mandatory ("*muß* der Spieler einen seiner Paragraphensteine im
  Winkelfeld plazieren"), so a player with an empty supply cannot complete a
  detour and therefore cannot move their Avocat. In practice games finish long
  before 25 detours each.
- **The blank corners score 0.** Nothing forbids turning on a vacated corner
  square, so it is allowed and simply banks no points.
- **Termination is proved, not capped.** Every turn either spends one Article
  from a hand (at most 50 in a game) or removes an Article that some detour put
  on the board (at most 50), so a game cannot exceed a couple of hundred plies.
  A hard cap of 400 plies exists purely as an unreachable safety net; if it ever
  fired, the position would simply be scored as normal.

## Sources

- **Two to four players.** The published game is for 2-4; this package
  implements the **two-player** game the German sheet sets up explicitly ("Bei
  2 Spielern werden das blaue und das rote Ausgangsfeld benutzt; jeder Spieler
  erhält 25 Paragraphensteine"). The 3-4 player game uses the other two corners
  and 15 Articles each.
- **German rules** — Schmidt Spiele, *WINKELADVOKAT* instruction sheet (3 pp),
  [spielanleitung.com](http://www.spielanleitung.com/download.php4?id=2051).
- **French rules** — *Winkeladvokat - L'avocat du diable*, Schmidt's French
  translation, scanned by François Haffner, [jeuxsoc](http://jeuxsoc.free.fr).
- **The printed board values** are not in either rules sheet. They were
  transcribed from photographs of three different physical copies: BoardGameGeek
  images *pic4768412* and *pic431977* in the
  [Winkeladvokat gallery](https://boardgamegeek.com/images/boardgame/2473), and
  the front-cover photograph of *Abstract Games* issue 23 (Spring 2022). All
  three agree on 2 / 4 / 8 / 16. (Several German review sites describe the board
  as carrying "2, 4, 8, 16 und 32"; no photograph shows a 32.)
- **Corroboration** — *Abstract Games* #23, front-cover note (p. 1) and Don
  Kirkby's *Domino Runners* (pp. 46-47), a game derived from Winkeladvokat and
  Cabale.
