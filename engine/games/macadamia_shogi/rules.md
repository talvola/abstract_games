# Macadamia Shogi

**Macadamia Shogi** is H. G. Muller's factor-two shrink of the historic
Japanese giant **Maka Dai Dai Shogi**. It keeps that game's key ideas — a royal
*Universal Leaper*, multi-capturing *Lion*-type pieces, *hook movers*, and above
all **promotion by capture** — on a manageable **13×13** board with **48 pieces
a side of 26 types** (11 more available through promotion), and **no drops**.

Rules as implemented here. Official source (followed exactly, overrides any
summary): <https://www.chessvariants.com/rules/macadamia-shogi>.

## Board & orientation

- 13×13, files **a–m** (columns 0–12), ranks **1–13** (rows 0–12).
- **Sente (Black)** starts at the bottom and moves toward higher ranks;
  **Gote (White)** is the 180° rotation. Sente moves first.

## Setup

Sente's army (Gote mirrors by rotation):

| Rank | Pieces (files a … m) |
|------|----------------------|
| 1 | Lance, Kirin, Copper, Silver, Gold, **Priest**, **King**, **Pirate**, Gold, Silver, Copper, Phoenix, Lance |
| 2 | – , Dragon, – , **Lion**, – , Tiger, **Elephant**, Tiger, – , **Wolf**, – , Dragon, – |
| 3 | Rook, Left-Chariot, Wrestler, Bishop, Castle, Capricorner, **Queen**, Hook-Mover, Castle, Bishop, Guardian, Right-Chariot, Rook |
| 4 | 13 Pawns (a4 … m4) |
| 5 | – , – , – , Snake (d5), – , – , – , – , – , Snake (j5), – , – , – |

## Pieces & their moves

Moves are given in Betza notation as on the source page (W = one orthogonal
step, F = one diagonal step, R/B = orthogonal/diagonal *slide*, `2`/`3` = a
slide limited to that many squares, A = a (2,2) jump, D = a (2,0) jump; the
prefixes f/b/l/r/s/v pick forward/back/left/right/sideways/vertical directions).

### Unpromoted (in the setup)

| Piece | Betza | Move |
|-------|-------|------|
| Pawn | `fW` | one step forward |
| Snake | `vW` | one step forward or back |
| Copper | `vWfF` | one step forward/back, or a forward diagonal |
| Silver | `FfW` | one diagonal, or one step forward |
| Gold | `WfF` | one orthogonal, or a forward diagonal |
| Tiger | `FsbW` | one diagonal, sideways or backward (not straight forward) |
| Phoenix | `WA` | one orthogonal step, or a (2,2) diagonal **jump** |
| Kirin | `FD` | one diagonal step, or a (2,0) orthogonal **jump** |
| Pirate | `lbfFrW` | any diagonal step, or one step **right** |
| Priest | `rbfFlW` | any diagonal step, or one step **left** |
| Elephant | `FfsW` | any diagonal, forward or sideways (Drunk Elephant) |
| King | `K` | one step any direction (**royal**) |
| Lance | `fR` | slides forward |
| Dragon | `F2` | slides up to 2 diagonally |
| Guardian | `W3fF` | slides up to 3 orthogonally, or a forward diagonal step |
| Wrestler | `F3sW` | slides up to 3 diagonally, or one step sideways |
| Left Chariot | `fRbWflbrB` | forward-rook slide, back step, and the fwd-left / back-right diagonal slides |
| Right Chariot | `fRbWfrblB` | mirror of the Left Chariot |
| Bishop | `B` | slides diagonally |
| Rook | `R` | slides orthogonally |
| Capricorner | `BmasB` | **hook bishop**: slides diagonally and may make one 90° turn |
| Hook Mover | `RmasR` | **hook rook**: slides orthogonally and may make one 90° turn |
| Wolf (Lion Dog) | triple mover | see below |
| Castle | `RF` | slides orthogonally, one diagonal step (Dragon-King) |
| Queen | `Q` | slides any direction |
| Lion | double mover | see below |

### The Lion (piece "Lion")

A **double mover**: up to two King-steps per turn, changing direction between
them; the first step may be a **jump**. So it can jump to any square in the 5×5
area around it; capture an adjacent piece and move on ("hit-and-run"), stay
("igui") or take a second adjacent piece ("double capture"); or pass its turn
(via an empty neighbour). Up to **2** captures in one turn.

### The Wolf (Lion Dog)

