# Soluna

Bruno Faidutti, 2012 (Blue Orange Games / Steffen-Spiele) — a re-theme of his
earlier *Babylon*. Two players, ~5 minutes, no luck after the deal.

## Components

Twelve shared **double-sided discs** carrying four celestial symbols — **Sun ☀,
Moon ☾, Stars ✶, Comet ☄**. Each disc shows a *different* symbol on each side,
and each of the six two-symbol combinations appears on exactly two discs (so
every symbol exists on six faces). **Neither player owns any disc.**

## Setup

The discs are dropped on the table at random: twelve single-disc stacks, each
showing a random face. Only the visible faces ever matter afterwards — stacks
are never flipped or split, so the game is perfect-information once dealt.

*As implemented:* the deal is randomized at game start and the twelve stacks
are laid on a 4×3 grid of slots. **Position is irrelevant** — there is no
adjacency in Soluna; any stack may be played onto any other. Red (seat 0)
moves first.

## Play

On your turn you **must** move one whole stack and place it **on top of**
another stack. This is legal only if, before the move, the two stacks

- show the **same top symbol**, *or*
- have the **same height**.

The moved stack keeps its order, so its top disc becomes the top of the merged
stack. Stacks may never be divided.

## End of the game

Every move merges two stacks into one, so at most eleven moves are possible.
The first player **unable to move loses**; equivalently, whoever makes the
**last move wins**. Draws are impossible.

## Implementation notes

- The physical rulebook plays a match: first to win **four rounds**, with the
  loser of a round starting the next. This implementation is a **single
  round**; play a rematch for the full match experience.
- Clicking a stack then a destination stack plays the move `from>to`.
