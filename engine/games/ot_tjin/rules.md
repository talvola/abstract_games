# Ot-tjin (Aw-li On-nam Ot-tjin)

A relay-sowing **"make fish"** Mancala of the **Penihing** people of the
Mahakam River, Central Borneo. First recorded by Carl Sophus Lumholtz in
*Through Central Borneo* (1920); the modern write-up followed here is Ralf
Gering's article in *Abstract Games* magazine, **issue 14** (Summer 2003). The
board is carved to look like a dugout canoe, and the game is about *"putting out
bait and catching fish."*

These are the rules **as implemented**.

## Board

- Two rows of **nine holes**, plus one large **store** at each end.
- Each player owns the **nine holes on his side** for playing, plus the large
  store on **his left** for collecting caught fish.
- **Player 0 = South** (bottom row), **Player 1 = North** (top row).
- At the start each hole holds the same number of seeds: **2–5**, chosen by the
  *Seeds per hole* option. **3 is the most common; 5 is the challenging
  "make-fish" variant.** (Default: 3.)

South moves first.

## Sowing (clockwise, relay)

On your turn, pick up **all** the seeds from **one of your own holes** and sow
them one at a time in a **clockwise** direction around the eighteen playing
holes. Stores are **not** sown into — they only hold caught fish.

Concretely the sowing cycle runs **North's row left→right, then South's row
right→left**, then wraps around. Each player, at his turn, therefore sows first
along his **own** row from **his right to his left** (Lumholtz's *"from right to
left,"* as seen by that player), then on into the opponent's row. Because the
fish end up in the store on the player's **left**, the distribution is
clockwise (unlike the anti-clockwise Sungka/Dakon, whose stores are on the
right).

**Hole numbering** (each player numbers his own nine holes 1–9 from **his right
to his left**):

| | hole 1 | … | hole 9 |
|---|---|---|---|
| **South** (bottom) | rightmost | … | leftmost |
| **North** (top) | leftmost | … | rightmost |

### Multi-lap relay, "gok", and "making fish"

If the last seed is dropped into an **occupied** hole, lift that hole's whole
contents and sow again in a **new lap** — and so on, lap after lap, until the
last seed is dropped into either:

- an **empty** hole (it now holds exactly 1 seed): the move **ends** and
  **nothing is captured**. This is called **gok**; or
- a hole that **then holds as many seeds as each hole held at the start of the
  game** (e.g. 5 in the five-seed variant — i.e. you drop the last seed into a
  hole that already held 4): that is a **fish** (*ára ot-tjin*, "to make fish").
  The whole fish (the start-count number of seeds) goes to **your store** and
  the move ends.

**Only one fish can be caught per move**, on either side of the board.

## Cannot move

If a player **cannot move** (all of his holes are empty), his **opponent
captures all the seeds remaining on the board** and the game ends.

## Winning

The player who has caught **more fish** (equivalently, more seeds) **wins**. An
equal catch is an honest **draw**.

## "No result" / replay (and how termination is handled)

Lumholtz noted that *"if stones are left on either side, but not enough to
proceed, then there is an impasse, and the game must be played over again."*
This is a repeating pattern in which the seeds keep **circulating with no
captures**. Traditionally the game then ends **without result and is replayed**
— the remaining seeds are **not** divided between the players, and it is **not
counted as a draw** (compare Triple-Ko in Go, or repetition in Gipf).

The printed endgame problem in issue 14 is exactly such a position: with each
player already holding eight fish, South's best line
(`9`, not the losing `8`) leads only to an endlessly circulating,
capture-less pattern — **"No result. The game has to be replayed!"** (In that
printed solution the `!` and `?` marks are chess-style move-quality
annotations, not capture markers.)

Because the platform needs every game to terminate, a long **capture-less
stretch** (or a hard ply cap) ends the game here. As in *Vai lung thlân*, the
result is then decided **purely by the fish actually caught** — seeds still
sitting on the board belong to no one and are never handed to anyone, so a fake
winner is never fabricated. A tied catch at that point scores as a **draw**,
faithfully representing the "no result" outcome.

## Sources

- Lumholtz, C. (1920). *Through Central Borneo* (Vol. II). Charles Scribner's
  Sons, New York.
- Gering, R. (2003). "Ot-tjin — Trying to make fish." *Abstract Games*, issue
  14 (Summer 2003), p. 15.
