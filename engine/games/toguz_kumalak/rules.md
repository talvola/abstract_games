# Toguz Kumalak

**Toguz Kumalak** (Kazakh, "nine pebbles"; Kyrgyz **toguz korgool**) is a
two-player sowing mancala from Central Asia. This package implements the rules
*as described on Wikipedia ("Toguz korgool")*, with the few mechanical choices
noted below.

## Board

- Two rows of **nine pits** (*otau*) — eighteen pits in all.
- Each player has a **kazan** (cauldron / store) that holds captured balls. The
  kazans are **not** board pits and are never sown into directly; balls only
  enter them via capture or a tuzdik.
- **162 balls** total, **9 in every pit** at the start; both kazans start empty.
- Player 0 owns the **bottom** row and the bottom kazan; Player 1 owns the
  **top** row and the top kazan.

In this package pits are addressed `col,row` on a 9×2 grid (`row 0` = player 0's
nine pits, `row 1` = player 1's nine pits). The two kazans live in the game
state, not as board cells.

## A move

On your turn you choose **one of your own non-empty pits** (you may not start a
move from a pit that is a tuzdik) and **sow** its balls counterclockwise.

The counterclockwise loop runs left-to-right along the bottom row
(cols 0→8), crosses to the top row, continues right-to-left (cols 8→0), then
wraps around.

### Sowing — the leave-one-behind rule

- If the chosen pit holds **exactly one** ball, pick that ball up and drop it in
  the **next** pit (the source pit ends empty).
- If the chosen pit holds **more than one** ball, **leave one ball behind** in
  the source pit and sow the rest one per consecutive pit. (Equivalently, and
  the way the rule is classically phrased: lift all the balls and drop the
  **first** one back into the just-emptied source pit, then continue onward.)

## Capture

If the **last** sown ball lands in a pit on the **opponent's** side and that
pit's **resulting count is even**, you **capture all** of that pit's balls into
your kazan (the pit is emptied). Landing in your own pit, or making an
opponent's pit odd, captures nothing. Only the single pit where the last ball
lands is checked (no back-propagating chain).

## Tuzdik — the signature rule

If the **last** sown ball lands in an **opponent** pit bringing its count to
**exactly three**, that pit becomes **your tuzdik** (a "sacred hole", marked as
yours), provided **all three** of these restrictions hold:

1. **One per player** — you do not already own a tuzdik (each player may create
   at most one in the whole game).
2. **Not the opponent's ninth pit** — the opponent's last (ninth) pit can never
   become a tuzdik.
3. **Not symmetric** — it is not the mirror-symmetric pit of the opponent's
   existing tuzdik (the same position counted from each player's own first
   pit, i.e. the same column on the opposite row).

When a tuzdik is created, the three balls then in it are immediately moved to
your kazan. From then on, **every ball ever sown into a tuzdik is immediately
transferred to its owner's kazan** — the tuzdik never accumulates balls and is
never sown from. (Because a tuzdik never holds balls, it is never the "last
pit" that triggers a capture or another tuzdik.)

If the three-ball pit fails any restriction, no tuzdik is made; if the resulting
count of three is *not* even it is also not a capture, so the balls simply stay.

## Winning

There are 162 balls, so a player with **more than 81** balls in their kazan can
never be overtaken. The first player to reach **more than 81 (i.e. ≥ 82)** wins
immediately.

The game also ends when the player to move has no balls to sow (their side is
empty of sowable balls). When the game ends this way, **every loose ball still on
the board is won by the player on whose side it sits**: each player adds the balls
remaining in **their own row of pits** to their own kazan before the final count
(tuzdik holes never hold balls, so they add nothing). The player with **more
balls** after this sweep wins; if both finish on **exactly 81**, it is a **draw**.

### Termination safeguard

Toguz Kumalak terminates naturally (every move banks at least the
leave-one-behind progress or empties a side), but as a defensive measure this
implementation also ends the game at a hard ply cap of 2000 plies, applying the
same end-game sweep to decide the result.

## Implementation choices

- **Symmetry definition** for restriction (3): two pits are symmetric when they
  occupy the same position counting from each player's own first pit — in this
  coordinate layout that is the **same column on the opposite row**.
- The last (ninth) pit that may never become a tuzdik is, in this layout,
  `(8,0)` for player 0 and `(0,1)` for player 1 (each side's last pit in its own
  sowing direction).
- End-of-game sweep: when a side is emptied (or the ply cap triggers), the loose
  balls left on the board are swept to their own side — each player adds the balls
  remaining in their own pit-row to their own kazan — and the winner is whoever
  then has more. Ball count is conserved (the two swept kazans total 162).
