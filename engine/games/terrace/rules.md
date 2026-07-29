# Terrace

**Anton Dresden & Buzz Siler** — designed 1950, brought to market by Siler/Siler
Ventures. The manifest follows BGG's **1992**, and so does the publisher's own
newsletter: *Terrace Times* Winter 1997 calls the 6x6 board a replacement for
"the eight-level game which was first introduced in 1992". (Wikipedia and the
*Los Angeles Times* piece it cites say 1991; the two are probably a launch/wide-
release distinction, and the first-party statement is the one followed here.)
Winner of *Games* magazine's Best New Abstract Strategy Game and a Mensa Select
award, and a permanent prop on *Star Trek: The Next Generation*.

This page describes the rules **as implemented here**.

## The board

Terrace is played on a square board whose squares sit at **different heights**.
The two diagonally opposite corners `a1` and `h8` are the single lowest squares
(level 1); the squares rise stepwise in L-shaped **terraces** to the other two
corners, `a8` and `h1`, which are the highest. The 8x8 board has eight levels:

```
      a  b  c  d  e  f  g  h
   8  8  7  6  5  4  3  2  1   8
   7  7  7  6  5  4  3  2  2   7
   6  6  6  6  5  4  3  3  3   6
   5  5  5  5  5  4  4  4  4   5
   4  4  4  4  4  5  5  5  5   4
   3  3  3  3  4  5  6  6  6   3
   2  2  2  3  4  5  6  7  7   2
   1  1  2  3  4  5  6  7  8   1
      a  b  c  d  e  f  g  h
```

The 6x6 board is the same shape with six levels. In closed form, the height of
the square in file `c` and rank `r` (both 0-based) on an `N x N` board is

```
elevation(c, r) = min( max(c, r), max(N-1-c, N-1-r) ) + 1
```

Two consequences the rules lean on, both checked in `selftest.py`:

* **No single step ever changes the level by more than one** — not even a
  diagonal one — so "one square per move, one level at a time" is never
  ambiguous.
* **Each level consists of exactly TWO one-square-wide L-shaped chains**, and
  the two chains of a level are never orthogonally adjacent. That is precisely
  what the publisher's rule *"it cannot move across the centerpoint of the
  board"* describes, so it needs no separate implementation: a piece sliding
  along its terrace simply has nowhere to cross to.

## The pieces

Each player has pieces in four sizes (three on the 6x6 board), shown here as
discs whose diameter grows with the size and labelled `1`–`4`. One size-1 piece
per player is marked **`T`** and is that player's royal piece.

**Long game** (the standard setup — 16 pieces each on 8x8, 12 each on 6x6):

```
   8  4  4  3  3  2  2  1  T      Blue
   7  1  1  2  2  3  3  4  4
   6  .  .  .  .  .  .  .  .
   5  .  .  .  .  .  .  .  .
   4  .  .  .  .  .  .  .  .
   3  .  .  .  .  .  .  .  .
   2  4  4  3  3  2  2  1  1
   1  T  1  2  2  3  3  4  4      Red
```

