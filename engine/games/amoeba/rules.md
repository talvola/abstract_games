# Amoeba

**Masahiro Nakajima, 2010** — published by nestorgames (rulebook © 2014 Néstor
Romeral Andrés). Two players, no hidden information, no randomness.

A pile of discs is an amoeba: it creeps forward in one piece, or it *sows* —
spilling itself out along a line, one disc per point, handing back whatever it
had swallowed. Somewhere in your pile is your **kernel**, and once your opponent
owns the top of the pile it is sitting in — and still does at the end of their
turn — you have lost.

## Board and pieces

The board has **37 points** — the vertices of a triangular grid arranged in a
hexagon, four points to a side. (This package draws them as hex cells, which is
the same graph: every point has up to six neighbours, along six straight lines.)

Each player owns **ten discs and one kernel**. The kernel is an ordinary piece
in every respect — it moves like any other and need not be on top of its pile.
Losing it loses the game.

Setup — Black fills the top three rows, White the bottom three, the middle row
starts empty, and each kernel stands alone on the middle point of its row:

```
        . . . .            row g   4 black discs
       . . K . .           row f   the BLACK KERNEL, alone
      . . . . . .          row e   6 black discs
     . . . . . . .         row d   empty
      o o o o o o          row c   6 white discs
       o o k o o           row b   the WHITE KERNEL, alone
        o o o o            row a   4 white discs
```

The position is symmetric under a 180° turn with the colours swapped.
**White moves first.**

## Stacks

A **stack** is a pile of pieces of any height — even one. A stack is
**controlled by the owner of its topmost piece**, and nothing else. So a stack
may contain enemy pieces, and stacks change hands: pile your disc on top of an
enemy stack and the whole thing is yours, prisoners and all.

Pieces are never removed from the board. All 22 stay on it for the whole game.

## Your turn

No passing. Take one stack **you control** and do exactly one of:

### Move

The whole pile travels in a **straight line**, **exactly as many points as it
has pieces**. A stack of three moves three points; a lone disc moves one; a lone
kernel moves one.

- **Nothing blocks it.** The pile flies over occupied points and empty ones
  alike; only the far end matters.
- If a stack is already on the landing point, your pile lands **on top of it**,
  in order, making one taller stack — and you control the result.
- The far end **must be on the board**. A tall pile can therefore be short of
  room, and any pile more than **six** high is frozen for good, because six
  points is the longest straight line this board has.

### Sow

Travel that same line, and **deploy one piece per point**: the pile's **bottom**
piece on the first point, the next one up on the second, and so on, until all of
them are placed. Each piece lands **on top of** whatever is already on its
point.

The whole line must fit on the board, since every piece has to be deployed — so
sowing has the same reach as moving.

Sowing is how prisoners come home. Any enemy piece in your pile lands somewhere
as the new **top** piece, which hands that point straight to your opponent.

*(A stack of height one has only one option — sowing one piece one point is the
same action as moving it — so this package lists it once, not twice.)*

## Winning

**At the end of your turn you win if either**

1. you **control a stack containing the enemy kernel** — its topmost piece is
   yours and their kernel is somewhere in the pile; or
2. your opponent then has **no legal move**.

If you cannot move, you lose. (Since pieces are never captured, that means every
stack you control is jammed against the edge or is too tall to travel — or you
control none at all, every one of your pieces buried.)

The test is asymmetric on purpose, and it is worth understanding: the check is
whether **you** control **their** kernel at the end of **your** turn. If your own
sow hands your opponent a stack that holds your own kernel, the game does *not*
end there — they win at the end of *their* next turn, unless their move happens
to break it up (which it can). Under random play this happens in about 7% of
games, and the opponent converts it 92% of the time.

## Repetition, and how the game is guaranteed to end

Play can repeat for ever on its own: two lone discs shuffle back and forth, and
from the opening position `a1-b1, g1-f1, b1-a1, f1-g1` returns the *exact*
starting position with White to move again.

The **English** rulebook says nothing about that. The publisher's **Japanese**
edition of the same rulebook does, and it is the more complete document:

> 同一局面が 3 回現れた場合 […] 制圧しているスタックの数がより多いプレーヤーの
> 勝ちです。[…] 支配しているスタックの数が同じ場合は、引き分けとします。

In translation: *"If the same position appears 3 times […] the player controlling
the greater number of stacks wins. […] If the number of stacks controlled is
equal, it is a draw."*

So:

- **If the same position (board plus side to move) occurs for the third time,
  the game ends there. Whoever controls MORE STACKS wins; if the counts are
  level it is a draw.** The double shuffle above therefore ends after 8 plies,
  as a draw — the opening position is level at 11 stacks each.

