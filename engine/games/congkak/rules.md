# Congkak (Sungka / Congklak)

Congkak is the **Malay / Indonesian / Bruneian** mancala (the closely related
Filipino version is **Sungka**, the Indonesian one **Congklak**). It is a *sowing*
game in the mancala family but is distinct from Kalah and Oware — its signature is
the **relay** (continuation) rule. These are the rules **as implemented** here.

## The board

Each player owns a row of **seven holes** (*rumah* / "houses") plus a **store** —
the large home hole (*rumah besar*, the "head"). South is Player 1 (bottom row),
North is Player 2 (top row). South moves first. Every small hole starts with
**seven seeds**, so there are **98 seeds** on the board; both stores start empty.

> **Variant note.** Congkak rules vary by region. The most common board is the
> seven-hole one implemented here. Some traditions open with **simultaneous** play
> (both players move at once until one's last seed dies); we deliberately do **not**
> model that — play strictly **alternates** by turn, which is the standard version
> for two-player turn-based play. The relay, extra-turn and capture rules below are
> the widely documented standard ones.

## Sowing

On your turn, scoop up **all** the seeds from one of **your own** non-empty holes
and drop them one at a time into each hollow that follows, travelling around the
board — **including your own store**, but **skipping your opponent's store** (you
never add to the opponent's head).

## Relay / continuation (the signature Congkak rule)

Look at where your **last** seed lands:

- **In an occupied hole** (a hole that already had seeds) → you **scoop up that
  whole hole** — the seeds that were there *plus* the one you just dropped — and
  **keep sowing** from there. You relay like this again and again, as long as each
  lap ends on an occupied hole.
- The turn's sowing only stops when the last seed lands in an **empty hole** or in
  your **store**.

## The two outcomes that end (or extend) a turn

- **Last seed in your own store** → you take **another turn** (sow again from any of
  your seven holes).
- **Last seed in an empty hole on YOUR side** → **capture**: that last seed *and*
  all the seeds in the hole **directly opposite** (your opponent's, across the
  board) are moved into **your store**; both holes are left empty and your turn
  ends. (If the opposite hole is empty there is nothing extra to take — just the
  lone seed, which already sits in your hole, and the turn ends.)
- **Last seed in an empty hole on the OPPONENT's side** → your turn simply **ends**
  with no capture; the lone seed stays in the opponent's hole.

## Ending and winning

The game ends when the **player whose turn it is has no seeds to sow** (all seven
of their holes are empty). The other player then **sweeps the seeds remaining in
their own holes into their store**. Whoever has **more seeds in their store** wins;
equal stores (49–49) is a draw. A defensive ply cap also ends a runaway game.

## Notation

A move names the hole sown, e.g. `South c (7)` — South's third hole, holding 7
seeds. Each hole shows its current seed count; the two store totals are shown in the
caption ("South 12 — North 9").
