# Nard (Long Nardy)

**Nard** (Persian نرد; also *Long Nardy* / *Long Backgammon*, Russian *Длинные
нарды*) is the Persian member of the tables/backgammon family. Two players,
**White** and **Black**, each have **15 checkers**. You race your checkers around
a 24-point board into your own **home quadrant**, then **bear them off**. The
first player to bear off all 15 wins.

Nard looks like backgammon but plays very differently — see **How Nard differs
from Backgammon** below.

## The board

24 narrow triangles ("points"), numbered **1–24**, arranged in four quadrants of
six, plus each player's **off-tray**. Both players run their checkers the **same
way** around the board (counter-clockwise), each toward their own home.

- **White** starts on the **head** at point **24** (top-right) and travels
  24 → 23 → … → 1. White's home quadrant is **points 1–6**; White bears off past
  point 1.
- **Black** starts on the **head** at point **12** (bottom-left, diagonally
  opposite White) and travels 12 → 11 → … → 1 → 24 → 23 → … → 13. Black's home
  quadrant is **points 13–18**; Black bears off past point 13.

The two heads (24 and 12) are diagonally opposite and exactly half the loop
apart.

## Starting position

**All 15** of each player's checkers begin stacked on that player's **head**:

- White: **15** on point **24**.
- Black: **15** on point **12**.

## Dice and movement

On your turn you roll **two dice** (1–6). Each die lets you move **one** checker
that many points forward along your path.

- You may play the two dice with **two different checkers** or move **one checker
  twice** (once for each die).
- **Doubles** (e.g. 3-3) are played as **four** moves of that value.
- A checker may land on an **empty** point or a point **you already hold**.

### No hitting — a lone checker holds a point

**You may NEVER land on a point that holds an opposing checker — not even a single
one.** There are no blots: one checker by itself fully controls its point. Because
nothing is ever hit, there is **no bar and no re-entry** — a checker is never sent
back. This makes Nard a pure **race-and-block** game.

### Only one checker off the head per turn

At most **one** checker may leave your **head** during a turn. The one exception:
on your **first turn** you may move **two** checkers off the head. On an opening
double **3-3, 4-4 or 6-6** you are in fact **forced** to bring two men off the
head — this happens automatically here, because a single man is blocked by the
opponent's full head (12 pips away) before all four dice can be spent, so using
both/all dice requires a second man to leave the head.

### You must use both dice if you legally can

Enforced exactly, as in backgammon: you must play **as many of your dice as
possible** (subject to the head cap and the no-hitting rule). The engine offers
only sub-moves that lie on a turn-sequence using the **maximum** number of dice.
If you can play no die at all, your turn is **forfeited** (shown as a *pass*).

## Bearing off

Once **all 15** of your checkers are in your home quadrant, you may **bear them
off** (the only way to win):

- A die of value *d* bears off a checker from the point whose distance from the
  edge is *d* (for White, point *d*; for Black, the point *d* steps from its
  edge — point 13 = 1, … point 18 = 6).
- You may use a die on a **lower** point only if **no checker sits on a higher**
  point within the home quadrant.
- **Overshoot:** if the die is larger than your **highest** occupied home point,
  you may bear off a checker from that highest point.
- You may also choose to move a checker *within* the home quadrant instead of
  bearing off, if that better uses your dice.

## Winning

The first player to **bear off all 15 checkers wins** (+1; the loser −1).

## How Nard differs from Backgammon

Nard is a genuinely distinct game, not a reskin:

1. **No hitting, no blots, no bar, no re-entry.** In backgammon a lone checker (a
   blot) can be hit and sent to the bar to re-enter; in Nard you can never land on
   an opponent's point at all, and nothing is ever sent back.
2. **All-on-the-head start.** Backgammon uses a distributed 2-5-3-5 opening
   setup; Nard stacks all 15 on a single head point.
3. **Same rotational direction.** Both Nard players move the same way around the
   loop toward diagonally-opposite homes; backgammon players move in mirrored
   directions.
4. **One-checker-off-the-head rule** (with the first-turn exception) has no
   backgammon equivalent.

## Simplifications (documented)

- **No doubling cube / no gammon scoring.** As in the backgammon package, the cube
  is a betting layer (not board movement) and is omitted; a win is simply a win.
- **The six-prime rule is omitted.** Long Nardy forbids building a full
  **six-point prime** that traps **all** of the opponent's checkers behind it (at
  least one opposing checker must be ahead of your prime). Detecting that
  correctly — which men are "ahead" of a prime, across the board wrap — is fiddly
  and it almost never binds in ordinary play, so the clean core is shipped without
  it. All other blocking is legal.

## Move encoding (for the click UI)

A move is a single **sub-move** = `from>to` using point ids:

- `"24>21"` — advance a checker from point 24 to point 21.
- `"4>off"` — bear off the checker on point 4.
- `"pass"` — no legal move; the turn is forfeited.

A turn's two (or four, for doubles) sub-moves are played **one at a time**, the
same player moving until the dice are spent or no remaining die can be played.

## Randomness

The dice are rolled and **stored in the game state** (there is no separate chance
step). The dice you have left to play this turn are always visible. White's first
pair is rolled at the start; each completed turn rolls the next player's pair.

## Termination

Nard is a monotonic race (every move advances a checker toward bearing off), so it
always terminates. A hard **ply cap of 4000 sub-moves** is a safety net for the
rare fully-jammed position; if it is ever reached, the player with the lower
pip-count is declared the winner.
