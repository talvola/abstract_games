# Smess — The Ninny's Chess

**Reuben Klamer & Perry Grant, Parker Brothers, 1970.** Also published as
**Take the Brain** (British name; identical rules) and re-skinned in 1979 with a
medieval look as **All the King's Men**. Smess is a *Recognized Chess Variant*
at chessvariants.com.

Smess is chess "for ninnies": every square of the board is printed with one or
more **arrows**, and a piece may leave a square **only** in a direction one of
that square's arrows points. It is always the arrows on the square a piece
*starts from* that decide where it may go.

## Board & setup

A **7 columns (a–g) × 8 rows (1–8)** board. Each player has **12 pieces**: one
**Brain**, four **Numskulls**, and seven **Ninnies**.

- **Red (seat 0)** — Ninnies a2–g2; Numskulls b1, c1, e1, f1; Brain d1.
- **Blue (seat 1)** — Ninnies a7–g7; Numskulls b8, c8, e8, f8; Brain d8.

(The squares a1, g1, a8, g8 start empty.) Red moves first.

The arrows are **absolute board directions** — the same arrows apply to both
players, so you may even move *backward* if an arrow points that way. In this
package the pieces are labelled **B** (Brain), **S** (numsku**ll**), **N**
(Ninny); the arrows are drawn as small chevrons on every square.

## The pieces

- **Ninny (N)** — moves exactly **one** square, in any direction shown by an
  arrow on the square it is standing on.
- **Numskull (S)** — *rides* **any number** of squares in a straight line, in
  any direction shown by an arrow on the square it starts from. It obeys only
  the arrows on that starting square (not the squares it passes over), and it
  **may not jump** — it stops at the first piece, capturing it if it is an enemy.
  The Numskull is the strong piece.
- **Brain (B)** — moves exactly **one** square, like a Ninny. **If your Brain is
  captured, you lose.**

## Moving & capturing

Players alternate, moving exactly one piece per turn. You may **never** move onto
or over a square occupied by one of your **own** pieces. You **capture** an
enemy piece by moving onto its square (displacement, as in chess); any piece can
capture any enemy piece, and captured pieces are removed for the rest of the
game.

## Winning

**The object is to capture your opponent's Brain.** There is **no check or
checkmate** — you win the instant you actually capture the enemy Brain, and a
player is under no obligation to protect their Brain from capture.

## Promotion

When a **Ninny moves onto one of the opponent's Numskull starting squares**
(for Red: b8, c8, e8, f8; for Blue: b1, c1, e1, f1) it is **promoted to a
Numskull**. This follows the official Parker Brothers rulebook.

*Interpretation note.* The official rule reads "replaced with a Numskull which
had previously been captured"; the game equipment reuses a captured piece, but
this package treats promotion as automatic and unrestricted (no captured-piece
requirement), matching Fergus Duniho's reference implementation. Fergus's
implementation additionally allows promotion on **any** Numskull starting square
(including a player's own); here we follow the *printed rulebook*, which promotes
only on the **opponent's** Numskull squares.

## Draws

The official rulebook states: *"If the only two pieces left in the game are the
two Brains, neither player can win and the game is a tie."* This package ends the
game as a **draw** the moment only the two Brains remain.

Two additional practical draw valves guarantee the game always ends (arrow moves
are largely reversible): a draw after **60 plies** with no capture and no
promotion, and a hard cap at **400 plies**.

*Deadlock.* If the player to move somehow had **no legal move**, the game would
be ruled a **draw** (a deadlock, not a loss — the sole win is Brain capture).
This is a defensive rule only: because every square on the Smess board is
"attacked" by some neighbouring arrow and each side has at most 12 pieces, a true
stalemate cannot occur in legal play.

## The arrow map

The per-square arrow layout **is** the game. It is transcribed here from the
official Smess board image (chessvariants.com, rendered from Fergus Duniho's
implementation) and cross-checked against the official Parker Brothers rulebook
and the photographed board. The layout is exactly **180° point-symmetric** — the
package's selftest asserts this property across all 56 squares, and it was used
to independently verify the transcription (the two halves were read separately
and agree). The four central squares (d4, d5) carry all eight arrows; the single
"pointing-hand" squares (a1, g8, b5, f4) carry exactly one direction.

## Take the Brain / All the King's Men — identity & errata

Smess, **Take the Brain** (the British release) and **All the King's Men**
(the 1979 adult re-skin with Knights, Archers and a King) are the **same
game** — identical board, arrows and rules (Kerry Handscomb, *Abstract Games*
issue 9, Spring 2002, pp. 8–9).

*Arrow correction (2026-07-18).* An earlier transcription of this package
misread two squares as diagonals: b2 as {N, SE} and f7 as {NW, S}. Both are in
fact **right-angle elbows** — **b2 = {N, E}** and **f7 = {W, S}** — confirmed
independently from two primary sources: *Abstract Games* #9 Diagram 1 rendered
at 600/1200 dpi (the elbow squares have purely vertical/horizontal shafts,
unlike the genuinely diagonal arrows on b7/f2), and chessvariants.com's Smess
board graphic (`play/pbm/backgrounds/smess73.png`), which draws the same
elbows. The two misreads were 180°-symmetric partners, so the board's
point-symmetry check alone could not catch them.

*AG#9 puzzle errata.* The magazine's Brain-vs-Brain puzzle answer (p. 29)
prints **47** non-trivial winning positions. A full 3,080-state retrograde
solve over the corrected board (pinned in this package's selftest) shows the
true answer is **48**: the printed list **misses b1b2** (Brain on b2 forces
the win in 9 plies — a line that requires b2's E arrow: 1.b2c2 b1a1 2.c2b2
a1a2 3.b2b3 a2a1 4.b3a3 a1a2 5.a3xa2) **and b1d2** (also 9 plies), and
**wrongly includes f4e3**, which has an immediate capture (e3's NE arrow) and
is therefore trivial by the puzzle's own definition. The selftest also replays
the magazine's complete Favel–Handscomb sample game (89 plies) through the
engine.

## Sources

- Official Parker Brothers *Smess* rulebook (Hasbro PDF).
- chessvariants.com — *Smess* (`other.dir/smess.html`), with the board diagram
  and Game Courier preset by Fergus Duniho.
- BoardGameGeek thing **1289** ("All the King's Men", 1970), which lists "Smess:
  The Ninny's Chess" and "Take the Brain" as alternate names.
- Kerry Handscomb, "Take the Brain: A Silly Game with Serious Strategy",
  *Abstract Games* issue 9 (Spring 2002), pp. 8–9 — board diagram, sample game
  and the Brain-vs-Brain puzzle (solution p. 29).