That also makes termination a theorem rather than a hope: there are finitely
many positions, so by the pigeonhole principle some position must reach its third
occurrence. In practice it is a rule for stubborn humans, not for the engine:
across 4,000 random games no position was ever reached a third time (the most any
position recurred was twice), and every game ended on one of the two published
win conditions.

Two further clauses of that Japanese paragraph are **not implemented**, because
they are not mechanisable:

- *"or if neither side has any effective move to control the enemy kernel"* — a
  judgement about whether a win is still possible at all.
- *"if the position does not converge, the player on turn proposes to end the
  game, and if both agree, the stacks are counted"* — an offer-and-agree, which
  the platform already provides through resign / agreed result.

For the engine's own safety there is a hard backstop at **1000 plies**, which
adjudicates by the sheet's own rule (count the stacks) rather than inventing a
different outcome — the automatic version of that last clause. It is the only
rule here that no edition states outright, so it is checked strictly *after*
every other ending, and it decides nothing in practice: over 200,000 random games
the median length was 41 plies, the 99th percentile 150 and the longest 365, and
the cap fired **zero** times. (That 200,000-game distribution was measured
*before* threefold repetition was implemented, so it is an upper bound on the
current one — the repetition rule can only end a game earlier. An independent
re-measurement of 20,000 games on the shipped code gives median 42, 99th
percentile 154, longest 300, cap fired **zero**, and threefold repetition
deciding 13 games — 9 wins and 4 honest draws, 0.065%.)

## How this package was pinned down

Rules as implemented come from the publisher's rulebook in **both editions** —
`nestorgames.com/rulebooks/AMOEBA_EN.pdf` (English, one page) and
`AMOEBA_JP.pdf` (Japanese, translated by Tchié Tokoro) — with all three figures
of each decoded independently, plus the designer's own summary on the
BoardGameGeek entry. They were then differentialled move-for-move against
AbstractPlay's independent implementation of the same game (0 mismatches; the
coordinate map was proved by adjacency isomorphism against that engine's own
graph, and its opening position offers exactly the same 52 moves as this one).

**The two editions are not equivalent, and the Japanese one is the fuller
document** — it carries the whole repetition/adjudication paragraph above, which
the English page simply does not contain, and it states several rules the English
page leaves to inference. Where they overlap they never conflict.

Interpretations, each with its evidence:

- **The kernel counts toward a stack's height.** The English page says a stack
  moves "as many spaces as **discs** comprise the stack", which reads as though
  kernels might not count — but it also defines a stack as "a pile of pieces
  (**discs or kernels**)". The Japanese edition settles it: 「スタックの積まれた
  数と同じ数だけ移動する」("move a number equal to the number of **pieces**
  stacked") together with 「通常駒もカーネル駒も、動きは同じです」("normal
  pieces and kernel pieces move the same"). Under a discs-only reading the lone
  kernel in the opening setup could move zero points and would be frozen from
  move one; counting it gives the opening position 52 legal moves, matching the
  reference implementation exactly, where excluding it gives 46.
- **Sowing deploys the bottom piece first.** Both editions say so in words —
  English "deploy its **bottom** piece on each step", Japanese 「スタックの下から
  順番に１つずつ […] 駒を置いていく」— and the Japanese sowing figure's caption
  numbers the pieces as they land: ①white, ②black, ③white, with ①白 (the bottom
  one) landing on the stack that was already in the way. Note that neither
  *picture* could have settled this on its own: the pile both editions draw is
  white-black-white, i.e. palindromic, so both orders produce an identical
  figure.
- **The English setup figure omits one white disc**, leaving the right-hand end
  of row c empty: it draws ten black discs but only nine white ones. That
  contradicts the same page's own MATERIAL list ("10 white discs, 10 black
  discs") and breaks the 180° rotational symmetry the other 36 points obey
  exactly — and the **Japanese edition's independently drawn setup figure shows
  all six white discs on that row**, ten a side, perfectly symmetric. The
  symmetric reading is used here.
- **The win is tested at the end of the mover's turn only.** The English page is
  explicit ("You win if, **at the end of your turn**, you control a stack with
  the enemy kernel in it"); the Japanese states the condition without a timing.
  The English timing is used, and the reference implementation agrees. This is
  what makes the self-handover described above a one-turn delay rather than an
  instant loss.
- **Board orientation** is pinned only up to a left-right mirror, and that is
  not a defect: the mirror maps the setup to itself, and every rule here is
  geometry-free (distances and directions only), so a mirrored board is
  indistinguishable in every observable. White is drawn at the bottom, as in the
  figure.
