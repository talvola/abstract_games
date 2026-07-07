# Volo

**Designer:** Dieter Stein (2010) · Published by nestorgames · [Official rules](https://spielstein.com/games/volo/rules)

*volo* — Latin "I fly", Italian "flight". A two-player game inspired by the beauty of
flocking birds. This page describes the rules **as implemented** in this package.

## Board — the "sky"

A hexagonal grid of *intersection points* (a "hexhex"), with the **six corners and the
centre point removed**:

- **Standard:** edge 7 → **120 points**.
- **Small:** edge 6 → **84 points** (select via the *Board size* option).

Two points are **adjacent** if they are neighbours on the hex grid (6 directions).

## Setup

Each player has a supply of birds of one colour (Orange = first player, Blue = second).
Each starts with **3 birds** already on the board, one in each of their three **nests** —
the six edge-midpoints of the rim, coloured **alternately** around the edge. On the small
board the nests are inset one step toward the centre.

## Objective

Gather **all** of your on-board birds into **one contiguous flock** (a single group of
birds connected by adjacency). Any flock size wins.

## Your turn — choose one

### Add a bird
Place one bird from your supply on a vacant point that is **both**:

1. **not adjacent** to any friendly bird already on the board, and
2. **not inside a region controlled by the opponent** — a vacant region has *no open
   path* to any friendly bird. An **open path** is a chain of points that are vacant or
   occupied only by *your* birds. Equivalently: the empty area you place into must be
   bordered by at least one of your own birds.

### Let the birds fly
Move **a single bird**, or **an entire flock that forms a straight line**, rigidly in a
**straight line** — any of the 6 directions, any distance — over vacant points. A flight:

- **may pass over friendly birds**, but an **enemy bird blocks** it (you cannot pass or
  land on an enemy, and cannot land on any occupied point);
- **must end adjacent to another friendly bird**, enlarging a flock;
- may **never split** an existing flock.

A single bird that belongs to a larger flock may also fly ("rearrange") provided the rest
of its flock stays joined *and* the move attaches it to a further flock (a net
enlargement). Non-straight flocks can only move one bird at a time in this way; a flock
that is itself a straight line may also fly as a whole unit.

## Regions

After your move, if the **opponent's** birds are split into two or more **regions** (no
open path between them), all but one region is **removed** and returned to the owner's
supply — *the mover chooses which region survives*. More than two regions may be created;
exactly one is kept. (A player's own move can only ever fragment the opponent, never
themselves, so the survival choice is always about the opponent.)

It is possible that clearing leaves the opponent with a single flock — in which case
**the opponent wins immediately**. So fragmenting the opponent is usually only good for
*them*: use it with care.

## Winning — and win priority

You win by ending your move with **all your birds in one contiguous flock**.

**Regions are always secondary.** If your move *simultaneously* brings all your birds into
one flock **and** fragments the opponent, **you win at once** — no regions are cleared
(so you never have to hand the opponent a winning position). Only if you did *not* win do
regions get resolved, after which the opponent may win as described above.

## Passing and draws

If you have **no** legal add and **no** legal fly, you **must pass**. If your only legal
adds would be into your **own** enclosed regions (and you have no fly), you **may** pass.
**Two consecutive passes end the game in a draw.**

## Move notation

- **Add:** a single point id `q,r`.
- **Single fly:** `from>to`, e.g. `6,-3>-2,-3`.
- **Whole-flock fly:** `*from>to` (the `*` marks a rigid flock translation; `from` is the
  flock's anchor point and `to` its destination).
- **Pass:** `pass`.
- **Region survival choice:** when a move fragments the opponent, the surviving region is
  named by appending `=q,r` (the kept region's representative point). The interface offers
  the choices as a small picker.

## Implementation notes / interpretations

Where the published rules leave room, this package uses the following readings:

- **"Open path"** (regions and the add restriction) = reachability through points that are
  vacant *or* occupied by the relevant player's own birds; enemy birds are walls.
- **Fly-over:** a flight passes freely over vacant points and friendly birds; an enemy bird
  blocks the line. The landing point must be vacant and adjacent to a friendly bird.
- **No-split / enlargement:** every fly must merge the moved unit with at least one further
  friendly bird, and must not disconnect any flock. A multi-bird flying unit is therefore
  always an entire straight-line flock (moving part of a flock away would split it).
- **Supply:** each player owns `points ÷ 2` birds (60 standard / 42 small); cleared birds
  return to supply and may be re-added.
- **Termination:** Volo is not provably finite (flights can cycle), so besides the
  double-pass draw a hard **ply cap** (`4 × points`) also ends the game as a draw. Real
  games end far sooner.