**Short game** (the publisher's quick setup — one rank, both end squares empty):

```
   8  .  T  2  2  3  3  4  .      Blue
   .  (ranks 2-7 are empty)
   1  .  4  3  3  2  2  T  .      Red
```

Each player's array is the 180-degree rotation of the other's, matching the
board's own symmetry.

## How to move

A turn is exactly one move of one of your pieces. There is no pass.

| | |
|---|---|
| **On the same level** | Move to **any vacant square on the same level** that the piece can reach **without jumping over an opponent's piece**. Your OWN pieces may be jumped over. |
| **Up** | **Straight or diagonally** up, one square, to a vacant square one level higher. |
| **Down** | **Straight down only**, one square, to a vacant square one level lower. Diagonal moves down are for capturing only. |
| **Capturing** | Move **diagonally down** one level onto a piece of **the same size or smaller**. The captured piece is removed. |

**Cannibalism.** "Any piece" in the capturing rule includes *your own*. The
publisher advertises this as the game's signature feature: "TERRACE is the first
strategy game ever to include 'cannibalism'... Sometimes it can be to your
advantage to capture your own piece!" Capturing your own `T`, which is legal,
loses the game immediately.

## Winning

* Move your **`T` to the lowest square across the board** — the level-1 corner
  diagonally opposite your own. Red's goal is `h8` (`f6` on the 6x6 board),
  Blue's is `a1`. The two goal squares are tinted in the players' colours.
* Or **capture your opponent's `T`**.

Either ends the game at once.

**Draw.** "If a player cannot make an allowed move, there is no winner and no
loser." A player with no legal move draws the game — they do not lose it.

**A decisive result always outranks a draw.** If the move that wins the game
also happens to leave the opponent with no legal move (or to trip the
no-progress counter below), it is still a win.

This is a deliberate difference from the AbstractPlay reference implementation
used to verify this package, which tests the no-move draw *first* and therefore
scores such a position 0-0. It is not a hypothetical: the commonest way for a
Terrace game to end is by capturing the `T`, and when the `T` was the loser's
last piece they have no legal move either — 1.4% of uniform-random games on the
6x6 short setup end exactly that way. The published rules make the objective
("to capture your opponent's `T`") the win and the draw rule the fallback for a
player who *has* pieces but cannot move them, so this package scores it as a
win.

## Termination (a house rule)

Terrace as published has no draw-by-inaction rule, and non-capturing moves can
be repeated forever. To guarantee that every game ends, this implementation adds
one:

> **200 plies (100 moves each) without a capture is a draw.**

That is twice the chess 50-move convention, and it is the only bound the game
needs: every capture removes a piece permanently, so a game can contain at most
`pieces - 1` captures and therefore at most `pieces x 200` plies.

How often it decides a game, measured over uniform-random play (real play
captures far more readily, so these are upper bounds):

| setup | games | drawn by the no-capture rule | longest game |
|---|---|---|---|
| 8x8 long (default) | 400 | 0 | 628 plies |
| 8x8 long, Rank Capture | 400 | 0 | 422 plies |
| 8x8 short | 400 | 34 (8.5%) | 721 plies |
| 8x8 short, Rank Capture | 400 | 0 | 323 plies |
| 6x6 long | 400 | 0 | 399 plies |
| 6x6 long, Rank Capture | 400 | 0 | 215 plies |
| 6x6 short | 400 | 9 (2.3%) | 499 plies |
| 6x6 short, Rank Capture | 400 | 1 (0.25%) | 328 plies |

The sparse **8x8 short** setup is the one where it bites; every other
combination is essentially untouched, and the standard long game not at all.
(A 2000-game run of 8x8 long tripped it once, 0.05%.) The manifest's
`max_random_plies` is 2000 — above every number in the last column, and well
below the game's own proved bound of `32 x 200 = 6400`, so a termination
regression fails loudly as "did not terminate" instead of being absorbed into a
silent cap draw. `selftest.py` asserts both inequalities, and asserts that the
rule is still *reachable* by real play, so the constant cannot quietly drift
until the rule is dead code.

## Options

* **Board** — `8x8` (the original 1992 game, eight levels, 16 pieces each) or
  `6x6` (the 1997 revision, six levels, 12 pieces each). Wikipedia attributes
  the revision to "legal problems with the owners of the molds to the original
  version"; the inventors' own account in *Terrace Times* Winter 1997 is simply
  that "it's a much better game", with a shorter game and quicker action. Either
  way, "none of the four Terrace rules have been changed" — the two boards
  differ only in size, level count and piece count.
* **Setup** — `Long game` (two ranks, the standard game) or `Short game`
  (one rank; the publisher's 15-20 minute version).
* **Capturing** — `Standard`, or **`Rank Capture`**, Tom Hawkins' variant
  published in the *Terrace Times* newsletter (Summer 1995), where only the
  capturing rule changes:
  * attacking **diagonally down** to the next level — the attacker may be **one
    rank smaller** than its victim;
  * attacking **straight up** to the next level — the attacker must be **at
    least one rank larger**;
  * attacking **on the same level**, to an adjacent square *along the terrace*
    (see the note on "adjacent" below) — the attacker must be **at least the
    same size**;
  * **assassination** — a rank-1 piece (the `T` included) may capture a
    largest-rank piece straight above it on the next higher level.

  Movement and the setups are unchanged.

## Notation

Moves are the platform's `from>to` cell paths (`"3,0>3,1"`). The move log uses
the published square names with the piece's size in front: `2 d1-d2` for a
quiet move, `3 g7xh8` for a capture, and `4 b2*a1` for capturing one of your
own pieces.

## Sources, and what each one settled

1. **"The 4 rules of Terrace", Siler/Siler Ventures** —
   [terracegames.com/rules.html, archived 2006-04-30](https://web.archive.org/web/20060430134129/http://www.terracegames.com/rules.html).
   The publisher's own rules page, and the primary source for every rule above:
   the four movement rules verbatim, the capture-or-escape objective, the
   draw-on-no-move rule, and the statement that the board game and computer game
   share one rule set.
2. **Wikipedia, *Terrace (board game)*** — settled the board's shape ("L-shaped
   levels ... that rise stepwise from the board's lowest points in two
   diagonally opposite corners to its highest points in the other two corners")
   and, crucially, the one rule the publisher's page states only by omission:
   "Players can move any number of squares on the same terrace, and **are
   allowed to jump over their own pieces**." Also the 1997 6x6 revision with 12
   pieces per player.
3. **Terrace Times, Summer 1995** —
   [archived](https://web.archive.org/web/20060504233129/http://www.terracegames.com/TerraceTimes/TT.Summer95.html)
   — the full text of the Rank Capture variant, quoted rule by rule above.
4. **The publisher's own setup artwork** (archived), which is what the four
   opening arrays are checked against square by square:
   * 8x8 — `GIFs/LongGame.gif` and `GIFs/ShortGame.gif`, the Computer Terrace
     screenshots linked from the rules page ("Computer Terrace has two starting
     setups... [Long] or [Short]").
   * 6x6 — `6x6board.gif`, the Long Game photograph on the Terrace6x6 page, and
     `Pg2boards.gif`, whose upper diagram is that page's Short Game ("The
     2-player 'short' game starts as shown in the diagram at right"). Both
     confirm the distinctive detail that the two setups run in *opposite*
     directions: in the long game the `T` sits on its own level-1 corner with
     the pieces growing outward, while in the short game the largest piece is
     the one beside that corner and the `T` is out at the high end.
   * The four worked examples the rules page links (`GIFs/MoveUp.gif`,
     `MoveDown.gif`, `MoveSameLevel.gif`, `Capturing.gif`) anchor the move
     generator directly, branching factor and all: *Move Up* draws **five**
     arrows from one square, which happens at exactly four squares on the 8x8
     board (`b2 c3 f6 g7`) and nowhere else; *Move Down* draws **two**, the most
     any square has (the eight anti-diagonal squares `h1 g2 f3 e4 d5 c6 b7 a8`),
     and draws **no** diagonal arrow at all; *Move Same Level* runs a single
     move the length of a terrace and around its corner; and *Capturing* shows
     one piece taking both an enemy of equal size and one of its **own** pieces,
     each by a diagonal step down.
5. **Terrace Times Winter 1997** —
   [archived](https://web.archive.org/web/20060504233129/http://www.terracegames.com/TerraceTimes/tt.winter97.html)
   — the 6x6 revision in the inventors' own words: 12 pieces instead of 16, two
   rows of vacant squares instead of four, "none of the four Terrace rules have
   been changed", and the 1992 date for the original 8x8 game.
6. **AbstractPlay's `gameslib`** (MIT; used as a rule-*enforcing* oracle only,
   no code copied) — every position of thousands of random games was compared
   move-for-move against it; see `_diff_ap.py`.

### Interpretations and open points

* **Which edition.** The only primary rules text reachable is the publisher's
  own page (© 1998-2003), which covers both the 8x8 and 6x6 board games and the
  computer game and states they share one rule set. It is unambiguous that
  capturing the opponent's `T` wins outright in the two-player game, so that is
  what is implemented. What genuinely differs between player counts is the
  *three- and four-player* game, where losing your `T` removes your pieces and
  the others play on — that variant is out of scope here (this package is
  two-player). A scan of the 1992 8x8 rulebook could not be obtained; the
  closest surviving copy of that text is `TERRACE.HLP` inside the archived
  Computer Terrace shareware (`terracegames.com/downloads/nettersh.zip` →
  `TERRACE.SHR`), a proprietary compressed installer container that was not
  unpacked. The publisher states the board game and the computer game share one
  rule set, so it is expected to agree with the rules page.
* **"Adjacent" in the Rank Capture same-level case — the weakest-anchored
  decision here.** Two squares on the same level can be *diagonally* adjacent
  where a terrace turns its corner (`b3` and `c2` on the 8x8 board are both
  level 3 and physically touch). The source says only "attacking on the same
  level (to an adjacent square only)". Read literally against its sibling
  clauses ("diagonally only", "straight only"), the parenthesis may be
  restricting *distance* — same-level **movement** is unlimited along the
  terrace, so "adjacent square only" would be saying "one step, not a slide" —
  in which case diagonal neighbours would count. Read as "adjacent along the
  terrace", they do not. This implementation takes the second reading, which is
  the one the AbstractPlay reference implementation takes; nothing in the
  newsletter text says so outright.

  What does tilt it that way is the base game's own geometry. Of the 14
  same-level diagonal pairs on the 8x8 board, 12 are the elbows inside a single
  terrace — but the other two are **`d4`/`e5` and `d5`/`e4`, the four squares
  meeting at the exact centre of the board** (`c3`/`d4` and `c4`/`d3` on the
  6x6). Those are the pairs the publisher singles out when the movement rule
  says *"IT CANNOT MOVE across the centerpoint of the board"*: the two chains of
  a level touch nowhere else. Reading "adjacent" as all eight neighbours would
  therefore let a Rank Capture reach straight across the centerpoint — the one
  same-level connection the base rules go out of their way to forbid — even
  though the newsletter says "the only change has been to the capturing rule".
  That is an argument, not a proof; the ambiguity is real.

  It is not a corner case either. Measured over uniform-random Rank Capture
  play, the share of positions in which the side to move has at least one
  same-level *diagonally* adjacent capturable target — a move the other reading
  would allow and this one does not — is:

  | setup | positions | with such a target | extra moves per position |
  |---|---|---|---|
  | 8x8 long | 12,526 | 56% | 0.95 (of ~52 legal) |
  | 8x8 short | 7,899 | 12% | 0.13 (of ~32 legal) |
  | 6x6 long | 5,884 | 64% | 1.09 (of ~31 legal) |
  | 6x6 short | 4,297 | 12% | 0.13 (of ~17 legal) |

  So on the two-rank setups it is live in most positions, and the two readings
  give materially different games. It is confined to the non-default
  `Rank Capture` option — the standard rules, which are what the game normally
  plays, are unaffected.
* **Player count.** The published game supports 2-4 players; the platform fixes
  a game's player count, so this package is the two-player game.
