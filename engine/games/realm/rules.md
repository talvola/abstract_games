# Realm

Phil Orbanes Sr., with input from Sid Sackson (Gamut of Games, 1973). Implemented
from the designer-maintained ruleset: William L. Mikulas, *Abstract Games* #9
(Spring 2002) — Mikulas and Stanley Levin acquired the rights from Orbanes, and
their article supersedes the boxed rules (which lacked the rearrangement limit
and end-by-agreement, and used 13 Bases).

## Board and pieces

- 12×12 board = **16 Realms** of 3×3. Each Realm's middle square is its
  **Center** (shaded darker); the other eight squares are **Border Spaces**.
  You **control** a Realm if your Base sits on its Center.
- Per player: **3 Powers** (discs), **8 Enforcers** (pointed triangles) and
  **12 Bases** (squares). Bases and Enforcers enter play by being *created*
  during the game; hollow triangles are **immobilized** Enforcers.

## Setup

1. Alternating (White first), each player places 3 Bases, one per turn, each on
   the Center of a vacant Realm — never in the same **row or column of Realms**
   as a Base he placed earlier.
2. Then, alternating, each player places his 3 Powers, one at a time, on any
   Border Space of a Realm he controls — max one Power per Realm in this phase.

## Movement

- **Bases** never move.
- **Powers** move like rooks (any distance, horizontal/vertical), must stop
  before any piece, **must end in a new Realm**, may pass *through* a vacant
  Center but may never *end* on a Center.
- **Enforcers** move the same way but only in the direction they point. Before
  moving you may turn one 90° left or right (never reverse); after moving it
  points the way it moved. Immobilized Enforcers cannot move.

## A turn — one of three options

- **Dispersal**: move any number of your mobile pieces **out of one single
  Realm** to other Realms, one at a time. (A single-piece move is a 1-piece
  Dispersal.) Click moves, then **End turn**.
- **Concentration**: move **two or more** pieces, all starting outside one
  target Realm, so that all **end in that common Realm**, one at a time.
- **Rearrangement**: pick up **all** your Powers/Enforcers in one Realm and
  replace them on **different spaces** within it, reorienting Enforcers freely
  (immobile ones stay immobile; your Base stays on the Center). No Special
  Events. You may **not rearrange the same Realm three of your turns in a
  row**. In the UI, moving a piece to another square of its own Realm starts a
  Rearrangement; the turn ends when every piece is re-placed.

Special Events resolve **after each individual piece move** (this ordering is
strategically central — e.g. bring Powers in before the Enforcer strikes).

## Special Events

1. **Power creates a Base** — a Power ends in a Realm with a vacant Center and
   no enemy Powers therein: your Base appears on that Center immediately.
2. **Power creates an Enforcer** — a Power ends in a Realm you control with no
   mobile Enforcer of either side therein: a new Enforcer appears on any vacant
   Border Space of that Realm, pointing any direction you choose (skipped if
   your 8 Enforcers are all created or no space is vacant).
3. **Enforcer immobilizes** — an Enforcer stops in a Realm holding one or more
   mobile enemy Enforcers: you flip one of them (your choice). Your Enforcer is
   flipped too, unless your Powers outnumber the enemy Powers in that Realm.
4. **Enforcer captures a Base** — an Enforcer stops in a Realm containing an
   enemy Base, no mobile enemy Enforcers, and more of your Powers than enemy
   Powers: the Base is removed (kept by you for good). If your Powers exceed
   theirs by exactly 1 your Enforcer is flipped; by 2 or more it stays mobile.

## End and scoring

The game ends **immediately** when one player has created all 12 of his Bases
(the three setup Bases count), or when neither player, by agreement, can create
another Base. Most controlled Realms wins; on a tie, the greater total of
**mobile Enforcers + uncreated Enforcers** wins; still equal is a **draw**.

## Implementation notes (decisions documented)

- **End by agreement = `pass`**: passing is a whole turn; two consecutive
  passes end the game with the normal scoring. A defensive hard cap of 1000
  sub-moves also ends and scores the game the same way (unreachable in sane
  play).
- **Centers are for Bases only**: Powers/Enforcers can never end on, be created
  on, or be rearranged onto a Center (the article's movement rule, all of its
  examples, and the independent AbstractPlay implementation agree).
- **Rearrangement** re-places *each* picked-up piece on a *different* space
  ("replace them on different spaces"); pieces may take each other's old
  squares. A pass or move turn breaks a rearrangement streak.
- Each piece moves at most once per turn; pieces created mid-turn cannot move
  that turn (a Dispersal moves pieces out of the source Realm; a Concentration
  piece must have *begun* outside the target Realm).
- Events are evaluated once, when the piece stops, and are mutually exclusive
  for a given piece move (a created Base does not chain into event 2 — matches
  every annotated move of the article's sample game).

## Not implemented (article variations 1–9)

11/13-Base and 7/9-Enforcer/4-Power counts; free Base placement; movement stops
in enemy Realms; stricter Base creation; capture-and-replace Bases; second
player moves first; rearranging opponent pieces; captured-Bases tiebreak; the
Power-sacrifice remobilization. The base ruleset above is what this package
plays.
