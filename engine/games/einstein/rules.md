# EinStein würfelt nicht!

*"Einstein doesn't play dice"* — but in this game you do. It is a light 5×5 race
with a die, by Ingo Althöfer (2004). These are the rules **as implemented** here.

## Setup

Each player has **six stones numbered 1–6** in a home corner triangle: Player 1
(red) in the top-left, Player 2 (blue) in the bottom-right. (This package arranges
each player's stones **randomly** at the start, a common variant; the official
game lets you place them yourself.)

## A turn

A **die** is rolled (you'll see it in the caption). You **must move the stone
showing that number**, one step toward the far corner:

- Player 1 moves right, up, or up-right; Player 2 moves left, down, or down-left.

If the rolled number's stone has already been captured, you may instead move the
stone with the **next-higher** or **next-lower** number you still have (your
choice).

**Capturing:** if you move onto an occupied square, that stone is removed — whether
it is your opponent's *or your own*.

## Winning

You win the moment you **land a stone on the opposite corner** (Player 1 on the
bottom-right square, Player 2 on the top-left), or when you have **captured all of
the opponent's stones**. Because every move advances a stone toward the far corner,
the game always ends.

## A note on the dice

The platform models the roll without a separate "chance" step: each move also rolls
the die for the *next* turn and stores it, so the value is already known when you
pick your move — exactly as if you had rolled first. (`has_randomness` is set, so
the computer opponent plays it as a game of chance.)

## Notation

A move is shown as `<number><from><x|->`<to>`, e.g. `3,2,2x3,3` means stone 3
moved from (2,2) capturing on (3,3). Stones display their number in the owner's
colour.
