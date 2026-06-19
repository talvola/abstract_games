---
name: gamecourier-to-platform
description: Convert a Game Courier / chessvariants.com chess variant into an Abstract Games Platform game module. Use when the user wants to port/add a game from Game Courier, gives a chessvariants.com play.php?game=…&settings=… URL, names a variant "from Game Courier" / "from chessvariants", or references a Game Courier preset/settings file.
---

# Game Courier (chessvariants.com) → Abstract Games Platform

Port a Game Courier preset into a platform game module. The platform's game
contract is the target — **read `engine/SPEC.md` first** (the authority on the
`Game` interface, move notation, board types, options) and, for chess-family
games, the **`agp.chesslike.ChessLike`** docstring (the fast path — a variant is
usually ~40 lines). This skill is the *procedure* for translating a Game Courier
preset into that contract. Iterate on it as you port more games.

**Key mental model:** Game Courier itself knows *no* game's rules. A preset is two
separable things: (1) a **declarative settings file** (board geometry + starting
position + piece graphics + addressing) that is *mechanically parseable*, and
(2) optional **imperative GAME Code** (the rule enforcement) that is *not*. You
read the rules from the human rules page + the declarative settings, and only mine
the GAME Code for the slider/leaper movement offsets. Most chess variants map onto
`ChessLike`; the rest fall back to a generic `Game` or the freeform path (§7).

## 1. Resolve and fetch the game

A preset is addressed as `play.php?game=<Name>&settings=<basename>`. From that (or
from a plain "import N Chess from Game Courier") you need three artifacts:

- **The settings file** (declarative game definition). Raw source is retrievable at
  **`/play/pbmsettings/showsource.php?game=<Name>&settings=<basename>`** — this is
  the import entry point. It's a PHP file of `$default['key'] = <<<'NOW' … NOW;`
  assignments.
- **The rules page** — the human prose rules (clearer than reverse-engineering GAME
  Code). Linked from the preset page's "Related" menu / the settings `rulesurl`
  field; usually `chessvariants.com/.../<game>.html`.
