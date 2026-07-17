# Puluc (Bul / Boolik)

The Maya / Q'eqchi' running-fight game of Guatemala and Belize. Traditionally
played on the ground: a row of corn kernels marks out the track, and the gaps
between them are the playing spaces. Both players run their pieces along the
**same** track in **opposite** directions.

## Equipment

- A track of **9 spaces** (ten corn kernels; options for 14 or 21 spaces —
  boards of many lengths are attested).
- **5 pieces** per player, starting in the player's **hand** (home base) at
  their own end of the track. Red's home is the left end; Red runs left→right.
  Blue's home is the right end; Blue runs right→left.
- **Four corn-kernel dice**, blackened on one side. The throw value is the
  number of black faces up: **1, 2, 3 or 4 — except that 0 black (all plain)
  counts 5**.

## Play

Players alternate turns. Each turn: the dice are thrown (the roll is shown in
the caption), and the player makes **one move** with the full value — enter a
piece from hand, or move one piece/pile already on the track. If no move is
possible, the turn is forfeited (**pass**).

- **Entering**: a throw of *k* puts a piece from your hand onto the *k*-th
  space from your own end (click your home cell, then the landing space).
- **Moving**: a free piece moves *k* spaces toward the enemy end.
- You may never end a move on a space occupied by your **own** piece or a pile
  you control. Pieces pass over occupied spaces freely — only the landing
  space matters.
- A free piece that moves **beyond the far end** of the track (its run
  complete, no capture) **returns to its owner's hand** and may re-enter
  later.

## Capture and carry

- Landing **exactly** on a space holding an enemy piece — or an enemy-
  controlled pile — **captures the whole pile**: it is placed **beneath** your
  piece, and your piece immediately **reverses direction**, dragging its
  prisoners back toward your own end (this also applies when entering from
  hand).
- A carrier moves by the throw like any piece. When it moves **past your own
  end**, off the board: every **enemy piece in the pile is killed** (removed
  from the game for good), every **friendly piece — the carrier and any of
  your own pieces that were prisoners in the pile — returns to your hand**.
- **Recapture**: an enemy landing exactly on your carrier captures the entire
  pile in turn — it goes beneath the new top piece, control flips, and the
  pile heads toward the *new* owner's end. Your former prisoners are freed in
  the sense that they now ride home in your pile and return to your hand when
  it bears off. Piles may change hands any number of times.

## Winning

Kill **all five** enemy pieces and you win. A hard cap of 3000 plies declares
an honest **draw** (this is a safety backstop; real games end long before).

## Sources & interpretations

Sources consulted: Wikipedia "Bul (game)" (following **Lieve Verbeeck 1998**,
*Bul: a Patolli game in Maya lowland*, and Culin 1907); the **Ludii** Puluc
entry and its `Puluc.lud` implementation (source: **Sapper 1906**, *Spiele der
Kekchí-Indianer*, p. 284); **R.C. Bell**, *Board and Table Games from Many
Civilizations* (pp. 89-90, via secondary write-ups); boardandpieces
(Bell/Parlett-based); playonlinedicegames.com/puluc; BGG entry 13745.
Contested points and what this package does:

1. **Dice values.** Verbeeck/Wikipedia and most modern write-ups: black faces
   up = 1..4, all-plain = 5 (*implemented*). Ludii reads Sapper 1906 as "two
   alike = 2, three alike = 3, four black = 4, four plain = 5" (so ONE black
   would count 3). We follow the Verbeeck majority mapping.
2. **Turn structure.** Verbeeck/Wikipedia and playonlinedicegames: one throw,
   one move per turn (*implemented*). Bell/Parlett (boardandpieces): two
   throws summed, moving a single counter; Ludii/Sapper: two separate
   throw-moves per turn. Not implemented.
3. **Track length.** Sapper/Bell/Ludii: 9 spaces (ten kernels) — the
   *default*. Fifteen-kernel boards (14 spaces) are common in modern sets, and
   Bell mentions a larger board of 21 spaces — both offered as options.
   Verbeeck records boards of up to 25 dividing rods.
4. **Capture direction.** All sources agree the capturer reverses and drags
   the prisoners toward its own end, killing them when it passes off the
   board; the carrier returns to hand (*implemented*). No exact throw is
   needed to bear off (Ludii: any move past the end exits).
5. **A free piece completing the track** returns to its owner's hand for
   re-entry (Bell/boardandpieces, playonlinedicegames — *implemented*).
   Ludii/Sapper instead loop the piece back to its own start seamlessly.
6. **Friendly prisoners on recapture** ride home in the recaptured pile and
   return to hand when it bears off (*implemented*). Wikipedia words this as
   "liberated" on reaching home; playonlinedicegames frees them at the moment
   of recapture as travelling "companions" — the outcomes coincide, since
   either way they reach the hand only via the pile's bear-off.
7. **Own pieces never share a space** (boardandpieces: "no two friendly
   counters share a position") — a move may not land on an own-controlled
   space (*implemented*; other sources are silent).
8. **Piece count**: 5 per player (Sapper/Ludii/Bell/playonlinedicegames).
   Verbeeck describes team play with one stone per team member; not
   implemented (this is the 2-player game).
9. **A carrier landing exactly on an enemy piece (or pile) on its way home
   captures it too** — it joins the prisoners beneath and the pile keeps
   heading home (*implemented*). The written sources are silent on this case
   (they only describe a piece being captured "on the way" in the recapture
   sense); we apply the general landing-captures rule, which also covers
   capture on entry from hand. The alternative (carrier and enemy sharing a
   space without capture, as Ludii's code would allow) has no textual support
   and is physically odd on a corn-gap track.
