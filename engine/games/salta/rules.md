# Salta

Konrad Heinrich Büttgenbach, 1899 — the Belle Époque "humanistic game": a
race across a 10×10 draughts board in which nothing is ever captured.
Rules as implemented, following Ralf Gering's article in *Abstract Games* #8
(2001), which is based on the original 1902 rules booklet.

## Board and setup

Play is on the 50 **dark squares** of a 10×10 board (a1 is dark). Each side
has 15 pieces in three themed rows, each row numbered **1–5 from that
player's left**:

- **First player** (historically *Green*, shown red here): stars 1–5 on
  a1 c1 e1 g1 i1, moons 1–5 on b2 d2 f2 h2 j2, suns 1–5 on a3 c3 e3 g3 i3.
- **Second player** (historically *Red*, shown blue): the 180° rotation —
  star 1 on j10 … star 5 on b10, moon 1 on i9 … moon 5 on a9, sun 1 on j8 …
  sun 5 on b8.

The first player moves first.

## Moving

- A piece moves **one square diagonally in any direction** to a vacant square.
- **Jumping is compulsory:** if an enemy piece stands diagonally **in front**
  of one of your pieces and the square immediately beyond it is vacant, you
  must jump. If several jumps are available you choose freely among them.
- Jumps are **forward only**, over **enemy pieces only**, and **one single
  jump per turn** — no chains. The jumped piece is **not** removed: there are
  no captures in Salta. (Over the board the obligation was enforced by the
  opponent calling "Salta!"; here illegal non-jumps are simply not offered.)
- **Blockade rule:** it is forbidden to play a move that leaves the opponent
  with no legal move. You may blockade *some* enemy pieces, never all.

## Goal

Be the first to shift your whole opening position **seven rows forward**,
each row keeping its original order — so every numbered piece has one exact
target square (the first player's star 1 must reach b8, star 5 j8, moon 1
a9 … moon 5 i9, sun 1 b10 … sun 5 j10; the second player's targets are the
180° rotation: star 1 to i3, moon 1 to j2, sun 1 to i1, etc.). The target
squares are tinted on the board.

**Tempo compensation:** the first player moved first, so one point is
subtracted from his score. In play this means: if the first player completes
his goal position while the opponent would need exactly **one** more move to
complete, the game is a **draw**; the second player completing first always
wins.

## The 120-move rule

At the latest the game is "completed" after **120 moves by each player**.
Each side then counts the moves it would still need to reach its goal, as if
the opponent's pieces did not exist. Each player's **surplus** is the
opponent's count minus his own; one point is then subtracted from the *first*
player's surplus. Whoever holds a positive surplus wins by that many points;
if neither does (counts equal, or the second player ahead by exactly the one
tempo), the game is a **draw**. The historical Krone–Grotewold game
(Jüterbog, 1901) scored this way — "Red wins by 27 points" — and is replayed
move for move in this package's selftest, which also re-derives the 27.

## Implementation notes (documented interpretations)

- The in-game remaining-moves count ignores **all** pieces on a piece's path
  (Wikipedia's reading of the counting rule); pieces are counted
  independently, so mutual-blocking detours among one's *own* pieces are not
  modelled. (Gering and the nestorgames sheet read the count as "as if the
  *opponent's* pieces were non-existent" — own pieces still block — and the
  1901 players counted that way: their 27 = the true own-blocking optimum,
  which our selftest reproduces by search, while the free count of the same
  position is 25. Computing that optimum exactly is a multi-piece
  path-planning search, intractable at arbitrary positions, hence the free
  count here. The choice provably never affects who wins or draws on a
  *completed* goal — a free count of 1 forces a true count of 1 — only the
  point margins, and win/draw at the 120-move cutoff in extreme own-piece
  congestion.)
- Precedence when rules collide: the blockade prohibition is absolute, so a
  totally-blockading jump is illegal and a non-blockading quiet move must be
  played instead; in the (theoretically unreachable) case that *every* move
  would blockade, the jump-priority moves stand, and a player somehow left
  with no move passes.
- The historical 100:120-style handicap system is not implemented.
- Colours: sources call the first player Green (green symbols on black
  pieces) and the second Red (red symbols on white pieces); this port uses
  the platform's seat colours, red for the first player and blue for the
  second.
