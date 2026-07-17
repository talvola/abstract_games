# Gliński's Hexagonal Chess

Invented by **Władysław Gliński** (Poland, 1936; launched in Britain 1949) — the most
widely played hexagonal chess variant, with over half a million players at its peak.
Chess on a regular hexagon of **91 hexes** (side 6) in three colours. Each side has the
orthodox army **plus one extra bishop and one extra pawn**: K, Q, 2×R, 3×B, 2×N, 9×P.

## Board & setup

Files `a`–`l` (no `j`); ranks bend 60° at the central f-file. White's corner is f1,
the centre f6, Black's corner f11. Starting position (White / Black mirrored):

- **King** g1 / g10 - **Queen** e1 / e10
- **Bishops** f1, f2, f3 / f9, f10, f11 (one on each of the three hex colours)
- **Knights** d1, h1 / d9, h9 - **Rooks** c1, i1 / c8, i8
- **Pawns** b1, c2, d3, e4, f5, g4, h3, i2, k1 / b7, c7, d7, e7, f7, g7, h7, i7, k7

*(The generic renderer draws the hexagons point-up, so the whole board appears rotated
~30° from the traditional vertical diagram — files run diagonally up-and-left. The
three background shades are the three hex colours; each bishop is bound to one.)*

## Moves

- **Rook**: any distance in the 6 *orthogonal* directions (through cell edges).
- **Bishop**: any distance in the 6 *diagonal* directions (through cell vertices);
  colourbound. A diagonal move passes between — never through — the two cells
  flanking the line, so it cannot be blocked by them.
- **Queen**: rook + bishop (12 directions). **King**: one step in any of the 12.
  **There is no castling.**
- **Knight**: two hexes orthogonally, then one more at 60° (12 possible targets),
  jumping over anything in between. It never lands on its own colour.
- **Pawn**: one vacant hex straight forward. If it stands on **any starting hex of a
  pawn of its own colour** (its own, or one reached by capturing — e.g. after e4xf5
  the pawn may later play f5–f7), it may instead advance two vacant hexes. It
  **captures one hex orthogonally forward at 60° to the vertical** (the two forward
  rook directions that are not straight ahead) — *not* diagonally. **En passant** as
  in chess: a pawn that could have captured a double-stepping enemy pawn on the hex
  it passed over may capture it there on the immediately following move. A pawn
  **promotes** to Q, R, B or N on reaching the end of any file (the 11 far-edge
  hexes: a6, b7, c8, d9, e10, f11, g10, h9, i8, k7, l6 for White). Promotion is
  forced.

## Ending the game

- **Checkmate** wins (+1 / −1).
- **Stalemate is NOT a draw**: per Gliński's tournament rules it scores **¾–¼** in
  the stalemater's favour. On this platform's +1 / 0 / −1 payoff scale that is
  **+0.5 / −0.5** (chess points *p* map to 2p−1), preserving the correct ordering
  win > stalemate-win > draw > stalemated > loss.
- **Draws**: 50-move rule (50 full moves without a pawn move or capture), threefold
  repetition (same position, side to move and en-passant rights), plus a defensive
  1000-ply cap as a termination backstop.

## Interpretations documented (rules as implemented)

- **No "insufficient material" auto-draw.** Unlike orthodox chess, **K vs K
  stalemate is reachable** on the hexboard (white Kf9 covers all five flight hexes
  of a black Kf11 without giving check) and would score ¾–¼, so declaring bare
  kings an automatic draw would misjudge a live position. Pointless K-vs-K shuffles
  end via the 50-move rule. (Also, K + 2N *can* force mate in this game.)
- The repetition key always includes the en-passant target when one exists (a
  conservative reading; it can only delay, never fabricate, a repetition draw).

## Correctness anchor

No published perft series for Gliński's chess was found, so this package froze its
own: **perft(1–3) from the start = 51 / 2,586 / 137,858**, verified two ways:

1. **Exhaustive differential vs an independent implementation** — every node to
   depth 3 (identical legal-move sets and counts) plus 40 seeded random full games
   (19,708 positions, zero move-set mismatches) against
   [`@bedard/hexchess` v2.5.1](https://github.com/scottbedard/hexchess), the
   open-source engine behind hexchess.club (one-time, 2026-07-17).
2. **Hand derivation of depth 1 = 51** from the published rules: 17 pawn moves
   (9 single + 8 double — f5's double step is blocked by Black's f7 pawn, as
   Wikipedia notes), 8 knight (d1→c3, b2, f4, g2 + mirror), 12 bishop (f1→e2, g2;
   f2→four cells each way on the long diagonals; f3→d2, h2), 6 queen (e2, e3, d2,
   c3, b4, a5), 2 king (g2, h2), 6 rook (c1→d2, e3, f4 + mirror).

`selftest.py` re-asserts the perft numbers, the Wikipedia pawn examples (e4xf5
regaining the double step; c7–c5 answered by b5xc6 e.p.), promotion, checkmate,
stalemate scoring, repetition, the 50-move rule and bishop colour invariance.

## Sources

- [Wikipedia — Hexagonal chess (Gliński's variant)](https://en.wikipedia.org/wiki/Hexagonal_chess)
- [chessvariants.com — Glinski's Hexagonal Chess](https://www.chessvariants.com/hexagonal.dir/hexagonal.html)
- Setup cross-checked against the initial-position FEN of
  [scottbedard/hexchess](https://github.com/scottbedard/hexchess) (hexchess.club).
- W. Gliński, *Rules of Hexagonal Chess* (1973), via the above.
