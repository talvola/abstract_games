# Entrapment

Rich Gowell, 1999. Two players (Player 1 moves first). Rules as implemented —
from the official rules at Boardspace.net, ambiguities resolved against the
Boardspace reference implementation.

## Equipment

- A **7x7** board (option: the designer-recommended tighter **6x7**).
- Each player: **3 roamers** (option: 4) and **25 barriers**.
- Barriers sit in the **grooves between two adjacent squares**, first *resting*
  (flat, in your colour), later possibly *standing* (upright — drawn as a
  gold groove).

## Setup

Players alternate placing one roamer at a time on any empty square (Player 1
first) until all roamers are placed.

## Play

Right after setup, Player 1 takes a **single action**: move a roamer *or*
place a barrier. Every turn after that is **two actions**:

1. **First action — move a roamer** (mandatory).
2. **Second action — move a roamer or place a barrier.** Once your 25
   barriers are all on the board, you may instead **move one of your
   *resting* barriers** to any empty groove.

**Roamer movement.** A roamer moves 1 or 2 squares in a straight orthogonal
line and must land on an empty square. Per move it may jump over **at most
one** of: a friendly roamer, or a friendly *resting* barrier. Enemy roamers,
enemy barriers and all *standing* barriers are impassable. **Every resting
barrier you jump flips to standing** — from then on it is immovable and
impassable to both players. (There is no separate voluntary "flip" action;
barriers only stand up by being jumped.)

## Entrapment and capture

- A roamer with all four sides blocked (board edge, **any** barrier in the
  groove, or **any** roamer on the adjacent square) is **trapped**
  (highlighted in gold).
- A trapped roamer that **cannot escape** — it has no legal move, and no
  friendly roamer adjacent across an empty groove can move — is **captured
  immediately**. This is checked after every action, so you can also trap
  (or suicide) your own roamer.
- If a player already has a trapped roamer, any further roamer of theirs
  that becomes trapped is **captured immediately** — a player can never keep
  two trapped roamers. If one action traps **two** roamers of one player at
  once, the **moving player chooses** which one is captured (click it).
- **Forced escape:** if you have a trapped roamer, your first action must
  try to free it — move the trapped roamer itself, or a friendly roamer that
  is adjacent to it across an empty groove. If it is still trapped after the
  first action, the second action is restricted the same way (or you may
  place/relocate a barrier).

## End of the game

- **Capture all enemy roamers to win.** If one action wipes out *both*
  sides' last roamers at once, the player who did **not** move wins
  (Boardspace rule).
- Engine backstops (honest draws): 80 consecutive actions with no barrier
  placement, flip or capture, or 1200 total actions, end the game in a draw.
  A `pass` button appears only in the theoretical corner where a mandated
  action has no legal move.

## Interface notes

- Place a barrier by clicking your **B** chip in the reserve tray, then a
  highlighted groove. Roamer moves and barrier relocations are click-source,
  click-destination.
- Resting barriers show in their owner's colour; standing barriers are gold.
