# Fenix (Strike)

Fred Horn, conceived 1974 and registered 1975 as **Strike**; published by HUCH! in 2019 as **Fenix** (the name Alex Randolph suggested — the phoenix, because captured pieces rise from the ashes). Rules below are as implemented, from the designer's original rules in *Abstract Games* #20 (recorded by David Parlett) and the HUCH! published rulebook.

## Board and setup

- 9x9 board. **Red** (first player) starts with 28 discs filling the corner triangle nearest them (all cells with `column + row <= 6`); **Black**'s 28 discs mirror it in the opposite corner. Three empty diagonals separate the armies.
- Pieces are stacks of your own discs: **Soldier** = 1 disc, **General** = 2, **King** = 3.

## Phase 1 — preparing for battle (each player's first five turns)

Turns alternate, Red first. On each of your first five turns you place one of your **single** discs on top of another of your own pieces:

- onto an own **Soldier** → a **General** (at most 4 such creations);
- onto an own **General** → your one **King** (exactly once).

After five turns you therefore have 1 King, 3 Generals, and 19 Soldiers. If your first four turns all made Generals, your fifth turn *must* promote one to the King.

- **Original rules** (default): the moved disc must be **orthogonally adjacent** to the piece it lands on — building your army necessarily opens holes in your formation.
- **Published rules** (HUCH! variant): no adjacency requirement — stack any single disc onto any of your pieces.

## Phase 2 — battle

On your turn move one piece:

- **Soldier**: one step orthogonally to an empty square.
- **General**: slides orthogonally like a chess rook (over empty squares, to an empty square).
- **King**: one step in **any** direction (like a chess king).

### Captures — compulsory, chained, maximum value

A Soldier or King captures by jumping over an enemy piece on an adjacent square it could step to (so Soldiers jump orthogonally, Kings also diagonally), landing on the empty square immediately beyond. A General may cross any number of empty squares before the jumped enemy and land on **any** empty square beyond it on the same line.

- **If you can capture, you must**, and the capturing piece **must keep jumping** until no further capture is available.
- Each enemy piece may be jumped **only once per turn**; if the chain reaches it again it acts as a block and the turn ends there.
- Jumped pieces stay on the board as obstacles during the chain and are **removed only at the end of the turn**. (The chain may cross the mover's own vacated starting square.)
- Among all complete capture sequences (any of your pieces) you must choose one of **maximum total value**: King = 3, General = 2, Soldier = 1. Capturing a Soldier + King (value 4) in two jumps beats three Soldiers (value 3) in three jumps. Equal-value options are a free choice.
- A jumped stack is captured whole; you cannot jump your own pieces.

### Reconstitution — rising from the ashes

- **General**: if the opponent captured one or more of your Generals on their last turn, you **may** (this turn only) stack one of your Soldiers onto an orthogonally adjacent Soldier, making **one** new General. This is your whole turn. It is optional — it may be played **instead of a compulsory capture** — and if you do anything else the right lapses.
- **King**: if your King was captured on the opponent's last turn, you **must** (this turn) stack a Soldier onto an orthogonally adjacent General to rebuild the King. This is your whole turn and replaces any other move or right (including a General rebuild and any compulsory capture). **If you cannot rebuild the King, you lose.**

## Game end

- **Win** by capturing the enemy King so that it cannot be rebuilt on the very next turn.
- A player with **no legal move** loses (documented interpretation, in the draughts tradition; the rules only state the unrebuildable-King case explicitly).
- **Repetition (original rules only)**: recreating the same position (same player to move, same pending rights) for the **third** time **loses** for the player who repeats — our reading of rule 11, "you also lose if you repeat the same sequence of moves for the third time". The published HUCH! rules have no repetition rule.
- **Draw**: "if neither player can capture the other's King, the game is drawn" (both rulebooks) is implemented as a no-progress rule — 60 consecutive plies without a capture or a stack creation (plus a hard 1000-ply safety cap) end the game as a draw.

The physical game's touch-move rule does not apply digitally. The HUCH! box's smaller 8x7 junior board is not included here.