A **triple mover**: up to three King-steps along **one** ray, and it may
**jump**. It can land 1, 2 or 3 squares away in any of the 8 directions
(jumping over anything in between), **annihilating** up to **3** enemy pieces it
passes over or lands on (any subset of the squares along that ray), capture an
adjacent piece without moving (igui), or pass its turn.

### Hook movers

The **Hook Mover** is a Rook and the **Capricorner** a Bishop that may make one
90° turn mid-slide (at an empty square, no jumping). On an empty board the Hook
Mover reaches any square, the Capricorner any square of its own colour.

### The Emperor & Prince

A **King promotes to an Emperor**, an all-powerful **Universal Leaper** that may
move to (or capture on) *any* square of the board. A **Drunk Elephant promotes
to a King** (called a Prince), so a player can have **two royal pieces**.

## Promotion — **by capture**

There is **no promotion zone**. A piece may promote **only at the end of a turn
in which it captured** something. Each type has one **fixed** promoted form.

- Promotion is **optional**, **except it is mandatory when the captured piece
  was itself already promoted** (a promoted "Gold" is therefore relatively
  immune to capture — anything taking it is forced to promote).
- **Saint / Ghost override.** When a **non-royal** piece captures a **Priest or
  Saint** it becomes a **Saint**; when it captures a **Pirate or Ghost** it
  becomes a **Ghost** — forced, even if it was already promoted (this is why the
  Saint and Ghost, the two strongest pieces, virtually never leave play). The
  **King, Emperor, Elephant and Prince never** become Saint/Ghost — they keep
  their own royal promotion. **Queen and Castle never promote** at all *except*
  under this Saint/Ghost override.

Promoted forms:

| Piece | Promotes to | Move of the promoted form |
|-------|-------------|---------------------------|
| King | Emperor | Universal Leaper |
| Elephant | King (Prince) | one step any direction (royal) |
| Priest | Saint | Wolf + Queen |
| Pirate | Ghost | Lion + Queen |
| Lion | Berserker | Lion + 3-square slides |
| Kirin | Unicorn | `sRvW2F3` |
| Phoenix | Golden Bird | `vRsW2F3` |
| Tiger | Running Tiger | `BbsR` |
| Gold | Running Gold | `RfB` |
| Silver | Running Silver | `BfR` |
| Copper | Running Copper | `vRfB` |
| Snake | Sliding Snake | `vR` |
| Pawn, Lance, Dragon, Guardian, Wrestler, L/R Chariot, Bishop, Rook, Capricorner, Hook Mover, Wolf | **Gold** | `WfF` |
| Queen, Castle | *do not promote* | |

## Winning

The game is won the moment your opponent has **no royal piece left**. Royal
pieces are the **King**, the **Emperor** and the **Prince** (promoted Elephant).
Because a player can hold two royals, capturing one King while a Prince survives
does **not** end the game.

## Repetition & draws

Repeating a position (same side to move) four times, or reaching a hard ply cap,
is scored as an honest **draw**.

## Interpretations & simplifications

The following deviations from the letter of the source are documented for
faithfulness:

- **Repetition.** The source's *intent-based* perpetual rules (perpetual checker
  loses, perpetual chaser loses, otherwise draw) are simplified to a
  **fourfold-repetition draw** plus a ply cap. This preserves termination and
  the "nothing can be achieved → draw" spirit without move-intent bookkeeping.
- **Emperor vs. protected royals.** The source forbids an Emperor from capturing
  a *protected* royal when that would expose it (so two Emperors cannot simply
  trade). This engine implements the Emperor as a plain Universal Leaper and
  does **not** enforce that protected-royal restriction (a rare two-Emperor edge
  case).
- **No check / pseudo-legal play.** As in the source there is no checkmate: a
  side may move into or leave a royal attacked; the game is decided purely by
  royals leaving the board. A side with **no legal move loses** (this only
  matters in constructed endgames — it guarantees termination).
- **Saint/Ghost double-capture tie-break.** When a Lion or Wolf captures *both*
  a Priest/Saint **and** a Pirate/Ghost in one turn, the source promotes to the
  one on the destination square (Lion) or the farthest (Wolf). This engine
  applies that preference (destination square first, else the Saint), a rare
  case.

## Oracle note

The variant is played by **HaChu 0.21** (`variant macadamia-shogi`), which was
used as a differential oracle during development: the exact setup, the board
orientation, and every initial legal move were confirmed against it, and across
extended real play HaChu never rejected a move this engine generates. The deeper
mechanics are anchored against the full Betza + prose rules above (HaChu's
`setboard`/search crash on this variant, so they could not be scripted directly).
