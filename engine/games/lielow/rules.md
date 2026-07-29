# Lielow

**Michael Amundsen & Alek Erickson, 2021** — a chess-like played with nothing
but a checkers set. Two players, no chance, no hidden information. These are the
rules **as implemented** in this package.

Sources used, in order of authority: the designers' own rules text as published
by Arthur O'Dwyer at
[quuxplusone.github.io/blog/2022/09/02/lielow](https://quuxplusone.github.io/blog/2022/09/02/lielow/)
(which also hosts the designers' AI at `quuxplusone.github.io/Lielow/`), the
Board Game Arena help page
[en.doc.boardgamearena.com/Gamehelplielow](https://en.doc.boardgamearena.com/Gamehelplielow),
and [BGG 349408](https://boardgamegeek.com/boardgame/349408/lielow). Every rule
below was additionally checked move-for-move against the AbstractPlay
`gameslib` reference implementation, which is MIT-licensed and was used here
purely as a rule-enforcing oracle — no code from it was copied.

## Material and setup

- An ordinary **8×8** chessboard.
- **8 stacks per player.** A "stack" is a pile of checkers of one colour; its
  **height** is how many checkers are in it. White is seat 0, Black is seat 1.
- Each player's eight stacks start on their **second rank — the chess pawn
  rank** — each of **height 1**. So White fills a2…h2 and Black fills a7…h7.
- **White moves first.**
- **Nobody starts crowned.** All eight of your stacks are tied at height 1, so
  there is no *unique* tallest stack and no crown is placed until after a move.

```
8 . . . . . . . .
7 b b b b b b b b     every stack starts at height 1
6 . . . . . . . .
5 . . . . . . . .
4 . . . . . . . .
3 . . . . . . . .
2 w w w w w w w w
1 . . . . . . . .
  a b c d e f g h
```

## Your turn — move exactly one stack

> "On your turn, move one of your stacks, queenwise, exactly the same number of
> spaces as its current height."

- **Queenwise** = any of the eight directions: orthogonal or diagonal.
- **Exactly** its height — not up to it. A height-3 stack moves three squares or
  not at all; it can never move one or two.
- **Stacks jump.** Only the landing square matters; anything standing in between
  is irrelevant ("pieces … can pass through other pieces" — BGA).
- **Passing is not allowed.**

What happens depends on where the stack lands:

| landing square | result |
|---|---|
| **empty** | the stack moves there and **grows by 1** |
| **an enemy stack** | the enemy stack is **removed from the game**, and your stack moves there and **resets to height 1** |
| **one of your own stacks** | **not allowed** — that is not a legal move |
| **outside the board** | your stack is **removed from the game** (its height does not change; it is simply gone) |

Because a stack that ends up 8 high can no longer reach any square on an 8×8
board, **height 8 is the ceiling** — such a stack's only legal move is to walk
off the edge. And a stack may only walk off the edge when it actually has the
range to clear it: a stack of height *h* on file *c*, rank *r* can leave exactly
when `c − h < 0`, `c + h > 7`, `r − h < 0` or `r + h > 7`. So a height-1 stack
can only leave from the rim, while any height-8 stack can leave from anywhere.

## The crown

> "If, at the end of your turn, you have a unique tallest stack, that stack
> becomes your 'king.' … If you have no unique tallest stack, your crown stays
> wherever it was."

This is checked **for both players after every move** (BGA: "After each move,
both players check the levels of their pieces"), because a capture changes the
victim's stacks too. Three consequences worth spelling out, because they are the
whole subtlety of the game:

1. **A tie does not move the crown.** "Another of a player's pieces may gain a
   level and tie that player's king, but the king's identity does NOT change in
   this situation" (BGA). So your crown can end up sitting on a stack that is
   *not* strictly the tallest — it is the last stack that was ever *uniquely*
   tallest.
2. **The crown travels with its stack.** Move your crowned stack and the crown
   goes with it.
3. **A capture re-crowns both sides.** Capturing resets your own mover to 1,
   which can hand your crown to a different stack of yours; and it removes one of
   the opponent's stacks, which can move *their* crown too.

## Winning

> "If your king is captured, or moves off the board, then you lose."

So there are exactly two ways the game ends, and both are the death of a crowned
stack:

- your opponent lands on your crowned stack — **you lose**; or
- **you** walk your own crowned stack off the edge — **you lose**. This is a
  legal move, and losing on purpose is a real (if unhelpful) option; more often
  it happens because a tall stack has run out of squares.

There is **no draw** in Lielow, and this package never invents one: see the two
proofs below.

## Why the game always ends

The `PLY_CAP = 512` constant in `game.py` is a backstop that **provably never
fires**. Let Φ be the total height of everything standing on the board (Φ = 16 at
the start). No stack can exceed height 8, so Φ ≤ 8 × 16 = 128 at all times. Then:

- a move onto an empty square adds exactly **+1** to Φ and removes nothing;
- a capture or a walk-off **removes a stack** and *decreases* Φ — by at most 15
  (a captured stack of at most 8, plus the mover falling from at most 8 down to
  1), or by at most 8 respectively.

Only 16 stacks ever exist and none is ever created, and the game is over by the
time the 15th removal happens (a player's last stack is always their crowned one
— see the next section), so there are at most **15** removing moves, losing at
most 15 × 15 = 225 from Φ in total. The number of non-removing moves is therefore
at most Φ_end − Φ_start + 225 ≤ 128 − 16 + 225 = 337, and the whole game is at
most **352 plies**. The manifest's `max_random_plies` is 400 — above the proven
bound and below the cap — so if a future change ever broke termination,
conformance would report "did not terminate" instead of the cap quietly emitting
a draw. In 1,500 uniform-random games the longest ran **73** plies, every one of
them ended with a crown dead, none was a draw and the cap never fired. If it
somehow did, the result would be an honest draw (`winner = None`, returns
`[0, 0]`) — no tiebreak is invented.

## Why nobody can ever be stuck

A player with at least one stack **always** has a legal move, so there is no
stalemate and no need for a pass rule. Take that player's **right-most** stack,
of height *h* on file *c*. Its eastward landing square is file *c + h*. If that
is off the board, the stack may leave the board. Otherwise the square is on the
board and cannot hold one of that player's own stacks — such a stack would be
further right, contradicting the choice — so it is empty or holds an enemy, and
either way the move is legal. (The same argument shows a player's **last** stack
is always their crowned one, which is why capturing someone's final stack is
always a crown capture and ends the game.)

`game.py` still carries a defensive branch that awards the win to the opponent if
the player to move somehow has no legal move at all, so that a future rule change
can never hand the server an empty move list; the branch is exercised by
`selftest.py` on a hand-built position that ordinary play cannot reach.

## Move notation used by this package

| move string | meaning |
|---|---|
| `c1,r1>c2,r2` | move the stack on `c1,r1` to `c2,r2` (growing it, or capturing there) |
| `c,r>off` | the stack on `c,r` **walks off the board** and is removed |

**Cell ids** are `"c,r"` with `c` = file `a`…`h` = 0…7 and `r` = rank 1…8 = 0…7,
so `a2` is `0,1` and `h7` is `7,6`.

Ordinary moves are played on the board: **click a stack, then click where it
goes**; its legal destinations light up. All eight off-board directions collapse
into the single `c,r>off` move, because they all produce the identical position.

`off` is deliberately **not** a cell id, so the walk-off is not a board click at
all — it appears below the board as its own **labelled button** ("Walk a2 off the
board", and "— RESIGNS (your king)" when that stack is the crowned one). The
alternative encoding, a path from a square to itself, would have been fired by
the *second* click on an already-selected stack — which is the universal
"never mind, deselect" gesture — and in Lielow that click permanently destroys a
stack and loses the game outright when it is the crowned one. Walking a stack off
the board is always deliberate, so it is always a button. At most one button can
appear per stack you own (so never more than eight; the median in random play is
four). `apply_move` additionally **refuses** the self-path spelling `c,r>c,r`
outright, so the guarantee does not depend on the renderer's routing alone.

The move log uses chess names, matching the reference implementation:
`e2-e3` (a quiet move), `d4xg7` (a capture), `a2-off` (walked off the edge), with
a trailing `#` on the move that ends the game.

## How the board is drawn

Each stack is drawn as a **tower of bands** in its owner's colour with a height
badge — the `piece.stack` primitive — rather than as a disc with a number on it.
That is the component-faithful choice: Lielow's pieces really are physical piles
of checkers ("stacks", in the designers' own wording, and the game's pitch is
that it needs only a checkers set), and height is *the* thing a player must read
at a glance. The crowned stack additionally carries a **♚** marker, standing in
for the physical crown token the rules tell you to place on your king.

## Interpretations and sourcing

Everything below is either quoted from a source above or was settled against the
AbstractPlay oracle; nothing is invented.

1. **No crown at the start.** No source places a crown during setup, and the
   accession rule ("*if* you have a unique tallest stack") cannot fire on eight
   stacks tied at height 1. The oracle agrees — both crowns are unset until the
   first move creates a unique tallest stack. A consequence: White's very first
   move, if it is `a2-off` or `h2-off`, leaves White with seven tied stacks and
   still no crown.
2. **Which rank.** "The second rank (where the pawns start in chess)" — White on
   rank 2, Black on rank 7, confirmed by the oracle's starting array.
3. **White moves first** (BGA, and the oracle).
4. **Stacks jump.** Stated outright by BGA ("can pass through other pieces");
   the oracle likewise checks only the landing square. The path is never
   examined.
5. **The walk-off is a genuine, freely-available move**, not just something that
   happens to over-tall stacks: any stack whose height would carry it past an
   edge may take it, including a height-1 stack on the rim on move 1.
6. **Height on walking off.** "Moving off the board removes the piece without
   changing its level" (BGA) — moot, since the stack is gone, and no source
   suggests any credit for it.
7. **The crown may sit on a stack that is not currently the tallest** — this
   follows from the tie rule and is stated explicitly by BGA. It is the single
   most easily-mis-implemented rule in the game, and the reason this package
   stores the crown's square in the state rather than recomputing it from the
   board.
8. **A player who has no unique tallest stack and no crown yet stays uncrowned**
   (the accession rule is the only thing that ever places a crown).
9. **The 9×9 variant** that AbstractPlay offers (`size-9`, two rows of stacks a
   side) is *not* implemented — it is that site's own variant, not part of the
   designers' published rules.
10. **Stalemate and draws** are not mentioned by any source. Neither is
    reachable — see the two proofs above — so no rule was invented for them; the
    unreachable fallbacks are documented where they live.

## Anchors

- **The opening has exactly 46 legal moves** (6 for each of the six interior
  stacks, 4 + a walk-off for each of a2 and h2) — the number the AbstractPlay
  implementation reports, and an independent check on both the starting array and
  the movement rule.
- `_diff_ap.py` plays random games in **lockstep** against the AbstractPlay
  oracle and compares the legal-move set (as cells, never as move strings), every
  stack's square/owner/height, **both crowns**, the side to move, terminality and
  the winner at every ply. 2,400 games / **51,560 positions** across three runs —
  a uniform policy and two capture-seeking ones, together covering 4,976
  captures and 4,862 walk-offs — produced **0 mismatches**. (Uniform random play
  hardly ever captures, so the capture-biased policy is what actually exercises
  the height reset, the crown re-accession that follows a capture, and winning by
  crown capture.)
- `selftest.py` (pure stdlib, in the test suite) re-derives move generation with
  a second independent formulation, pins the height and crown mechanics on
  hand-built positions, checks both losing conditions, and checks that a decisive
  result outranks the ply counter — with a control proving the counter is live on
  that same ply.

## Why this is not one of our other games

**Not Focus or Mixtour.** Those build *mixed* stacks that you split and carry;
control is about whose checker is on top, and the distance rule refers to the
number of pieces you lift (Focus) or the height of the *target* stack (Mixtour).
A Lielow stack is a single-colour counter that is never split, never merged and
never captured piecemeal — it is a piece with a number on it.

**Not Battle Sheep**, which also moves "as far as the stack allows": there you
split a tower and slide *as far as possible* in a direction, on a hex pasture,
scoring territory. Lielow moves *exactly* the height, on squares, and is won by
royal capture.

**Not Byte**, the other checkers-on-a-chessboard stacking game here: Byte is
merge-only, confined to the dark squares, and has forced moves for isolated
stacks. Nothing in Lielow merges.

**Not a chess variant** in the usual sense either — there are no piece types, no
promotion, no check, and the "king" is not a piece you place but a title that
migrates to whichever of your stacks was last uniquely tallest. That migrating
crown, plus a mover that must travel exactly its own height and grows every time
it does, is the combination no other package in this library has.
