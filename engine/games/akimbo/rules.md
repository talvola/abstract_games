# Akimbo

Luis Bolaños Mures (2026). A drawless square-board connection game — the
designer's successor to **Rhode** (2016). Same board, edges, pie rule and
crosscut machinery; the difference is how unconsolidated diagonal links are
handled. Rhode *forces* you to spend a turn consolidating them; **Akimbo
instead limits how many may exist**, and lets crosscuts self-destruct.

## Board and goal

- Played on the points of an initially empty square grid (default **13×13**;
  this port offers 9×9, 11×11, 13×13). The designer's reference implementation
  defaults to 13×13 and offers 3×3–19×19.
- **Black** owns the **top and bottom** edges, **White** the **left and right**
  edges.
- You win by completing a chain of **orthogonally adjacent** stones of your
  colour touching your two opposite edges. Diagonal adjacency does **not**
  connect.
- Black moves first. **Pie rule**: on White's first turn only, White may play
  `swap` to take over Black's opening instead of placing.

## Definitions

- A **naked diagonal** of a colour is a 2×2 square in which one diagonal pair
  are both that colour and **both of the other two corners are a different
  colour** (empty or the opposite colour). (This is exactly Rhode's "weak
  pair".)
- A **crosscut** is a 2×2 of four stones forming two interlocking
  opposite-colour naked diagonals: two diagonally adjacent black stones and two
  diagonally adjacent white stones.

## Playing a turn

1. **Place** a stone of your colour on an empty point. The placement is **legal
   only if**, *immediately after placing and before any removal*, there is **at
   most one naked diagonal of each colour** on the whole board — i.e.
   `count_naked(Black) ≤ 1` **and** `count_naked(White) ≤ 1`. This bound must
   hold "not even momentarily", so it is judged on the raw board before the
   removal step below.
2. **Resolve crosscuts.** For every crosscut 2×2 that **contains the stone you
   just placed**, remove **your other stone** in that crosscut. The stone you
   just placed is never removed; opponent stones are never removed. (A crosscut
   is legal to create — it is one naked diagonal of each colour — precisely so
   that this removal can then dissolve it.)
3. The winning connection is checked **after** the removal step.

## Moves in this implementation

- Placement: click an empty point. Only points that satisfy the ≤1-per-colour
  rule are offered.
- `swap` (pie rule) appears as a button on White's first turn.
- `pass` is offered **only** when you have no legal placement (a forced skip);
  this is unreachable in normal play.

## Interpretations / notes

- **Verified against the designer's own reference JavaScript** (`Akimbo.html`,
  author luigi87 = Bolaños Mures — the definitive oracle). The legality test
  mirrors `isValidAkimboMove` (place, check `nakedDiags[0].size ≤ 1 &&
  nakedDiags[1].size ≤ 1`, undo). The removal mirrors
  `resolveCrosscutsOnBoard` — only crosscuts touching the placed stone are
  resolved, removing the mover's other stone. Win-after-removal mirrors
  `play` → `checkWin`.
- **The opponent's naked count is invariant under your placement** (a black
  stone can never create or destroy a *white* naked diagonal, since the off
  corners "empty" and "black" are both "not white"). So the opponent's bound is
  automatically satisfied at your placement; the reference checks both colours
  and so does this port.
- **Board size default.** The reference UI defaults to 13×13; this port keeps
  13×13 as the default and offers 9/11/13.
- **Pie rule.** The reference is a hotseat that physically swaps sides. With
  fixed seats (seat 0 = Black/rows, seat 1 = White/columns) the value-preserving
  equivalent is to reflect Black's lone opening stone across the main diagonal
  and recolour it White — Akimbo is symmetric under transpose + colour swap.
  Same convention as this library's Rhode/Hex/Konobi.

## Draws / termination

Akimbo is drawless in real play. The ≤1-per-colour bound means at most one
naked diagonal of each colour survives a placement, hence at most one crosscut,
and it must touch the placed stone — so it is always resolved and **the board is
crosscut-free at the start of every turn**; a crosscut-free full board has
exactly one winning chain. As the platform's standard defensive backstop,
reaching a hard ply cap of 8·N·N (or a double pass, possible only from
constructed near-full positions where a player has no legal placement) is scored
as an honest **draw** — a winner is never fabricated. Never observed in testing
(hundreds of seeded random playouts, all far under the cap, zero draws).

## How Akimbo differs from Rhode

Both are Bolaños Mures square-board orthogonal-connection games with Black
top/bottom vs White left/right. **Rhode forces** you, whenever you have a naked
diagonal (weak pair), to place adjacent to both its stones (consolidating it),
and removes your crosscut stones every turn. **Akimbo** imposes no obligation —
you may place anywhere — but forbids leaving **more than one naked diagonal per
colour**, and only dissolves crosscuts that your placement completes. Its
sibling **Okimba** is the "no captures" variant (the bound is one naked diagonal
*total* across both colours, which makes crosscuts impossible).

Sources: the designer's reference JS `Akimbo.html` (luigi87 / Bolaños Mures);
BGG item 466041 ("Akimbo", 2026). Successor to Rhode (BGG thread 1593043).
