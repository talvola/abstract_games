# Senet

**Senet** is one of the oldest known board games, played in ancient Egypt from
roughly **3100 BCE**. No record of its rules survives, so all modern rulesets are
**reconstructions** from tomb paintings, board inscriptions and fragmentary
texts. This implementation follows the widely-used reconstruction of
**Timothy Kendall** (Kendall 1978/2007), as summarised on
[Wikipedia "Senet"](https://en.wikipedia.org/wiki/Senet). Every rule below is a
deliberate, documented choice — other reconstructions differ.

## The board and path

Thirty "houses" arranged in a **3 × 10 grid**, traversed in a
**boustrophedon (S-shaped) path**:

1. **Houses 1–10** — the **top** row, left to right.
2. **Houses 11–20** — the **middle** row, running **back** right to left (house
   11 sits under house 10, house 20 under house 1).
3. **Houses 21–30** — the **bottom** row, left to right, off the end.

A linear track index 0–29 maps to a grid cell `(col,row)`: the top and bottom
rows run left→right, the middle row runs right→left, so the path snakes.

## Pawns and starting position

Each player has **5 pawns** (Kendall's original text used 7; 5 is the common
playable choice, used here and documented). They start **interleaved on
houses 1–10**:

- **White** on houses 1, 3, 5, 7, 9.
- **Black** on houses 2, 4, 6, 8, 10.

## The throw sticks

You throw **four flat two-sided sticks** (one side white/marked, one black). The
throw is the **number of white sides up**, with the special case that
**all-black counts as 5**:

| White sides up | 4 | 3 | 2 | 1 | 0 (all black) |
|---|---|---|---|---|---|
| **Throw** | 4 | 3 | 2 | 1 | **5** |
| **Probability** | 1/16 | 4/16 | 6/16 | 4/16 | 1/16 |

So the throw is always **1–5**. A throw of **1, 4 or 5 grants another throw** (an
extra turn for the same player); a throw of 2 or 3 ends the turn. (A forced pass
does not grant the bonus, since no pawn moved.)

The throw is rolled and **stored in the game state**, so it is always known when
the move is chosen (the platform's "randomness without a chance node" pattern).

## Movement

Advance **one** of your pawns forward by the throw, subject to:

- **No own pawn** — you may not land on a square already holding your own pawn.
- **Swap** — landing on an opponent's **single, unprotected** pawn **swaps** the
  two: your pawn takes the square, the opponent's pawn goes **back** to the
  square you came from.
- **Protection (pairs)** — a pawn is **protected** if it has a friendly pawn on
  an **immediately adjacent** track square (a pair). A protected pawn cannot be
  landed on or swapped.
- **Blockade (three in a row)** — **three or more** consecutive friendly pawns
  form an **impassable block**: an enemy pawn may not move onto or **past** that
  run.

If you have **no legal move** for your throw, your turn **passes**.

## Special houses

- **House 15 — House of Rebirth** (the Ankh): a plain house in play, but the
  square that pawns are sent back to from the House of Water.
- **House 26 — House of Happiness**: a **mandatory stop**. A pawn may **not pass**
  house 26 — every pawn must land **exactly** on it before continuing toward the
  exit. (A throw that would overshoot house 26 cannot move that pawn.)
- **House 27 — House of Water**: a pawn that lands here is **immediately sent back
  to house 15** (House of Rebirth), or — if house 15 is occupied — to the first
  empty house **before** it.
- **House 28 — House of the Three Truths**: a pawn here bears off only on an
  **exact throw of 3**.
- **House 29 — House of Re-Atoum**: a pawn here bears off only on an **exact throw
  of 2**.
- **House 30 — House of Horus**: a pawn here bears off on a **throw of 1**.

A pawn between house 26 and the exit must therefore land on houses 28, 29 or 30
and leave on the exact throw for that house; the board cannot be overshot.

## Bearing off and winning

Pawns leave the board from houses 28/29/30 on the exact throws above. The first
player to **bear all 5 pawns off** the board **wins**. (A hard ply cap awards the
win to the leader as a safety net; in practice the race always terminates.)

## Move encoding & UI

Moves are `from>to` cell paths, e.g. `0,0>2,0`. Bearing off uses the destination
token `off`, e.g. `7,2>off`. When the throw yields no legal move, the only move
is the **`pass`** action button. The current throw, whether it grants an extra
turn, and each side's borne-off count are shown in the caption — the throw is part
of the position, so there is no separate dice prompt. Special houses are tinted on
the board.

## Notes / interpretations (Senet is reconstructed)

- **5 pawns** (Kendall's 1978 text used 7; 5 is the common modern choice).
- The **starting layout** interleaves the two colours on houses 1–10 (the most
  commonly depicted opening).
- **Extra turn on 1/4/5** follows the common throw-stick convention; the precise
  bonus rule is not attested and is a documented choice.
- **Pair-protection** (a single pawn is swappable; an adjacent pair is safe) and
  the **three-in-a-row block** follow Kendall; some reconstructions protect only
  via the three-in-a-row rule.
- **House of Happiness** is treated as a strict mandatory stop (no passing); the
  exact-throw exits at houses 28/29/30 follow Kendall.
