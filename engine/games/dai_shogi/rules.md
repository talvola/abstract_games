# Dai Shogi (大将棋)

The historical 15×15 Japanese "large shogi" from the Kamakura period
(~1230 AD) — the ancestor of [Chu Shogi](https://en.wikipedia.org/wiki/Chu_shogi),
which later shrank the board and removed its weakest pieces. Each side starts
with 65 pieces of 29 types. **There are no drops**: captured pieces leave the
game. This implementation follows the English Wikipedia article, cross-checked
against The Chess Variant Pages (H.G. Muller) and Muller's HaChu engine;
differences between sources are noted below.

## Goal

Capture **all** of your opponent's royal pieces: the **King**, plus the
**Prince** if their Drunk Elephant has promoted. There is **no check or
checkmate rule** — you may move into, ignore, or stay in "check"; the game
simply ends when the last royal is actually captured. (A player with no legal
move at all — practically unreachable — loses.)

## Moving

Dai Shogi has Chu Shogi's full piece set plus eight weak short-range pieces.
Highlights:

- **Lion** (獅子): may leap directly to **any square within 2** (the 5×5 box,
  jumping over anything), or make **two king steps in one turn** — capturing
  on both (a double capture), capturing an adjacent piece **without moving**
  (*igui*: click the victim, then back to the start square), or stepping out
  and back to **pass the turn** (*jitto*: needs an empty adjacent square).
  In the UI: click the Lion, an adjacent square, then the final square;
  distance-2 leaps are a single second click.
  **Unlike Chu Shogi, there are NO Lion-trading restrictions** — Wikipedia:
  "The capture rules in chu shogi do not apply in dai shogi."
- **Kirin** promotes to a **Lion**; **Phoenix** promotes to a Queen.
- **Horned Falcon** (promoted Dragon Horse): slides in every direction except
  straight forward, where it instead has the **Lion power along that ray**:
  step, jump two, double capture, igui, or pass. The **Soaring Eagle**
  (promoted Dragon King) is the same with the Lion power on **both forward
  diagonals**.
- The eight Dai-only pieces: **Iron General** (one step forward or diagonally
  forward), **Stone General** (diagonally forward only), **Knight** (the
  shogi knight's forward jump), **Angry Boar** (one step orthogonally),
  **Cat Sword** (one step diagonally), **Evil Wolf** (one step forward,
  diagonally forward or sideways), **Violent Ox** (one *or two* squares
  orthogonally — blockable, not a jump), **Flying Dragon** (one or two
  squares diagonally — blockable). All eight promote to **Gold General**.
- The full move diagrams are in the
  [Wikipedia article](https://en.wikipedia.org/wiki/Dai_shogi); this
  implementation reproduces them exactly.

## Promotion

The promotion zone is the far **five** ranks (the enemy camp). Promotion is
**always optional** (a move that could promote offers a "+" choice) and
permanent; a piece promotes at most once — a Rook obtained by promoting a
Gold can never become a Dragon King. A piece may promote when:

- it **enters** the zone (from outside) with any move, or
- it makes a **capture** with either end of the move inside the zone, or
- it left the zone and **re-enters** it.

A quiet move wholly inside the zone gives **no** promotion opportunity.
**Unlike this site's Chu Shogi, a Pawn reaching the last rank gets no extra
promotion chance**: Wikipedia describes that second chance as a Chu-specific
refinement (motivated by Chu's Lion-trading rules, which Dai lacks) and calls
its presence in Dai uncertain; the Dai article instead states plainly that a
pawn / stone / iron general / knight / lance that reaches the far edge
unpromoted is **trapped** (a dead piece). Decline promotion at your own risk.

King, Queen and Lion do not promote. The Drunk Elephant promotes to the
**Prince** — a second royal, shown as `Pr`.

## Draws & endings

- **Fourfold repetition** of the same position with the same player to move
  is a **draw**. (The historical rule made a repeating move simply illegal,
  with modern interpretations placing the burden on the attacker/checker;
  this is simplified to the draw rule, as in this site's Chu Shogi.)
- A hard cap of 800 plies ends the game as a draw.
- Stalemate (no legal move at all) loses for the stalemated player, per The
  Chess Variant Pages' convention; no bare-king rule.

## Pieces & promotions (labels as shown on the board)

| Piece | Label | Promotes to | Label |
|---|---|---|---|
| King (royal) | K | — | |
| Queen (Free King) | Q | — | |
| Lion | Ln | — | |
| Dragon King | DK | Soaring Eagle | SE |
| Dragon Horse | DH | Horned Falcon | HF |
| Rook | R | Dragon King | +R |
| Bishop | B | Dragon Horse | +B |
| Kirin | Kr | Lion | Ln |
| Phoenix | Ph | Queen | Q |
| Drunk Elephant | DE | Prince (royal) | Pr |
| Blind Tiger | BT | Flying Stag | FS |
| Ferocious Leopard | FL | Bishop | +F |
| Gold General | G | Rook | GR |
| Silver General | S | Vertical Mover | +S |
| Copper General | C | Side Mover | +C |
| Vertical Mover | VM | Flying Ox | FO |
| Side Mover | SM | Free Boar | FB |
| Reverse Chariot | RC | Whale | +A |
| Lance | L | White Horse | +L |
| Go-Between | GB | Drunk Elephant | +I |
| Pawn | P | Gold General | +G |
| Iron General | Ir | Gold General | +G |
| Stone General | St | Gold General | +G |
| Knight | Kt | Gold General | +G |
| Angry Boar | AB | Gold General | +G |
| Cat Sword | CS | Gold General | +G |
| Evil Wolf | EW | Gold General | +G |
| Violent Ox | VO | Gold General | +G |
| Flying Dragon | FD | Gold General | +G |

A `+X` label means "promoted X": it moves as the piece named above but can
never promote again. All nine pieces that promote to Gold General become
movement-identical, so they share the `+G` label; `GR` is the Rook obtained
by promoting a Gold (also unable to promote again).

Player 1 (Sente/Black) sits at the bottom and moves first.
