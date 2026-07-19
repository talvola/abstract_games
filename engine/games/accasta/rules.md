# Accasta

Dieter Stein, 1998 (Bambus Spieleverlag "tactic blue"). Implemented from the
designer's official rules ([spielstein.com](https://spielstein.com/games/accasta/rules),
version 12 April 1998, updated 7 March 2010 with a new winning condition) and
Stein's article *"Accasta — Introduction to a Pure Stacking Game"* (its Fig. 1
setup and complete sample game anchor this implementation).

## Board and setup

A hexagonal board of **37 points** (hexhex-4). Rows are lettered `a`–`g` from
White's side; spaces are numbered left to right. Nine tinted spaces on each
side form the **castles** (White: a1–a4, b2–b4, c3–c4; Black mirrored:
g1–g4, f2–f4, e3–e4). Each player's 20 pieces start stacked in their castle:

- back row (a / g): four towers of **Shield, Horse, Chariot** (Chariot on top),
- middle row (b2–b4 / f2–f4): three towers of **Shield, Horse**,
- front (c3, c4 / e3, e4): two single **Shields**.

## Moving

White moves first; players alternate; **passing is not allowed**. Shields,
Horses, and Chariots move **up to 1, 2, or 3 spaces** respectively, straight
in any of the six directions. They cannot jump over pieces, but may **land on
any friendly or enemy piece or stack** within reach. A piece's movement never
depends on its position in a stack.

- **Leading / splitting:** the top piece (the "head") may carry any number of
  pieces below it — a stack splits at any point. The moving group travels with
  the range of its *leading* piece. In the app: click the stack, a
  destination, and pick how many pieces move from the top.
- **Captures:** the head dominates the whole stack; enemy pieces under it are
  captured but *never leave the board*. Recapturing the stack liberates them.
- **Multiple moves:** if a split surfaces a **friendly** piece at the origin,
  that piece may also move this turn (optional, repeatable — every sub-move of
  a turn starts from the same origin stack). Press **End turn** to stop.
  Surfacing an **enemy** piece (a "release") ends the turn immediately.
- **Safe stacks:** a stacking move is legal only if the resulting stack has
  **no more than three pieces of the same colour**. A stack containing three
  captured pieces therefore cannot be recaptured — a "safe stack".

## Winning

You win if, **at the beginning of your turn**, you control at least **three
stacks inside the enemy castle** (so the threatened player always has one turn
to defend). You also win if your opponent has **no legal move** on their turn
(2010 rule: they control no stack, or the safe-stack rule blocks everything).

## Variant: Accasta Pari

Official variant ([rules](https://spielstein.com/games/accasta/rules/pari)):
the same game with a **single piece type**. A stack's head moves up to
**min(3, number of pieces of its own colour in the stack)** spaces, evaluated
*before* the move — pieces are promoted or demoted as stacks form and split.
All other rules apply, in particular the three-pieces rule. The app labels
each stack with its head's current movement power.

## Implementation notes

- The article adds "releasing an enemy piece in one's own castle is illegal";
  the current official rules **omit** this rule (the 2010 beginning-of-turn
  win check resolves the double-win paradox it addressed), so it is **not
  enforced** here. A release at home that hands the opponent three stacks in
  your castle simply loses when their turn begins.
- The official Pari page's notation example (`a1:1-c1,+b2`) would put four
  white pieces on b2 and contradicts the three-pieces rule the same page says
  still applies; this implementation follows the **rule**, not the example.
- Draw backstops (house rules — pieces never leave the board): threefold
  repetition of a turn-start position, or a hard cap on game length.