- **The preset play page** itself — confirms board size, piece labels, and whether
  rules are enforced ("Rules enforced. Legal moves displayed." vs. "No rules
  enforced.").

**chessvariants.com 403s automated fetchers** (`WebFetch`/curl). Use the
**`pinchtab`** skill — Erik is logged in there — to open the pages and scrape text,
or ask the user to save the HTML (as they did under `research/`, gitignored). If
the user pasted a URL, parse `game=` / `settings=` out of it (URL-decode `+`→space,
`%3D`→`=`). If you can't reach a page, ask the user to paste the settings source +
rules text.

## 2. Map the settings file → the contract

`$default[...]` keys (the Edit-mode fields), and where each goes:

| Settings key | Meaning | Platform |
|---|---|---|
| `game` | display name | manifest `name`; the id (lowercase, spaces→`_`) ≈ our `uid` |
| `code` | **extended FEN** — board + starting position | board geometry + `setup_board()` (see §3) |
| `cols` | number of files (board width) | `WIDTH` / RenderSpec width |
| `files` / `ranks` | space-separated coordinate **labels** | cell-id mapping + `describe_move` notation |
| `board` | checker **pattern** (digits pick colors) | ignore — cosmetic (our renderer colors itself) |
| `shape` | `Square Cells` / `…Hexagonal` / `Circular` / `Custom Grid` / `Custom Board` | RenderSpec board `type` (see §3) |
| `sides` | side names, first moves first | seat order — **first side = `to_move` 0 (White)** |
| `set` / inline JSON custom set | piece label → image | ignore — we have our own renderer |
| `rulesurl` | link to the rules webpage | manifest `bgg_url` (the "official source" link) |
| `rules` | brief in-preset HTML rules | seed for `rules.md` (but prefer the full rules page) |
| Pre-Game / Pre-Move{1,2} / Post-Move{1,2} / Post-Game{1,2} | **GAME Code** rule enforcement | mine for movement offsets only (see §4); not transpiled |

## 3. Decode the board + starting position (extended FEN)

`code` is an extended FEN, read **left-to-right, top-to-bottom from White's view**
(top-left = file 0, highest rank; down to rank 0). a1 = (col 0, row 0), like our
board. Token rules:

- **A base-10 number** = that many consecutive **empty** squares (`8` = 8 empties;
  `32` = four empty 8-wide ranks).
- **A single letter** `[A-Za-z]` = a piece; **uppercase = White (player 0)**,
  **lowercase = Black (player 1)**.
- **`{NB}`** (braces) = a multi-character piece label (fairy pieces).
- **`/`** = end of rank. If it comes *before* the rank is naturally full, it pads
  the rest of the rank with `-` (non-cells).
- **`-`** = a **non-cell** (hole / padding for non-rectangular boards) — *not* an
  empty playable square.
- **`*`** = fill the rest of the rank with **empty** squares (`****` is not the same
  as `/*/*/*/*`).

Equivalent encodings of the chess start (all valid): `rnbqkbnrpppppppp32PPPPPPPPRNBQKBNR`
≡ `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR` ≡ `rnbqkbnr/pppppppp/****/PPPPPPPP/RNBQKBNR`.

Map `shape` → RenderSpec board `type`: `Square Cells` → `square`; the two
`Hexagonal` shapes → `hex` (work out `shape`/`size`; CV hex uses parallelogram
file/rank coords — see `games/hex`); `Circular` / `Custom Grid` / `Custom Board` →
our generic **`polygons`** type (or **pause and ask** — exotic topology is real
work). Sanity-check the parsed cell count and starting layout against the preset
play page screenshot before writing code.

**Cell ids must be numeric** `"col,row"` (square) / `"q,r"` (hex) — the web Board
renderer only treats a move as click-to-move when *every* `>`-segment matches
`^-?\d+,-?\d+$`. Keep the CV `files`/`ranks` labels (e.g. `a1`, `e4`) only for
`describe_move`. (Same rule as the Zillions skill.)

## 4. Translate piece movement

The rules page prose is the primary source — read how each piece moves, then
*confirm the offsets* against the GAME Code if present. In GAME Code, a piece's
move is a one-line `def <Label> …` using these primitives (`from to Δfile Δrank`):

- **`checkleap from to Δf Δr`** — direct, unblockable **leaper**, symmetric over all
  sign/▸direction permutations of `(Δf,Δr)`. `checkleap … 1 2` = knight; `1 1` =
  ferz (one-step diagonal); `1 0` = wazir (one-step orthogonal).
- **`checkride from to Δf Δr`** — **rider/slider** (repeat the step over empty
  squares), symmetric. `checkride … 1 0` = rook; `1 1` = bishop.
- compound pieces are `or`-chains: `def Q fn B #0 #1 or fn R #0 #1` (queen),
  `def K checkleap #0 #1 1 0 or checkleap #0 #1 1 1` (king).
- **`checkaleap` / `checkaride`** — *asymmetric* (direction matters; `+Δr` =
  forward from White's view) — used for pawns and other divergent/directional moves.

**These `(Δfile,Δrank)` pairs ARE our `(slide_dirs, leap_offsets)`.** A piece that
is an `or`-chain of `checkleap`/`checkride` translates mechanically into a
`ChessLike` `PIECES` entry:

```python
from agp.chesslike import ORTHO, DIAG, ALL8, KNIGHT   # the standard offset sets
PIECES = {
    "R": (ORTHO, []),          # checkride 1 0
    "B": (DIAG,  []),          # checkride 1 1
    "Q": (ALL8,  []),          # rook or bishop
    "N": ([], KNIGHT),         # checkleap 1 2
    "K": ([], ALL8),           # king = one-step all directions
    "M": (ORTHO, KNIGHT),      # Marshall = rook + knight (compound)
    "C": (DIAG,  KNIGHT),      # Cardinal = bishop + knight
}
```
For a leaper with an unusual `(Δf,Δr)`, the offsets are the 8 sign/swap
permutations of that pair (4 if `Δf==Δr` or one is 0). Games authored in **Betza /
"funny" notation** (via the fairychess include or the GAME-Code wizard) map the
same way for the rider/leaper subset (atoms `W`=wazir, `F`=ferz, `D`=dabbaba,
`N`=knight, `A`=alfil, `R/B/Q`=sliders, …).

**What does NOT fit `(slide_dirs, leap_offsets)`** — flag for a generic `Game` or
ask the user:
- **Pawns** — divergent (move ≠ capture), double-step, en passant, promotion. Don't
  put them in `PIECES`; use the `PAWN` strategy (`StandardPawn` / `BerolinaPawn`)
  + `PROMOTION` (`LastRankPromotion` / `GrandPromotion`).
- **Castling / king-swaps** — `StandardCastling` / `NoCastling`, or custom.
- **Hoppers / Cannons / Grasshoppers** (`checkhop`/`checkgrasshop`) — movement
  depends on a screen piece in the path.
- **Locust / long-leaper capture** (`checklongleap`) — captured square ≠ destination.
- **Bent / lame leapers** (Xiangqi horse/elephant, `checkatwostep`/`checkpath`) —
  intermediate-square dependency.
- **Drops, swaps, multi-move turns, moving the opponent's pieces** — turn/action
  structure, not piece geometry.

## 5. Implement (chess-family fast path)

If the game is a rectangular-board chess variant with a royal king, subclass
`ChessLike` — usually ~40 lines. Declare `WIDTH`/`HEIGHT`, `PIECES`, `HEAVY`
(letters that count as mating material), the three strategies (`PAWN`,
`PROMOTION`, `CASTLING`), and `setup_board()`. Model after
`engine/games/{chess,grand_chess,berolina,los_alamos_chess}`. Example skeleton:

```python
from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

class MyVariant(ChessLike):
    uid = "my_variant"          # match manifest uid (don't invent a different one)
    name = "My Variant"
    WIDTH = HEIGHT = 8
    PIECES = { "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
               "N": ([], KNIGHT), "K": ([], ALL8) }
    HEAVY = ("P", "R", "Q")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(["Q", "R", "B", "N"])
    CASTLING = StandardCastling()

    def setup_board(self) -> dict:
        b = {}
        # place pieces: b[(col,row)] = (WHITE|BLACK, "LETTER")
        return b
```

For **non-chess** variants (Xiangqi-like, hoppers, drops, exotic boards), write a
plain `agp.game.Game` subclass against `SPEC.md` instead, with hand-written
`legal_moves`/`apply_move`. Either way also write `manifest.json` (set `category`
"Chess & chess-like" for chess variants, `bgg_url` to the rules page,
variants/sizes as `options`) and a **`rules.md`** one-pager of the rules *as
implemented* (note any interpretation you made where the source was ambiguous —
e.g. stalemate result, promotion choices, repetition/50-move handling).

## 6. Validate and wire

```
cd engine && PYTHONPATH=. python3 -m agp.cli validate games/<uid>   # must print RESULT: OK
PYTHONPATH=. python3 -m agp.cli render   games/<uid> --moves 8       # eyeball board + moves
PYTHONPATH=. python3 -m agp.cli playtest games/<uid> --bot           # MCTS self-play sanity
```
- **Guarantee termination** — if random play could loop, add a no-progress /
  ply-cap draw (`ChessLike` already has `PLY_CAP` + halfmove/repetition handling).
- **Perft check (chess variants):** verify leaf-node counts from the opening
  against a known/independently-derived value — the highest-confidence correctness
  test for move generation. See `tests/test_games.py::test_full_chess_perft_and_special_moves`
  (`perft(s0,1)==20`, `…2)==400`, `…3)==8902` for standard chess); add an analogous
  test for the variant.
- Restart the backend (the registry caches game code at startup) and screenshot the
  board with `pinchtab` to verify rendering. Add a conformance test to `engine/tests/`.

## 7. The freeform / unenforced fallback

Game Courier hosts hundreds of games precisely because a preset can be *unenforced*
(board + pieces + honor-system moves, no rule code). If the platform has a
**freeform mode** (board geometry + piece set + initial setup, no
`legal_moves`/`is_terminal` enforcement — see PLATFORM_PLAN §8 / the freeform
spike), a settings file alone is enough: parse `code`/`cols`/`shape`/`files`/`ranks`
(§2–3), skip movement entirely, and ship. This is the cheap on-ramp for the long
tail; graduate popular ones to fully-enforced `ChessLike`/`Game` modules later. If
freeform mode does not yet exist, don't fake it — port to a strict module or pause.

## When to pause and ask

Stop and confirm with the user if the preset uses: randomness/dice or cards;
hidden information; piece **drops** from hand (Shogi-like); **multi-move** turns or
moving the opponent's pieces; **hoppers/locust/bent-leaper** movement; an exotic
**board topology** (circular / custom pixel-mapped / 3-D); or win conditions you
can't cleanly express. Also confirm the **stalemate result** and any draw rules,
which CV presets vary. Better to ask than ship a subtly-wrong port. Respect
chessvariants.com's content ownership: credit the preset author + link the source,
import for personal/playtest use, and don't bulk-scrape.
