# Jul-Gonu (줄고누)

A traditional **Korean** two-player custodial-capture game, one of the many
*gonu* games. *Jul* means "lines" — the board is often just four lines each way
drawn on the ground (hence also *ne-jul-gonu*, "four-line gonu"). Played on a
**4×4** grid of points (coords `c,r`). Player 0 is **Black** (rows count from
Black's side), player 1 is **White**.

## Setup

Each player has **4 pieces**, filling their **back rank**:

- **Player 0 (Black):** the four points of row 0.
- **Player 1 (White):** the four points of row 3.

The middle two rows start empty. Black moves first.

## Moving

On your turn, move **one** piece **one step orthogonally** (never diagonally)
to an adjacent **empty** point. Move notation: `c1,r1>c2,r2`.

**Repetition ban (positional superko):** a move may **not recreate any
position that has already occurred** in the game (same board arrangement with
the same player to move). This is what gives Jul-Gonu its zugzwang/forced-
retreat character — you cannot shuffle forever.

## Capturing (active custodial)

After **your** move, look outward from the moved piece along its **row and its
column**: an **unbroken line of one or two enemy pieces** trapped between your
moved piece and **another friendly piece**, with no gaps, is **captured**
(removed). (On a 4-point line, a run of two is the physical maximum.)

- A **row capture and a column capture can both fire on the same move** — the
  only multi-capture case.
- Capture is **active only** — it must be *created by the capturing player's
  move*:
  - a piece that **moves into** a sandwich between two enemy pieces is **safe**;
  - a piece that moves next to a friendly piece so that *both* end up flanked
    is also safe — the opponent must break and re-form the sandwich on their
    own turn to capture.
- There is **no corner rule** (unlike Hasami Shogi) and captures never involve
  the board edge — the far end of a sandwich must be a friendly **piece**.

## Winning

You win by either:

1. **Reducing the opponent to one piece** (a lone piece can no longer capture,
   so it is no threat) — this includes a line-of-two capture that removes their
   last two at once; or
2. **Stalemating** the opponent: on their turn they have **no legal move**
   (including the case where every move they have is barred by the repetition
   ban).

## Termination backstops

The superko ban already guarantees the game cannot cycle, but as platform
safety nets the game is scored an honest **draw** after **80 consecutive
captureless plies** or **250 total plies**. Both are far beyond the solved
optimal-play length below, so they never deny a forced win.

## Exhaustively analysed: the repetition ban IS the game

The full position graph of this exact ruleset was solved one-time
(`_solve.py` in this package): a forward search enumerated **every reachable
position** (board + side to move, repetition ban set aside — 3,412,738
positions, 21,039,712 move edges), then retrograde win/loss propagation valued
the whole graph, with cycle-bound positions defaulting to draws. The move
generator used was differentially verified identical to this package's.

- Position values: **1,315,354 wins / 807,911 losses** (for the side to move)
  / **1,289,473 cycle-bound draws**.
- **The initial position is a cycle-bound DRAW of the ban-free game**: without
  the no-repetition rule, neither player can force a win — best play dissolves
  into mutual-zugzwang shuffling. This confirms the traditional observation
  (quoted by the Zillions implementer) that Jul-Gonu "is all about parity and
  forced retreat": the anti-repetition rule, not the capture, is the essence.
- With the superko ban, every game IS decisive (positions cannot repeat, so
  play must end in a capture-win or a stalemate) — but the game's exact value
  is **path-dependent** (which side gets squeezed depends on the whole history
  of visited positions) and remains **open**; it is not computable by
  retrograde/memoized methods. The backstop caps score an honest draw if
  over-cautious play drags on.
- Positions the retrograde solve DID resolve keep their exact value under the
  superko ban **provided the game's earlier history stayed inside the
  cycle-bound draw region**: along a minimal-depth winning line the
  distance-to-win strictly decreases every ply, so the line never repeats a
  position and can never collide with the (unresolved) positions already
  visited. If play has already passed through resolved positions, the ban
  could in principle bar a winning line, so the transfer is only guaranteed
  under that proviso (see `_solve.py`).

## Jul-Gonu vs Four Field Kono

Both live on the same 4×4 Korean board but are **different games**:

- **Four Field Kono** starts with the board **completely full** (8 pieces
  each) and captures by the signature **jump over your own adjacent piece**
  onto an enemy beyond it. No custodial capture at all.
- **Jul-Gonu** starts **sparse** (4 pieces each on the back ranks only) and
  captures **custodially** — sandwiching one or two enemy pieces between two
  of yours. No jumping, plus the no-repetition rule.

## Sources

Rules per Wikipedia "Jul-gonu" and J. P. Neto's *World of Abstract Games*
Jul-Gonu page (Wikipedia's primary citation). One wording difference: Wikipedia
says "a move that repeats **the previous position** is not allowed", while
jpneto (and Seo SangHyeon's Zillions implementation notes) state "a move cannot
be made that repeats **any previous position**". This package implements the
stronger jpneto/ZRF formulation (positional superko), documented here as the
local source of truth.
