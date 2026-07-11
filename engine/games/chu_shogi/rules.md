# Chu Shogi (中将棋)

The classic 12×12 Japanese "middle shogi" (14th century) — the flagship large
shogi variant, famous for its double-moving **Lion**. Each side starts with 46
pieces of 21 types. **There are no drops**: captured pieces leave the game.
This implementation follows the ruleset of the English Wikipedia article
(the ruleset of HaChu, the reference engine); differences between sources are
noted below.

## Goal

Capture **all** of your opponent's royal pieces: the **King**, plus the
**Prince** if their Drunk Elephant has promoted. There is **no check or
checkmate rule** — you may move into, ignore, or stay in "check"; the game
simply ends when the last royal is actually captured. (A player with no legal
move at all — practically unreachable — loses.)

## Moving

Pieces are steppers (one square), rangers (slide any distance), or jumpers
(leap over anything to a fixed square). Highlights:

- **Lion** (獅子): may leap directly to **any square within 2** (the 5×5 box,
  jumping over anything), or make **two king steps in one turn** — capturing
  on both (a double capture), capturing an adjacent piece **without moving**
  (*igui*: click the victim, then back to the start square), or stepping out
  and back to **pass the turn** (*jitto*: needs an empty adjacent square).
  In the UI: click the Lion, an adjacent square, then the final square;
  distance-2 leaps are a single second click.
- **Kirin** promotes to a **Lion** and is then a Lion in every respect
  (including the Lion-trading rules below). **Phoenix** promotes to a Queen.
- **Horned Falcon** (promoted Dragon Horse): slides in every direction except
  straight forward, where it instead has the **Lion power along that ray**:
  step, jump two, double capture, igui, or pass. The **Soaring Eagle**
  (promoted Dragon King) is the same with the Lion power on **both forward
  diagonals** (each two-step stays on its diagonal).
- The full 28 move diagrams are in the
  [Wikipedia article](https://en.wikipedia.org/wiki/Chu_shogi); this
  implementation reproduces them exactly.

## The Lion-trading rules (as implemented)

To keep the Lions on the board, capturing one is restricted:

1. **Protected-Lion rule.** A Lion may not capture an enemy Lion standing on a
   **non-adjacent** square (a distance-2 leap or the far end of a double move)
   if the capturing Lion **could be recaptured in the resulting position** —
   evaluated *after* the move, so an X-ray "hidden protector" through the
   vacated square counts, and capturing the sole protector en route makes the
   capture legal. Exception (*tsukegui*): the capture is always legal if the
   double move also captures another piece that is **not an unpromoted Pawn or
   Go-Between**. Capturing an **adjacent** enemy Lion is always legal.
   Hypothetical recaptures are tested naively (the Lion rules are not applied
   recursively — the Wikipedia/HaChu reading of the historic sources).
2. **Counterstrike rule.** When a **non-Lion captures a Lion**, the opponent
   may not reply *on the very next move* by capturing a Lion with a non-Lion —
   except on the **same square** as the first capture (so a Kirin that
   promoted to Lion while capturing one may be shot at once). A Lion may
   always recapture (subject to rule 1). Falcon/Eagle "hit-and-run" and igui
   captures count as captures for both sides of this rule.

**Documented interpretation choices** (historically ambiguous corners):

- Wikipedia's example V (a distance-2 Lion protected only by a pawn that the
  capturing Lion eats en route): **legal** here, per the post-move reading
  (The Chess Variant Pages); the Japanese Chu Shogi Association evaluates
  protection *before* the move and rules it illegal.
- The **Okazaki variant** (counterstrike allowed against an *unprotected*
  Lion) is **not implemented** — the traditional rule is used.

## Promotion

The promotion zone is the far **four** ranks. Promotion is **always optional**
(a move that could promote offers a "+" choice) and permanent; a piece
promotes at most once — a Rook obtained by promoting a Gold can never become a
Dragon King. A piece may promote when:

- it **enters** the zone (from outside) with any move, or
- it makes a **capture** with either end of the move inside the zone, or
- it left the zone and **re-enters** it.

A quiet move wholly inside the zone gives **no** promotion opportunity (the
Japanese/JCSA rule, per Wikipedia — not modern shogi's rule). Exception: a
**Pawn** reaching the last rank gets one extra non-capture chance; declined,
it stays as an immobile "dead piece" (as does a Lance run to the last rank —
legal, if pointless). The Okazaki last-rank rule for the Go-Between is not
implemented (the JCSA repealed it).

King, Queen and Lion do not promote. The Drunk Elephant promotes to the
**Prince** — a second royal, shown as `Pr`.

## Draws & endings

- **Fourfold repetition** of the same position with the same player to move
  (and the same counterstrike status) is a **draw**. (The JCSA's asymmetric
  repetition rules — perpetual-check and pass-loop losses — are simplified to
  this draw rule.)
- A hard cap of 600 plies ends the game as a draw (long even for chu).
- The JCSA **bare-king rule** (a lone King loses against remaining material)
  is **not** implemented; win by capturing the royals.

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
| Gold General | G | Rook | +G |
| Silver General | S | Vertical Mover | +S |
| Copper General | C | Side Mover | +C |
| Vertical Mover | VM | Flying Ox | FO |
| Side Mover | SM | Free Boar | FB |
| Reverse Chariot | RC | Whale | +A |
| Lance | L | White Horse | +L |
| Go-Between | GB | Drunk Elephant | +I |
| Pawn | P | Gold General | +P |

A `+X` label means "promoted X": it moves as the piece named above but can
never promote again.

Player 1 (Sente/Black) sits at the bottom and moves first.
