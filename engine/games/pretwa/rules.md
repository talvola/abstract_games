# Pretwa

**Pretwa** is a traditional capture game from India (associated with the Bihar
region). It belongs to the alquerque / draughts family but is played on a
circular board of concentric rings instead of a square grid. Two players,
**White** and **Black**, race to wipe out (or immobilise) the enemy.

## The board

- **Three concentric circles** (rings) plus a single **centre point**.
- **Three diameters**, equally spaced, crossing at the centre. Three diameters
  give **six radial spokes** running outward from the centre (spokes `0..5`,
  60° apart).
- Each spoke crosses each ring once, so there are **6 spokes × 3 rings = 18 ring
  points**, **plus the centre = 19 points total**.

Cells are named `"ring,spoke"`:

- the **centre** is `"0,0"`;
- ring **1** = inner, ring **2** = middle, ring **3** = outer;
- spoke `s` runs `0..5`.

### Lines and adjacency (how points connect)

Two points are **adjacent** (a single step) when they are directly joined by a
drawn line:

- **Along a spoke (radial):** centre `0,0` — `1,s` — `2,s` — `3,s`. The centre is
  joined to all six inner points.
- **Along a ring arc:** on each ring `r`, every point `r,s` joins its two
  neighbours `r,(s±1 mod 6)`. Each ring is a closed 6-cycle.

### Capture lines (straight "jump" lines)

A jump travels in a straight line over one adjacent enemy to the empty point
beyond. The straight three-in-a-row lines are:

- **Radial:** `0,0 – 1,s – 2,s` and `1,s – 2,s – 3,s` (jump along a spoke).
- **Diameter through the centre:** `1,s – 0,0 – 1,(s+3 mod 6)`. Because a
  diameter is a straight line, an inner man can jump an enemy sitting on the
  centre and land on the opposite inner point.
- **Ring arc:** `r,s – r,(s+1) – r,(s+2)` on each ring (jump along the circle).

## Setup

Each player starts with **9 men**. White takes the three adjacent spokes
`{0,1,2}` (all three rings — 9 points); Black takes the opposite three spokes
`{3,4,5}`. **The centre point starts empty.** White moves first.

## Play

On your turn you make exactly one of:

- **Step:** move one of your men along a line (a ring arc or a spoke) to an
  **adjacent empty** point.
- **Capture (jump):** jump one of your men over a **single adjacent enemy** along
  a straight line, landing on the **empty** point immediately beyond; the jumped
  man is removed. **Captures are compulsory** — if any capture is available you
  must capture (you may not make a plain step that turn). A capture **chains**:
  after landing, if the same man can capture again it must continue, and a
  multi-jump may freely switch between ring arcs and diameters. (Only single,
  contiguous enemies are jumped — you cannot leap two men at once or an empty
  gap.)

## Winning

You **win** if you:

- **reduce the opponent to three men** (three or fewer — a player who is left with
  three men or fewer has lost), or
- **capture all** of the opponent's men.

### When no move can be made (tiebreak)

If the game reaches a point where **no further move can be made** — the side to
move has no legal step or capture — the player with **more men** wins. If both
players have the **same number** of men, the game is a **draw**. (A stuck player
is therefore *not* automatically the loser: if they still hold the larger army
they win.)

### Draw (anti-loop, this implementation)

To guarantee termination the engine also stops the game if 60 plies pass with no
capture, if the same position+side-to-move repeats three times, or at a hard cap
of 400 plies. As with the no-move case, the result is then decided by **piece
count** — more men wins, **equal men is a draw**.

## Ruleset choices and ambiguities — FLAGGED for human review

Pretwa is genuinely under-documented; the two best English sources (the
[Wikipedia "Pretwa" article](https://en.wikipedia.org/wiki/Pretwa) and the
[bead.game writeup](https://www.bead.game/games/traditional/pretwa)) agree on the
core but leave details open. Choices made here:

1. **Board = 3 rings × 6 spokes + centre = 19 points.** Both sources state "three
   concentric circles" + "three diameters." Three diameters yield six radial
   spokes, which is also what makes "9 men on three adjacent spokes" come out
   exactly right (3 spokes × 3 rings = 9). bead.game's phrase "6 lines radiating"
   matches. *Chosen as the most-supported geometry.*
2. **Start = 9 men each on three adjacent spokes, centre empty.** Stated directly
   by both sources. Consequence: White's only opening options are stepping a man
   onto the empty centre (or shuffling along the shared boundary).
3. **Capture is mandatory and chains.** Stated by both sources ("a capture must
   be made"; "must continue to capture"). Implemented draughts-style.
4. **Jump through the centre is allowed along a diameter.** Sources say a capture
   runs "along a concentric circle, or along a diameter." A diameter is the
   straight line spoke-`s` → centre → spoke-`s+3`, so an inner man may jump an
   enemy on the centre to the opposite inner point. *This is the natural reading;
   flagged because no source gives an explicit centre-jump example.*
5. **No jump from the centre to a middle ring across the diameter beyond the
   centre.** The diameter line only contains the two inner points and the centre
   (the middle/outer rings are not collinear through the centre), so the only
   centre-involving jumps are `1,s – 0,0 – 1,(s+3)`. Radial jumps stay on a
   single spoke (`0,0–1,s–2,s`, `1,s–2,s–3,s`).
6. **Win threshold = opponent reduced to three men.** Both sources say reducing
   the opponent "to three" / "to just 3" loses for that player, so this
   implementation declares the win the moment the opponent's men count reaches
   **three or fewer** (annihilation included). *Matches the cited sources.*
7. **No-move result = most pieces wins (equal = draw).** Both sources say that if
   no more moves can be made the player with more pieces wins; Wikipedia adds that
   equal pieces is a draw. So a player with no legal move is **not** automatically
   the loser — the piece count decides.
8. **Draw rules (60-ply no-capture / 3-fold repetition / 400-ply cap)** are an
   engine addition for guaranteed termination, not part of the traditional game.
   When they fire the result is decided by the same piece-count tiebreak (more men
   wins, equal men draws).

If a human reviewer has access to a more authoritative source (a Bihari/Hindi
traditional-games reference), items 1 and 4 are the ones most worth checking.
