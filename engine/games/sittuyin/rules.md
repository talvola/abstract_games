# Sittuyin (Burmese chess)

Sittuyin (Burmese: စစ်တုရင်, "representation of war") is the traditional chess of
Myanmar (Burma), played on an 8×8 board. It is a close cousin of Makruk (Thai
chess) and descends from the same medieval ancestor as chess. Its two signature
features are a **deployment (setup) phase** — only the pawns start on the board,
and the players alternately place their other pieces — and a distinctive
**pawn-to-general promotion**. **White (player 0) deploys and moves first.**

## Pieces and how they move

Each side has 1 King, 1 General, 2 Chariots, 2 Elephants, 2 Horses and 8 Pawns.

- **Min-gyi (King, `K`)** — moves one square in any of the eight directions,
  exactly like a chess king. It may not move into check. **There is no castling.**
- **Sit-ke (General, `G`)** — a *ferz*: moves **one square diagonally** in any of
  the four diagonal directions. A short-range piece.
- **Sin (Elephant, `E`/`e`)** — moves **one square diagonally (any of the four
  diagonals) or one square straight forward** — five destinations in all. It
  cannot move straight backward or sideways, so its move is directional and
  depends on which side owns it (White's elephant uses the letter `E`, Black's
  uses `e`; both render and are described as "Elephant"). This is the same move
  as the Makruk Khon / a Shogi silver general.
- **Myin (Horse, `N`)** — moves like a chess knight (the (1,2) leap) and jumps
  over pieces.
- **Yahta / Ratha (Chariot, `R`)** — moves any number of free squares
  orthogonally, exactly like a chess rook.
- **Ne (Pawn / feudal lord, `P`)** — moves **one square straight forward** (never
  two — there is **no double step** and therefore **no en passant**), and
  **captures one square diagonally forward**.

All pieces capture by moving onto an enemy piece (the pawn only on its two
diagonal-forward capture squares).

## Starting position and the deployment (setup) phase

At the start, **only the pawns are on the board**, in a characteristic staggered
("split") formation:

```
8  . . . . . . . .      (Black deploys here, rows 6-8)
7  . . . . . . . .
6  . . . . b b b b      Black Ne: files e-h on rank 6
5  b b b b . . . .      Black Ne: files a-d on rank 5
4  . . . . B B B B      White Ne: files e-h on rank 4
3  B B B B . . . .      White Ne: files a-d on rank 3
2  . . . . . . . .      (White deploys here, rows 1-3)
1  . . . . . . . .
   a b c d e f g h
```

That is: White's pawns sit on files **a–d on rank 3** and files **e–h on rank 4**;
Black's pawns mirror this (a–d on rank 5, e–h on rank 6). This is the start
position used by the Fairy-Stockfish `sittuyin` variant.

Then comes the **deployment / setup phase** (Burmese *sit-tee*). The players
**alternately place their remaining eight pieces** (King, General, 2 Chariots, 2
Elephants, 2 Horses) **from a reserve onto their own half of the board**:

- A piece may be deployed onto any **empty square in the player's own three
  ranks** (rows 1–3 for White, rows 6–8 for Black) — i.e. on or behind its own
  pawns.
- **Chariots (Rooks) may only be deployed on the back rank** (rank 1 for White,
  rank 8 for Black).
- The two sides alternate one placement at a time, **White first**, until both
  reserves are empty (16 placements total). The normal **play phase then begins,
  with White to move.**

In this implementation each deployment is a **drop move** of the form `L@c,r`
(click the piece in your reserve tray, then click a highlighted target square).
The legal deployment region for the side to deploy is **tinted** on the board,
and the pieces still to place are shown in the reserve trays.

**Check and checkmate do not apply during the deployment phase** — the kings are
being placed, so the phase is purely placement; the game cannot end until both
sides have fully deployed.

> *Interpretation (deployment order).* Over the board, each side deploys all of
> its pieces simultaneously behind a small curtain, so the deployments are
> independent and hidden. A turn-based engine cannot reproduce that, so here the
> placements are made **sequentially and openly, alternating White/Black**. This
> is the same modelling choice made by digital implementations (pychess). One
> consequence is that the *second* player sees the first player's placements;
> over-the-board rules that constrain the second player relative to the first
> (e.g. "the second player may not place a chariot giving immediate check") are
> **not enforced** here — check simply has no meaning until deployment is
> complete.

## Sit-tu promotion (pawn → General)

A pawn may be promoted to a **General**, but only under tight conditions tied to
the board's two long diagonals (the *sit-ke-myin*, "general's lines"):

- The **promotion squares** are the squares of the **two long corner-to-corner
  diagonals that lie in the enemy half of the board.** For White these are
  `a8, b7, c6, d5` (the anti-diagonal) and `e5, f6, g7, h8` (the main diagonal);
  for Black they are `a1, b2, c3, d4` and `e4, f3, g2, h1`. (These are exactly
  the promotion squares of the Fairy-Stockfish `sittuyin` variant.)
- A pawn standing on one of its promotion squares may, **as its move**, promote
  to a General — either **in place** (it stays on the square) **or by stepping to
  an adjacent empty diagonal square** (which becomes the General's square).
- Promotion is allowed **only if the player currently has no General** (each side
  may have at most one General at a time — so a promotion can only happen after
  the player's original General has been captured).
- The promotion may not leave the player's **own king in check**.

In the move notation a promotion is written `from>to=G` (with `to == from` for an
in-place promotion), e.g. `4,4>4,4=G` (in place) or `4,4>5,5=G` (onto an adjacent
diagonal). The promotion counts as the player's move for that turn.

> *Interpretation (omitted finer restriction).* Some descriptions add that a
> promotion may not be made if the **new** General would, on appearing, give
> check to / capture / attack an enemy piece. That finer "no aggressive
> promotion" restriction is **not enforced** here — only the well-attested core
> rules (must be on a promotion-diagonal square, the player must have no General,
> and the move must not leave one's own king in check). This is the one
> simplification of the promotion rule and is noted here as a ruleset choice.

> *Interpretation (promotion timing).* Some sources require the pawn to reach the
> promotion square on one turn and promote only on a **later** turn (never the
> turn it arrives). This engine allows the promotion **on any turn the pawn is on
> a promotion square** (including, in principle, the move after it arrives there);
> the "no general yet" requirement already makes promotion rare, and there is no
> separate arrival/promotion bookkeeping.

## Winning, check, and draws

- **Check / Checkmate** — the King may not be left in check. **Checkmating the
  enemy King wins the game.** (Once both sides have deployed.)
- **Stalemate is a draw** — Sittuyin forbids forcing stalemate, and here a side
  with no legal move that is *not* in check is scored as a **draw**.
- **Termination / no-progress** — to guarantee every game ends, this package also
  draws on a position with **insufficient mating material** (e.g. a bare King, or
  a lone General / Elephant / Horse that cannot force mate), a long no-progress
  count, threefold repetition, and a hard ply cap. The traditional Burmese
  **counting** endgame procedure is **omitted** (the same simplification as the
  Makruk package), replaced by these finite-termination rules.

## Letter legend

`K` King (Min-gyi) · `G` General (Sit-ke) · `E`/`e` Elephant (Sin) · `N` Horse
(Myin) · `R` Chariot (Yahta) · `P` Pawn (Ne).

## Sources

Rules verified against Wikipedia's *Sittuyin* article, ancientchess.com,
pychess.org, and the **Fairy-Stockfish** `sittuyin` variant definition (start
FEN, the rook-on-back-rank deployment rule, and the eight promotion squares),
which is the authoritative digital reference used to pin down the exact pawn
formation and promotion geometry.
