# Pachisi

**Pachisi** (पचीसी, from Hindi *paccīs* = "twenty-five") is the classic Indian
cross-and-circle race game — the ancestor of Ludo, Parcheesi and Parchís. This
package implements the **four-player** game, faithful to the rules described on
Wikipedia and Masters of Games.

## Board

The board is a **cross (cruciform)**. Each of the four arms is **three columns of
eight squares**; in the centre is a large square, the **Charkoni**, which is both
the start and the finish. Each player owns one arm. The **middle column** of an
arm is that player's **private home column** (only its owner travels it, and it
is safe). The two **outer columns** of every arm form a single shared loop around
the periphery — the **main track**, where captures happen.

## Pieces & goal

Each player has **4 pieces**, all starting in the Charkoni. The goal is to bring
**all four pieces home** (back onto the Charkoni). The first player to do so wins.

## The path

A piece travels: **OUT** down the middle column of its own arm to the arm's tip →
**ANTICLOCKWISE** around the whole periphery (the outer columns of all four arms)
→ **back UP** the middle column of its own arm to finish on the Charkoni. A full
lap is **84 squares** (this package numbers the per-piece path as 83 track
positions from the entry square to the Charkoni, plus the Charkoni itself).

## The cowrie throw

Movement is by **six cowrie shells**; the value is a function of how many land
mouth-up:

| Mouths up | Value | Grace (extra turn)? |
|-----------|-------|---------------------|
| 0 | **25** | yes |
| 1 | **10** | yes |
| 2 | 2 | no |
| 3 | 3 | no |
| 4 | 4 | no |
| 5 | 5 | no |
| 6 | **6** | yes |

Each shell is mouth-up with probability ½, so the count is *binomial(6, ½)*: the
value distribution is P(2)=15/64, P(3)=20/64, P(4)=15/64, P(5)=6/64, P(6=value 6)=1/64,
P(10)=6/64, P(25)=1/64. **25** ("pachisi") is the largest possible throw and gives
the game its name.

A **grace** throw (**6, 10 or 25**) grants an **extra turn** (the same player
throws again) and lets the player **introduce a new piece** from the Charkoni onto
the board. A piece that is in the Charkoni (a fresh piece, or one sent back) can
**only enter** the track on a grace throw.

## Castle (safe) squares

Twelve squares are marked with a cross — the **castle squares**: the **middle
square at each arm's tip**, plus the square **four in from the tip on each outer
column** of every arm (3 per arm × 4 arms). **A piece on a castle square cannot be
captured.**

## Capture

Landing **exactly** on a square of the **main track that is not a castle square**
and is occupied by one or more opponents' pieces **captures** them — they go back
to the Charkoni and must re-enter on a future grace throw. Captures never happen
on a player's own private home column or on a castle square. You may not land on
your own piece on the main track.

## Finishing

A piece reaches home (the Charkoni) only on the **exact count** — an overshoot is
not a legal move, so the piece must wait for the precise throw. (Four of the
castle squares lie exactly 25 from the Charkoni, so a returning piece can rest
there safely and finish directly on a throw of 25.)

## Player count & partnerships

Traditional Pachisi is most often played by four, frequently as **two
partnerships** (yellow + black vs red + green). This package implements the
simpler, fully general **free-for-all**: four independent seats, the first to get
all four pieces home wins. At the end the winner scores **+1** and each of the
other three scores **−1**. (Two-player and three-player Pachisi exist too;
this package fixes four seats, since the number of players is a fixed property.)

## Move & throw encoding (no chance node)

Randomness is modelled **without a chance node**: the current player's throw is
**stored in the state**. The first throw is set in `initial_state`; every
turn-ending move rolls the next mover's throw. Moves:

- **entry** of a piece from the Charkoni: a single cell, the entry square
  (one click) — only legal on a grace throw;
- a normal advance: `"fromCell>toCell"` (e.g. `"10,11>10,13"`);
- bringing a piece home: `"fromCell>home"`;
- `"pass"` when the throw allows no legal move.

A grace throw keeps the same player to move (a re-throw). If a non-grace throw
yields no legal move, the player passes and the turn moves on.

## Termination

A race always makes forward progress, but the **exact-finish** rule means a last
piece sitting near home can wait many throws for the precise count. Under purely
random play most games finish in well under a thousand plies, but the tail can
drag, so a hard **ply cap of 1500** declares the current **leader** the winner
(pieces-home, then total progress). Real play (human / MCTS) finishes far below
the cap; it only bounds pathological random playouts so the game always
terminates.

## Interpretations / decisions

- **No blockade rule.** Some Pachisi rule-sets let two of a player's own pieces on
  one square block opponents from passing. This package **omits** the blockade
  (it only forbids you from *landing* two of your own pieces on one main-track
  square); this keeps the rules clean and avoids any chance of a deadlock.
- **Free-for-all, not partnerships** (documented above).
- The **private home column is fully safe**; opponents never enter it, matching
  the physical board where the middle column belongs to its arm's owner.
