# Backgammon

Backgammon is the classic race-and-block dice game. Two players, **White** and
**Black**, each have **15 checkers**. You race your checkers around a 24-point
board into your own **home quadrant**, then **bear them off**. The first player
to bear off all 15 wins.

## The board

24 narrow triangles ("points"), numbered **1–24**, plus the central **bar** and
each player's **off-tray**. The points are arranged in four quadrants of six.

- **White** moves from high-numbered points toward point 1 and bears off past
  point 1. White's home quadrant is **points 1–6**.
- **Black** moves the opposite way, from low points toward point 24, and bears
  off past point 24. Black's home quadrant is **points 19–24**.

## Starting position

The standard opening setup. For White:

- **2** checkers on point **24**
- **5** checkers on point **13**
- **3** checkers on point **8**
- **5** checkers on point **6**

Black's setup is the exact mirror (Black's point *p* = White's point *25−p*):
2 on point 1, 5 on point 12, 3 on point 17, 5 on point 19.

## Dice and movement

On your turn you roll **two dice** (1–6). Each die lets you move **one** checker
that many points toward your home.

- You may play the two dice with **two different checkers** or move **one checker
  twice** (once for each die).
- **Doubles** (e.g. 3-3) are played as **four** moves of that value.
- A checker may land on an **empty** point, a point you already hold, or a point
  with **exactly one** enemy checker (a **blot**) — which is **hit** and sent to
  the **bar**. A point with **2 or more** enemy checkers is **blocked**.

### You must use both dice if you legally can

This is a real rule, enforced here exactly: you must play **as many of your dice
as possible**. If you can play both, you must. If only one die can be played, you
must play the one that lets you use it — and if either single die works but not
both, you must play the **larger**. The engine offers only sub-moves that lie on a
turn-sequence using the **maximum** number of dice. If you can play no die at all,
your turn is **forfeited** (shown as a *pass*).

## The bar

If you have one or more checkers on the **bar**, you **must enter them all**
before making any other move. A checker enters into the **opponent's home
quadrant** on the point matching a die:

- **White** enters on point **25 − die** (die 1 → 24, … die 6 → 19).
- **Black** enters on point **die** (die 1 → 1, … die 6 → 6).

If the entry point is **blocked** (2+ enemy checkers), that die can't enter; if
**neither** die can enter, the whole turn is forfeited.

## Bearing off

Once **all 15** of your checkers are in your home quadrant, you may **bear them
off** (the only way to win):

- A die of value *d* bears off a checker from the point whose distance from the
  edge is *d* (for White, point *d*; for Black, point *25 − d*).
- You may use a die on a **lower** point only if **no checker sits on a higher**
  point (within the home quadrant).
- **Overshoot:** if the die is larger than your **highest** occupied home point,
  you may bear off a checker from that highest point (you are not forced to make a
  smaller move instead).
- (You may also choose to move a checker *within* the home quadrant rather than
  bear off, if that uses your dice — the must-use-both rule still applies.)

If a checker is **hit** while you are bearing off, it goes to the bar and you must
re-enter and bring it home before bearing off again.

## Winning

The first player to **bear off all 15 checkers wins** (+1; the loser −1).

## Simplifications (documented)

- **No doubling cube.** The cube is a stake-betting layer, not board movement, so
  it is omitted. Gammon / backgammon (double / triple) win multipliers are
  meaningless without stakes, so **a win is simply a win**.
- **Opening.** Real backgammon decides who moves first by each player rolling a
  single die (higher goes first, using both dice). Here **White (player 0) simply
  moves first** with a freshly rolled pair.

## Move encoding (for the click UI)

A move is a single **sub-move** = `from>to` using point ids:

- `"13>7"` — advance a checker from point 13 to point 7.
- `"bar>20"` — enter a checker from the bar onto point 20.
- `"4>off"` — bear off the checker on point 4.
- `"pass"` — no legal move; the turn is forfeited.

A turn's two (or four, for doubles) sub-moves are played **one at a time**, the
same player moving until the dice are spent or no remaining die can be played.

## Randomness

The dice are rolled and **stored in the game state** (there is no separate chance
step). The dice you have left to play this turn are always visible. `White`'s
first pair is rolled at the start; each completed turn rolls the next player's
pair.

## Termination

A game of backgammon always progresses toward bearing off, but repeated hitting
and re-entering can prolong it. A hard **ply cap of 4000 sub-moves** guarantees
termination; if it is ever reached (it isn't in normal play — random games run a
few hundred sub-moves), the player with the lower pip-count is declared the
winner.
