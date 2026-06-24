# Spartan Chess

*An asymmetric-army chess variant by **Steven Streetman** (2010), published on
[chessvariants.com](https://www.chessvariants.com/rules/spartan-chess). The
**Persians** (an orthodox army) face the **Spartans** (two Kings and four unique
pieces). This page documents the rules **as implemented** here.*

## Overview

* **Persians = White = player 0.** A standard FIDE army with **one King**.
  Persian pieces, pawns, castling, en passant and promotion are all orthodox.
* **Spartans = Black = player 1.** Two Kings, eight Hoplites and four unique
  piece types. The Spartans may **not** castle and have **no** en passant.
* **The Persians (White) always move first.**

## Starting position

| | a | b | c | d | e | f | g | h |
|---|---|---|---|---|---|---|---|---|
| **8** (Spartan) | Lieutenant | General | **King** | Captain | Captain | **King** | Warlord | Lieutenant |
| **7** (Spartan) | Hoplite | Hoplite | Hoplite | Hoplite | Hoplite | Hoplite | Hoplite | Hoplite |
| **2** (Persian) | Pawn | Pawn | Pawn | Pawn | Pawn | Pawn | Pawn | Pawn |
| **1** (Persian) | Rook | Knight | Bishop | Queen | **King** | Bishop | Knight | Rook |

The Persian first rank is the orthodox `R N B Q K B N R`; the Spartan back rank is
`L G K C C K W L`.

## The Persian (White) army

The Persians play exactly as in orthodox chess: Rook, Knight, Bishop, Queen and a
single royal King, with eight pawns. **Castling** (king + rook), **en passant**
and **pawn promotion to Q/R/B/N** all follow standard chess rules.

## The Spartan (Black) army

* **General (G)** — moves as a **Rook** *or* one square diagonally (rook + king).
* **Warlord (W)** — moves as a **Bishop** *or* leaps as a **Knight**.
* **Captain (C)** — moves or captures **one or two squares orthogonally**
  (horizontally/vertically). It **jumps**: if the first square is blocked (friend
  or foe) it may still reach the second square.
* **Lieutenant (L)** — moves or captures **one or two squares diagonally**,
  **jumping** over a blocking first square; and may additionally move (but **not**
  capture) **one square sideways**.
* **Hoplite (H)** — the Spartan pawn. It **moves one square diagonally forward**
  (this move never captures) and **captures one square straight ahead**. On its
  **first move** a Hoplite may go **one or two squares diagonally forward**,
  jumping the first square, but may **not** capture on that jump. (There is no
  en passant against a Hoplite.)
* **King (K)** — an orthodox king (one square in any direction). The Spartans
  begin with **two**.

## The two-King mechanic (the signature rule)

While the Spartan has **two Kings** in play, a Spartan King is **immune from
check**. The Spartan may move a King onto an attacked square, leave a King under
attack, or make a move that exposes a King to attack. The **only** restriction is:

> **Duple-check.** A Spartan move that leaves **both** Kings under attack at the
> same time is **illegal**.

Because a single Spartan King is not protected by check, the **Persian may capture
a Spartan King** as an ordinary capture. Once the Spartan is reduced to **one
King**, that King reverts to an orthodox royal: ordinary check and checkmate apply
to it.

## Winning

* **The Spartans win** by **checkmating the Persian King** (orthodox checkmate).
* **The Persians win** by either:
  1. **capturing one Spartan King and checkmating the other**, or
  2. **duple-check & mate** — placing **both** Spartan Kings under simultaneous
     attack such that, on the Spartan's move, **no** move removes at least one
     King from attack.

Mechanically (as implemented): the side to move is **in danger** when

* it is the **Persian** (or a one-King Spartan) and its King is attacked, or
* it is a **two-King Spartan** and **both** Kings are attacked (duple-check).

If the side to move has **no legal move while in danger**, it is **mated and
loses**. With **no legal move while NOT in danger**, the game is a **stalemate
draw**.

## Hoplite promotion

A Hoplite that reaches the **last rank** (the Persian first rank) promotes:

* to a **General, Warlord, Captain or Lieutenant** — always available; and
* to a **King** — **only if the Spartan currently has exactly one King in play**
  (this lets the Spartan regain a second King, restoring check immunity).

## Draws

In addition to stalemate: the **fifty-move rule** (100 half-moves with no capture
or pawn/Hoplite move), **threefold repetition**, and a **600-ply hard cap**
(to guarantee termination) all draw. The orthodox insufficient-material rule is
disabled — it is meaningless with two royals and unorthodox material.

## Implementation notes / interpretations

* **Source of truth:** the inventor's chessvariants.com page (Steven Streetman),
  corroborated by H. G. Muller's XBoard/WinBoard implementation and pychess. The
  Spartan pieces match the Betza definitions on those pages: General `RF`, Warlord
  `BN`, Captain `WD`, Lieutenant `FAsmW`.
* **King capture is a real, legal move** in this engine (orthodox chess never
  permits it). It is the mechanism by which the Persian removes a Spartan King and
  ends check immunity.
* **No source ambiguity** was found on the core rules; the only judgement call is
  the draw set above (chosen to match the rest of this platform's chess variants
  and to guarantee termination).
