# Carnac

**Emiliano "Wentu" Venturini, 2014** (HUCH! & friends; art Andreas Resch;
2016 Mensa Recommended). 2 players, no randomness, no hidden information.

Carnac in Brittany is famous for its fields of standing stones. In this game you
raise **menhirs** (megaliths) and knock them over — but you never decide alone.
Whoever stands a stone up, the **opponent** chooses whether it stays standing or
gets pushed flat. It is an "I cut, you choose" game about *how many* groups you
own, not how big they are.

These are the rules **as implemented here**. They follow the publisher's own
rulebook — the HUCH! 2014 multilingual sheet (German pp. 1–2, English pp. 3–4;
[a mirror of the PDF](https://www.bordspellenstore.nl/wp-content/uploads/2018/02/Spelregels-Carnac.pdf))
— together with the designer's component note in the
[BGG entry](https://boardgamegeek.com/boardgame/103061/carnac). Every rule was
differentialled against the [AbstractPlay](https://play.abstractplay.com)
reference implementation, which agrees on everything **except the win
condition** (see *Interpretations* below).

## Board and pieces

One board printed with three nested playing areas; pick one before the game:

| Size | Squares | Note |
|---|---:|---|
| Small — 8×5 | 40 | |
| **Medium — 10×7** | 70 | the rulebook recommends starting here (the default) |
| Large — 14×9 | 126 | |

There are **28 megaliths in one common stock**. They do not belong to anybody:
either player may take one, and may show either colour.

A megalith is a **2×1×1 block of two cubes**, so it has two small **square ends**
and four long **rectangular faces**. All 28 are painted identically, and the
painting is the whole game:

> "All Megaliths are the same: three faces (one square and two **opposed**
> rectangular ones) of one color and the other three faces of the other color."

So one square end is Red and the other Blue, and of the four long faces the
**opposite** ones share a colour while **adjacent** ones differ.

## Play

**Red moves first.** A turn always begins with a placement:

1. **Stand a menhir up** on any empty square, taking it from the common stock.
   You choose how it stands, which is two free choices: *which colour shows on
   top*, and *which of the two long-face colours faces north–south* (the other
   then faces east–west). The move's orientation picker spells both out.
2. Your **opponent** now decides between:
   - **(i) Topple it and place** — push the stone over into one orthogonal
     direction, then stand a menhir of their own on any empty square. Their turn
     is over and *you* face the same choice about their new stone.
   - **(ii) Leave it standing** — then the turn goes **straight back to you**,
     and you stand another menhir. Declining does **not** give you a placement.

Because of (ii) one player can place several menhirs in a row, as long as the
other keeps declining.

**Toppling.** A menhir is laid flat onto the **two** squares beyond it in one of
the four orthogonal directions. Both squares must be **on the board and empty**;
never diagonally, never off the edge. The square it stood on becomes **empty
again** and may immediately receive the follow-up placement.

Pushing a stone over in some direction brings up the long face that was pointing
*away* from that direction. Since opposite long faces share a colour:

- toppling **north or south** shows the colour the placer put on the north–south
  axis, on **both** covered squares;
- toppling **east or west** shows the **other** colour, on both squares.

The colour brought up therefore depends only on the **axis** the stone falls
along — never on the colour that was standing. The top end and the north–south
pair are painted independently (all four combinations are offered), so a topple
may perfectly well bring up the *same* colour that was standing. Nor is a
*choice* guaranteed: the toppler only has one when both axes have room. Measured
over complete random games (8×5 / 10×7 / 14×9), only one axis is available in
**54.1% / 44.6% / 27.0%** of topple decisions, and in **26.5% / 22.4% / 13.4%**
of them every legal topple brings up the colour that was standing.

If the new stone **cannot be toppled at all** (no direction has two free squares),
the opponent gets no choice — but still takes their turn and stands a menhir:

> "if your opponent is not able to tilt the last placed megalith, then it is
> still his turn and he may place a new megalith onto the board."

**Nothing else ever moves.** A menhir may be toppled only in the single moment
right after it is placed; once that moment passes — toppled or not — it is fixed
for the rest of the game, and nothing is ever captured or removed.

## End of the game

The game ends **immediately** when the common stock of 28 is exhausted, or when
the board has no empty square left. (Only the 8×5 board can fill up: 28
megaliths cover at most 56 squares, more than 40 but fewer than 70.) Because the
ending is immediate, **the 28th menhir is never toppled** — its placer has the
last word.

## Scoring

Everything is read **from directly above**: only the symbol pointing upwards
counts. A standing menhir colours one square; a toppled one colours two.

A **DOLMEN** is a group of **at least three** squares of one colour connected
**orthogonally**. Diagonal contact does *not* connect — the rulebook prints a
figure of three diagonally-touching symbols captioned "Kein Dolmen".

**The player with the MOST dolmens wins.** Equal counts are broken by the
largest dolmen, then the next largest, and so on. If every dolmen matches, the
game is an honest **draw**.

Count comes first, and that is the point of the game:

> "In CARNAC the number of dolmens is decisive, and not necessarily their size.
> Winning points already scored are minimized by dolmens of the same colour
> growing together."

Two separate groups of three are worth **more** than one group of six, so you
want your own colour scattered and your opponent's joined up. That is why
standing a stone with the *opponent's* colour up, or toppling one onto their
colour, is often the strong move.

### The rulebook's worked example

Page 3 prints a finished large-board game with the tally spelled out: both
players built **5 dolmens**; the largest white and the largest red dolmen are
both **8** symbols; the second largest are **6** (white) and **5** (red); *"Weiß
gewinnt das Spiel"*. That exact position is transcribed in this package's
`selftest.py`, which reproduces all six of those printed numbers — red
(8,5,4,4,4) against white (8,6,4,3,3) — and the winner.

## Notation and the display

Squares are `col,row` internally and shown as algebraic `a1`…`n9` in the move
log (file letter left to right, rank number bottom to top). A placement is a
single click plus an orientation pick; a topple is *click the standing stone,
then click the square it should fall towards*; declining is the button below the
board.

Because scoring is a bird's-eye reading, **every occupied square is drawn as a
solid block of the colour it shows** — so a dolmen is literally a block of one
colour on screen. Over the top, a **dark bar** joins the two halves of each
toppled menhir and a **small dark diamond** marks each one still standing; the
stone awaiting the topple decision wears a **gold diamond**.

Seat 1 is **Red** and seat 2 is **Blue**. The physical game is red versus white;
blue is simply this platform's second seat colour.

## Why the game always ends

Every placement spends one megalith from a stock of 28, and every decision ply
is immediately followed by a placement (from the decision phase the only moves
are a topple or a decline, and both lead straight to a placement). The
first move of the game is a placement, so there is always one fewer decision
than placement: a game is at most **2 × 28 − 1 = 55 plies**, whatever the
players do. No repetition rule, no ply cap and no move limit is needed, and none
is used — nothing in this implementation caps the game or can decide a result.

## Interpretations and departures

* **The win condition (a correction to the reference implementation).** The
  rulebook, the designer's BGG summary and the *abstractgames.org* review all say
  the same thing: most dolmens first, largest dolmen only as a tie-break.
  AbstractPlay's `carnac.ts` instead compares the two sorted **size** lists
  directly, ignoring the count, so a player with one huge dolmen beats a player
  with three small ones. That disagrees with the published rule on **19.8% /
  30.8% / 42.5%** of random games (14×9 / 10×7 / 8×5), and it inverts the
  rulebook's own strategy advice, under which merging your dolmens *hurts*. This
  package follows the rulebook. It is the only rule on which our differential and
  the oracle disagree; the dolmen **sizes** matched on every one of the 85 games
  compared.
* **A full tie is a draw.** The sheet's tie-break chain (count, then each
  successive size) simply runs out if the two lists are identical, and says
  nothing further, so an all-equal game is scored 0–0. It is not a dead branch:
  ties occur in about 0.2% of random 10×7 games and 1.5% at 14×9.
* **The orientation choice.** The sheet never says the placer picks the stone's
  rotation, because physically they cannot avoid it — a block has to be put down
  facing *some* way. The four orientations offered here are exactly the four
  distinguishable ways to stand the published piece up, and match the reference
  implementation's move count (280 on 10×7).
* **Who starts.** The rulebook says the eldest player begins; here seat 1 (Red)
  always does.
* **Two clicks, one turn.** Toppling and the placement that follows it are one
  turn in the rulebook and two moves here, so the move log records the topple and
  the placement separately. Nothing about the rules changes: after a topple the
  same player must place, and no other move is offered.
* **Standing versus lying is only ever cosmetic after the fact.** Nothing but
  the just-placed stone can be toppled, so once a decision has passed, a standing
  menhir and a toppled one differ only in which squares they colour. The display
  still distinguishes them, but no rule reads that distinction.
* **No bot evaluation function is shipped**, deliberately. A game lasts at most
  55 plies and the generic MCTS bot rolls out 50, so a rollout reaches a real
  terminal — and is scored by the real result — on 100% / 98.4% / 92.5% of plies
  over complete games (8×5 / 10×7 / 14×9). A hand-written evaluation could only
  ever replace the true result, never improve on it.
