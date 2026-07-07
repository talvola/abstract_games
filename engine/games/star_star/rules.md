# *Star (Star-Star)

**Designer:** Ea Ea (formerly **Craige Schensted**), with Charles Titus and
collaborators; published by **Kadon Enterprises** (© 2004). *Star is the deepest
of Ea Ea's celebrated connection series (Y, Poly-Y, Star, *Star).

This is a **distinct game** from the two look-alikes already in the library:

- Our **`star`** is Schensted's *earlier* (1983) game — a hexagon whose six sides
  alternate in length, scored by how many non-playable border cells a group
  *touches*. *Star is a later, different game with **edge-cell ownership** and a
  **star-count award**.
- Our **`starweb`** / **`superstar`** are **Christian Freeling's** games on a
  six-fold hex board. *Star's board is Ea Ea's own **five-sided** *STAR board.

## The board

The **five-sided *STAR tournament board** has **five sectors** (the rulebook
labels them `*`, `S`, `T`, `A`, `R`; here sector index 0–4). Each sector is a
triangular fan of **rings 1–10** counting outward from the centre; ring *r* holds
exactly *r* cells (offsets `0 … r-1`). So each sector has 1+2+…+10 = **55 cells**
and the whole board has **275 cells**.

- **Edge cells** ("pericells") = the outermost ring (ring 10): 10 per sector =
  **50 edge cells**.
- **Corner cells** ("quarks") = ring 10, offset 0, one per sector = **5 corners**
  (the star's points).
- **The bridge:** a star-shaped region at the very centre. **No stone is ever
  placed on the bridge**, but it **conducts a connection for both players** — the
  five innermost (ring-1) cells are all linked to one another through it.

A cell is addressed `sector,ring,offset`, e.g. `0,10,0` is a corner and `0,10,2`
is an edge cell. Clicking an empty cell places a stone there.

*Board fidelity note.* The rulebook's board is a hand-drawn irregular
("mudcrack") tiling that no regular hex grid reproduces exactly. This package
builds the faithful **topological** graph: each sector is a triangular-hex
("Y") array, adjacent sectors join along their shared ray, and the bridge links
the five centre cells. This exactly reproduces the counts (275 / 50 / 5) and the
scoring invariant below. The on-screen board is a pentagonal-star rendering of
that graph, not a pixel copy of the printed board.

## Play

- **White (player 0) moves first.**
- On your turn, place one stone of your colour on any empty cell (the bridge is
  not a cell, so it is automatically off-limits). Stones never move or get
  captured.
- **Passing is legal.** Two successive passes end the game. (Safety nets: a full
  board or a hard ply cap also end it.)

## Scoring

- A **star** is a connected group of one colour containing **two or more edge
  cells**. (A lone stone — even on a corner — is *not* a star.)
- A star **owns** every edge cell it contains, **plus** every edge cell it
  **surrounds** that is not already owned by another star. Surrounding is
  resolved by the reduction the rulebook and Wikipedia describe: groups holding
  fewer than two edge cells are set aside, and any empty region then bordered by
  **exactly one colour's** stars belongs to that colour (a region touching both
  colours is neutral).
- **1 point** per edge cell owned.
- **+1 point** to the player owning **three or more** of the five corner cells.
- **The award:** count each player's number of separate stars. The player with
  **fewer** stars has their score **raised by twice the difference**; the other
  player's score is **lowered by the same amount**. (This strongly rewards
  connecting your stars into one big star.)

**Highest total wins.**

### The drawless invariant

Because every edge cell resolves to exactly one owner, the corner bonus adds
exactly one point (five corners is odd), and the award is zero-sum, the two
players' **combined score is always the number of edge cells plus one = 51** on
the full board. 51 is **odd**, so a tie is impossible — *Star is **drawless** by
design. (This package verifies the invariant on thousands of random full boards;
see `selftest.py`.)

## Double *Star (option)

Set **Stones per turn = 2**. On each turn a player places **two** stones on any
two empty cells (they need not be adjacent) — **except** White places only
**one** stone on the very first move. Everything else is identical to *Star.
Double *Star has a very different, "labyrinthine" character (Ea Ea): two-way
stretches are no longer connections, and it features the famous *Limbo*
situation. Passing ends your whole turn.

## Not implemented (documented differences)

- **Nobridge *Star** and **Star Y** (rulebook variations, p.21) are not included.
  In Nobridge *Star the centre star is an ordinary region either player may
  occupy; Star Y changes the winning object entirely. These are genuinely
  different games and are left as future packages.
- **Handicapping** (pre-placed stones, point spots, the pie/swap first-move
  offer) from the rulebook is omitted.
- The exact printed cell shapes/positions are approximated (see board note above).

## Sources

- Official Kadon *STAR rulebook (PDF): <https://gamepuzzles.com/starbook-final.pdf>
- Ea Ea, *Double *Star* (archived): <http://ea.ea.home.mindspring.com/*DoubleStar.html>
- Wikipedia, *"\*Star"*: <https://en.wikipedia.org/wiki/*Star>
- Craige Schensted & Charles Titus, *Mudcrack Y & Poly-Y* (Kadon).
