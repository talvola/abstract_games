# Micro Shogi

Micro Shogi (マイクロ将棋) is a tiny Shogi variant played on a **4×5 board**
(4 files wide, 5 ranks deep) with just **five pieces per side**. Its signature
rule replaces Shogi's promotion zone entirely: **a piece promotes the instant it
captures.**

## Board and pieces

Each player has: **King, Bishop, Gold General, Silver General, and one Pawn.**

Every non-royal piece is a two-faced token. Its *base* face and its *promoted*
face are:

| Base face | Promoted face | Base moves like | Promoted moves like |
|-----------|---------------|-----------------|---------------------|
| Silver (S) | Lance (L)  | Silver general  | Lance (slides straight forward) |
| Gold (G)   | Rook (R)   | Gold general    | Rook (slides orthogonally) |
| Bishop (B) | Tokin (T)  | Bishop (slides diagonally) | Tokin — moves as a Gold general |
| Pawn (P)   | Knight (N) | Pawn (one step forward) | Knight (jumps 2 forward + 1 sideways) |
| King (K)   | *(none)*   | one step any direction | — |

All pieces move exactly like their standard Shogi equivalents. The **King never
promotes**.

## Starting position

Each player's back rank, read from that player's own left, is **Silver, Gold,
Bishop, King (S G B K)**, with the **Pawn on the second rank directly in front of
the King**. The two armies face each other as a 180° rotation, so the Kings sit
in diagonally opposite corners.

In this engine's coordinates (Black at the bottom, files 0–3, ranks 0–4):

- **Black (Sente):** S`0,0` G`1,0` B`2,0` K`3,0`, Pawn `3,1`.
- **White (Gote):** K`0,4` B`1,4` G`2,4` S`3,4`, Pawn `0,3`.

Black moves first.

## Promotion — the signature rule

There is **no promotion zone.** Instead:

- **A piece flips to its other face whenever it makes a capture**, and this is
  **mandatory** and automatic. A Silver that captures becomes a Lance, a Gold
  becomes a Rook, a Bishop becomes a Tokin, a Pawn becomes a Knight.
- **A promoted piece flips back** to its base face when *it* captures. So a token
  oscillates between its two roles over the game, driven purely by captures
  (Lance→Silver, Rook→Gold, Tokin→Bishop, Knight→Pawn on a capture).
- A **non-capturing move never changes a piece's face.**
- The King never flips.

A piece moves as its *current* face; if that move captures, it then flips on the
destination square. Check, checkmate and king-safety are judged on the position
*after* the capture-flip.

### Trapped pieces

Because promotion only happens by capturing, a piece can get stuck: an
unpromoted Pawn or Lance on the last rank, or a Knight on the last two ranks, has
no legal move and is simply **trapped** until it is captured. This is legal — the
piece just sits there.

## Drops

Captured pieces switch sides and go into the capturer's hand, as in standard
Shogi. On a later turn you may drop a piece from hand onto any **empty** square.

Micro Shogi imposes **no drop restrictions**:

- A dropped piece may show **either face** (your choice) — e.g. the pawn/knight
  token can be dropped as a Pawn *or* as a Knight.
- **No nifu** — you may have two (or more) Pawns on the same file.
- **No last-rank ban** and **no drop-mate ban** — you may drop a Pawn on the last
  rank (it is then trapped) and a Pawn drop may deliver checkmate.

## Winning

Checkmate the opponent's King, exactly as in standard Shogi. The game is drawn
if the position repeats four times or the hard ply cap (300) is reached — a
safeguard so every game terminates.

## Move notation (this platform)

- Board move: `fromfile,fromrank>tofile,torank`, e.g. `2,0>1,1`. No promotion
  suffix is ever used — the capture-flip is automatic.
- Drop: `Face@file,rank`, e.g. `L@2,2` drops the silver/lance token as a Lance,
  `N@1,2` drops the pawn/knight token as a Knight. The reserve tray shows both
  faces of each held token; click the face you want to drop.

## Deviations / interpretations

- Faithful to the rules as described on Wikipedia's *Micro shogi* article: 4×5
  board, S/G/B/K + Pawn armies, promote-on-capture (mandatory), demote when the
  promoted face captures, and unrestricted either-face drops.
- The hand is keyed by the *pair* (one physical token = both faces), matching the
  "drop with either side up" rule; the tray simply exposes both faces.
