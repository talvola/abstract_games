# Blooms

*Blooms* is a Go-like capture game by **Nick Bentley** (2018), winner of the
2018 Best Combinatorial Game award. It plays like Go's capturing heart on a
hex board — with the twist that **each player owns two colours of stones**,
so four colours share the board.

## Board & colours

A **hexagon of hexagons** ("hexhex") of side 4, 5 or 6 (option; default 5 =
61 cells, the designer's recommended starting size). Cells use axial `q,r`
coordinates; each cell has up to six neighbours.

- **Player 1** owns the **Red** and **Orange** stones.
- **Player 2** owns the **Blue** and **Green** stones.

## Blooms and fencing

- A **bloom** is a single stone, or an entire group of connected stones of
  the **same colour**. Your two colours never connect to each other — a red
  stone next to an orange stone is two separate blooms.
- A bloom is **fenced** when there are **no empty spaces adjacent** to any
  of its stones (its "fence" may be any mix of stones, including its owner's).

## Play

1. To start, Player 1 places **one** stone of either of her colours on any
   empty space. (The first turn of the game is exactly one stone.)
2. From then on, starting with Player 2, the players take turns. On your
   turn you **must place 1 or 2 stones** onto empty spaces. If you place 2,
   they must be **different colours** (one of each of your colours). There
   is **no passing**, and there are **no illegal placements**.
3. **After placement**, capture **all fenced enemy blooms**: remove them
   from the board and add their stones to your capture count. All enemy
   blooms fenced at that moment are removed **simultaneously** (a fenced
   enemy bloom is captured even when its fence includes another captured
   enemy bloom).
4. Your **own** blooms are never removed on your own turn. Leaving your own
   bloom fenced ("suicide") is legal — it stays on the board, and your
   opponent captures it at the end of their next turn *unless* your own
   capture step frees it first (removing a fenced enemy bloom can hand your
   fenced bloom its liberties back — the game's signature sacrifice-rescue
   tactic).

## Winning

The **first player to have captured X stones in total wins**. X is the
"Capture target" option:

- **Auto** (default): **15** on size 4, **20** on size 5 (the designer's own
  recommendation), **30** on size 6.
- Or pick X directly (15 / 20 / 25 / 30). Smaller X gives a shorter, more
  tactical game; larger X a longer, more strategic one (the designer prefers
  larger X).

There is no ko or repetition rule: because captures only ever accumulate,
the capture target itself kills cycles (the designer's stated design).

## Move encoding (as implemented)

A turn is one or two moves by the same player:

- `q,r=C` — place a stone of colour `C` (`R`ed / `O`range / `B`lue /
  `G`reen) on cell `q,r`. In the UI: click a cell, then pick the colour
  (no picker appears when only one colour is possible).
- After your first stone you may either place your **other** colour the same
  way, or play **`done`** to stop at one stone. The game's opening turn ends
  automatically after its single stone.

Captures resolve when the **turn ends** (per the official "after placement"
wording), so a bloom fenced by your first stone is not removed until you
finish your turn.

## Implementation notes

- A genuine tie cannot arise from the rules; as defensive backstops only,
  the game declares an honest **draw** at a generous hard ply cap and in the
  provably unreachable "no empty cell at the start of a turn" position.
- Resignation (mentioned in the official rules) is handled by the platform's
  resign button, not by the ruleset.

Rules source: Nick Bentley's official rules ("Blooms 2.0", nickbentley.games,
Nov 2018), cross-checked against the Abstract Games magazine treatment
(abstractgames.org/blooms.html) and the AiAi implementation report.
