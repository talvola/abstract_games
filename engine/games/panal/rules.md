# Panal

**Glenn Overby II, May 2003** — *panal* is Spanish for **honeycomb**. A hexagonal chess
on **61 hexes** in which the two armies face each other across **opposed sides**, not
opposed corners, and in which — uniquely among the hex chesses in this app — there is
**no hex diagonal at all**. Only the six directions of travel of a hexagon exist.

> *"I have always found the diagonal move as defined in many hexagonal games to be
> contrived, born of a determination to mimic traditional chess moves."* — the author

The four non-royal pieces are one of each of the four classical families of chess move:
a **stepper** (Soldier), a **leaper** (Horseman), a **rider** (Princess) and a **hopper**
(Gunne). There are **two royal pieces per side**, with two quite different ways to lose.

These rules are as implemented here. Sources: the author's article at
[chessvariants.com](https://www.chessvariants.com/hexagonal.dir/panal.html) — prose
rules, a setup diagram, and a complete annotated sample game — and **the author's own
Zillions rules file** (`panal.zip` → `panal.zrf`), linked from that page. Where they
disagree, see *Interpretations* at the bottom.

## The board and the notation

61 hexes: the central 61 of Gliński's 91 (a hexagon of side 5), coloured in three
shades that have no bearing on play. A **rank** is a horizontal row of hexes, so the
board is drawn with **pointy-top** hexes: a hex has neighbours E and W, but none
directly above or below. **That is the geometric reason a Soldier has only two forward
directions instead of three.**

Files are lettered `a`–`q` and ranks numbered `1`–`9`; horizontally adjacent cells are
**two letters apart**, and the two "upward" neighbours are one letter and one rank away:

```
        e9  g9  i9  k9  m9
      d8  f8  h8  j8  l8  n8
    c7  e7  g7  i7  k7  m7  o7
  b6  d6  f6  h6  j6  l6  n6  p6
a5  c5  e5  g5  i5  k5  m5  o5  q5
  b4  d4  f4  h4  j4  l4  n4  p4
    c3  e3  g3  i3  k3  m3  o3
      d2  f2  h2  j2  l2  n2
        e1  g1  i1  k1  m1
```

The six directions from `i5` are therefore `g5` and `k5` (W, E), `h6` and `j6` (the two
"forward" ones for White), and `h4` and `j4` (backward for White). The move log uses
these names; they are also printed faintly on the board.

## Setup

```
        bM  bG  --  bG  bP          9
      --  bH  bH  bH  bH  --        8
    --  bS  bS  bS  bS  bS  --      7
  --  --  --  --  --  --  --  --    6
--  --  --  --  --  --  --  --  --  5
  --  --  --  --  --  --  --  --    4
    --  wS  wS  wS  wS  wS  --      3
      --  wH  wH  wH  wH  --        2
        wP  wG  --  wG  wM          1
```

| | White | Black |
|---|---|---|
| 5 Soldiers `S` | e3, g3, i3, k3, m3 | e7, g7, i7, k7, m7 |
| 4 Horsemen `H` | f2, h2, j2, l2 | f8, h8, j8, l8 |
| 2 Gunnes `G` | g1, k1 | g9, k9 |
| 1 Princess `P` | e1 | m9 |
| 1 Monarch `M` | m1 | e9 |

Black's array is White's rotated 180°, so each Princess faces the enemy Monarch down
the long side. White moves first, up the board; Black moves down.

## The pieces

**Soldier** — moves **one hex forward or sideways, never backward**: for White, to the
two upward neighbours or to E/W. It **captures the same way in all four of those
directions** (unlike an orthodox pawn). It may instead make a **two-hex move forward
without changing direction if both hexes are vacant**; that longer move never captures,
and it is available from *any* hex, not only from the home rank. Soldiers **do not
promote** and there is **no en passant**.

**Horseman** — moves **exactly two hexes in any direction or combination of
directions, ignoring any intervening piece**, and *"may not end its move in the hex it
came from, or in any hex adjacent to that hex"*. That is exactly the **12 hexes at
distance two**: six two-step straights and six 60° combinations (the 120° and 180°
combinations are what the exclusion clause rules out). In Betza terms, the hexagonal
**DF** — a dabbabah plus a ferz.

**Gunne** — the artillery. It **moves one hex in any of the six directions without
capturing**. It **captures like a Chinese cannon**: slide any clear distance along one
of the six lines, **leap over exactly one piece of either colour**, and land on the
**next** piece in that line if it is an enemy. A Gunne one hex away from an enemy
therefore cannot touch it at all.

> If a Gunne could capture a given enemy piece, it may do so by moving to that hex —
> **or it may stay where it is and *shoot*, removing the enemy without moving.**

**Princess** — slides any distance along one of the six lines (a hexagonal rook). She is
**royal by capture**: *"If the Princess is captured, the game is lost."* It is expressly
**not illegal** to leave her where she can be taken — *"if you snooze, you lose"*.

**Monarch** — *"rules the kingdom, but does not lead the army to war."* He **may not move
at all unless he is in check**. When in check he may **swap places with a friendly piece
that is not itself under threat** — any friendly piece, anywhere on the board. He never
captures, and therefore never threatens anything either: two Monarchs may stand side by
side without either being in check.

## Winning, and check

Two ways to lose, and they are quite different:

1. **Your Princess is captured.** The game ends immediately. Nothing protects her.
2. **Your Monarch is checkmated.** *"If no move by any friendly piece will take the
   Monarch out of check, the game is lost."* As in orthodox chess a move that leaves
   your own Monarch in check is illegal — which is also why the Monarch himself can
   never actually be captured. Check may be answered in any of the usual ways: capture
   the attacker, block the line, break the Gunne's screen count, or swap the Monarch
   away.

Everything not described above is as in orthodox chess. There is no castling, no
promotion and no en passant.

### Draws

The author notes that *"stalemate is impossible, and it is hard to conceive a draw by
repetition except through inattention"*. Stalemate is in fact **not** impossible — the
selftest constructs one (White's five Soldiers walled along rank 9, where a Soldier has
only its two sideways neighbours, his Princess boxed in behind them and his Monarch
immobile because he is not in check) — and a fabricated result would be a bug, so this
implementation ends the game as a **draw** if any of the following happens:

- the side to move has **no legal move and is not in check** (stalemate);
- **100 plies** (50 moves each side) pass with no capture and no *forward* Soldier
  move — a sideways Soldier step is reversible, so it does not reset the counter;
- the **same position occurs three times** with the same side to move;
- a hard **8,500-ply cap** is reached (a backstop that cannot be hit: at most 83
  plies of a game are irreversible — 60 forward Soldier steps plus 23 captures —
  and each of the 84 reversible runs they delimit is at most 100 plies long, so
  the counters above bound a game at 8,483 plies).

**A decisive result always outranks these counters.** A Princess captured, or a
Monarch mated, on the hundredth reversible ply or in a thrice-repeated position is a
win, not a draw. (Measured over 1,000 uniform-random games: 97.2% end by Princess
capture, 2.8% by checkmate, **none** by any counter, and the longest ran 262 plies.)

## Playing it here

- Click a piece, then a highlighted hex. A Gunne's capture offers a **choice**:
  **Capture by moving in** or **Shoot (Gunne stays put)** — the move strings are
  `from>to` and `from>to=SHOOT`.
- To swap the Monarch (only possible when he is in check), click him and then the
  friendly piece to swap with.
- Move log: `Si3-g5`, `Sg5xh6`, `Gg1xm7` (capture by moving in), **`Gg1*m7`** (a shot),
  `Mm1<>Hl2` (a swap). A `+` marks a move that threatens either royal — check on the
  Monarch or an attack on the Princess, which is the author's own use of the symbol —
  and `#` the move that ends the game.

## How Panal differs from the other hex chesses here

The six classical hexagonal chesses in this app — **Gliński's**, **McCooey's**,
**Shafran's**, **Brusky's**, **de Vasa's** and **Mini Hexchess** — all transplant the
orthodox army onto a hex board, and all of them invent a *hex diagonal* so that they
can keep a bishop and a 12-direction queen; they have promotion, en passant and a
single royal king that steps one hex in any of the twelve directions. **Starchess** is
likewise an orthodox army (on a 37-cell star, with an opening placement phase), and
though it also drops the hex diagonal it keeps orthodox royalty. **Xiang Hex** is
hexagonal *Xiangqi*, with a river, a palace and cannons that have no shooting option.

Panal shares none of that: a **purpose-designed army** of one stepper, one leaper, one
rider and one hopper; **six directions only**; **no promotion, no en passant, no
castling**; a **cannon that can shoot without moving**; and **two royal pieces with two
different loss conditions**, one of which — the Princess — is deliberately *not*
protected by the rules.

## Interpretations

The two sources are complete and agree almost everywhere. Every place where a judgement
was needed:

1. **The Soldiers' starting rank.** The article's setup *table* prints the Soldiers on
   ranks 1 and 9 — which is impossible, since that would stack five Soldiers on top of
   the two Gunnes, the Princess and the Monarch. The author's ZRF, his setup diagram
   and every move of his sample game put them on **ranks 3 and 7**, which is what is
   implemented.
2. **`Gh9xh6` (move 3 of the sample game).** `h9` is not a hex of this board. Only the
   Gunne on **k9** can make that capture (hopping the Horseman on j8), and the author's
   own diagram nine plies later shows k9 empty and g9 still occupied. Read as `Gk9xh6`.
3. **The two-hex Soldier move is not restricted to the home rank.** Neither source
   attaches any such condition, and the ZRF's move generator has no start-cell guard.
4. **No promotion, no en passant.** The article never mentions either; the Playing Tips
   say Soldiers *"don't promote"*, and the ZRF's Soldier has no promotion or e.p. rule.
   A Soldier on the far rank simply has sideways moves only.
5. **A Soldier's sideways move captures.** The sources give a Soldier one move
   description covering all four directions, and the ZRF marks all four
   `not-friend?` — i.e. move or capture alike.
6. **"A friendly piece not so threatened"** is *exactly* the orthodox requirement that
   the Monarch may not be left in check: a swap leaves every hex of the board occupied
   as it was, and enemy attacks depend only on occupancy and on the *enemy's* own
   pieces, so the enemy's attack set is identical before and after a swap. Both
   conditions are enforced; they provably never disagree.
7. **The Monarch has no attack.** He has no capturing move of any kind, so he threatens
   nothing, and a piece "defended" only by him is not defended at all.
8. **The enemy Monarch is never a legal capture target.** He cannot be en prise at the
   start of a turn (that would have been an unanswered check), so this is inert; it is
   enforced structurally rather than left to be proved.
9. **Stalemate is a draw**, per orthodox chess and per the Zillions default the author's
   file relies on. He believes it unreachable — but a stalemate position does exist
   (it is built and scored in the selftest), so it is handled honestly rather than
   assumed away.
10. **Shot notation.** The article writes a shooting capture as a bare `xm7`, noting that
    the same capture *by moving* would be `Gg1xm7`. Since a move log must tell the two
    apart, a shot is written `Gg1*m7` here.
