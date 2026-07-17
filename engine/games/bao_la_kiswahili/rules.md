# Bao la Kiswahili

Bao ("board" in Swahili) is the four-row Mancala of Zanzibar and the East
African coast, generally reckoned the deepest and most complex traditional
mancala in the world. This package implements the **de Voogt master ruleset**
(the tournament rules collected by Alex de Voogt from Zanzibari Bao masters,
1991–1995, published in *Limits of the Mind*, 1995). Everything below is the
rules **exactly as implemented**; contested or simplified points are listed at
the end.

## Board & setup

- An **8 × 4** board of pits. Each player owns the **two rows nearest them**;
  the row adjacent to the opponent is that player's **front row** (row 1 for
  South/bottom, row 2 for North/top). Only front-row seeds can ever be
  captured; back-row seeds are safe.
- The **nyumba** ("house") is the square-marked pit, the **4th front-row pit
  from each player's right** (South: column 4; North: column 3). It is tinted
  gold while *functional*, pale while alive with fewer than 6 seeds, grey once
  destroyed.
- **Start (master game):** each player has **6 seeds in the nyumba** and **2
  seeds in each of the two front pits on the nyumba's right**, plus **22 seeds
  in hand** (shown in the caption). 64 seeds total, and all 64 stay in play for
  the whole game — captured seeds re-enter on the capturer's side.
- South (seat 0) moves first.

## The two stages

- **Namua** — while you have seeds in hand, every turn begins by introducing
  **one** hand seed into a non-empty pit of your **front row**.
- **Mtaji** — once your hand is empty, you move by picking up a pit with **at
  least two seeds** (never a singleton) and sowing it.

Sowing is always around **your own 16 pits only**, in a loop (front row, then
around the corner along your back row, and round again). Every move chooses a
direction; in the move list `=L` / `=R` name the direction of travel along
**your front row as seen on screen** (a back-row pit sown `=R` first travels
left along the back row — it is the same right-handed circuit).

## Captures

A capture needs **two occupied pits facing each other** in the two front rows.
Captures are **mandatory**: if any capturing move exists you must play one.

- **Namua:** placing your hand seed into an occupied front pit whose opposite
  enemy front pit is occupied captures **the contents of that enemy front pit**
  (only the front pit — the back-row pit behind it is untouched).
- **Mtaji:** a move captures when the **last seed of its first lap** lands in
  an **occupied** pit of your front row whose opposite enemy front pit is
  occupied. If the first lap does not capture, **nothing can be captured in
  the whole move**; if it does, further captures can chain, even after
  intervening non-capturing laps. A first lap of **16 or more seeds never
  captures** (it wraps the whole circuit).

**Re-entering captured seeds (kichwa & kimbi).** Captured seeds are sown, one
per pit, along your own circuit **starting in a kichwa** — the leftmost or
rightmost pit of your front row — heading toward the centre:

- If the capture happened in a **kimbi** (either end pit or either
  next-to-end pit of your front row), you **must** enter from the kichwa of
  **that side**.
- On the **first** capture of a namua turn from one of the four central pits,
  you **choose** the kichwa (the `=L`/`=R` in the move).
- On every later capture of the turn — and on any mtaji-stage capture — the
  kichwa is **forced**: it is the one that keeps your current sowing direction
  unchanged, except that a kimbi capture at the far end forces that end's
  kichwa and **reverses** your direction.

## Relay (multi-lap) sowing

If the last seed of any lap falls into an **occupied** pit, you pick that
whole pit up and keep sowing in the same direction — unless the landing
triggers a capture (capture turns only, see above) or a nyumba rule (below).
Your turn ends when the last seed falls into an **empty** pit. Sowing laps in
Bao can be provably **never-ending** (de Voogt exhibited a legal move that
cycles forever, 2006 — the cycle in his published position repeats every 228
laps); the engine detects such cycles and scores the game a **draw** (or a
win, if the opponent's front row was already emptied by the move's captures).

## Non-capturing turns (takasa / takata)

If you cannot start with a capture, your move is a *takasa* and **no captures
at all** happen during it.

- **Namua takasa:** put your hand seed into a non-empty front pit and sow that
  pit in either direction, with these restrictions:
  - if your nyumba is functional you may **not** place into it — unless it is
    your only occupied front pit, in which case you place into it and sow
    **just two seeds** from it in either direction (the "tax"; the house
    survives);
  - if you have no functional nyumba, you must place into a pit with **at
    least two seeds** unless all your occupied front pits are singletons.
- **Mtaji takata:** sow any **front-row** pit holding 2+ seeds (the nyumba
  included — sowing it destroys its special status); only if your front row
  holds nothing but singletons may you sow a back-row pit (2+ seeds).
- **Your front row may never be emptied, not even for a moment**: any takasa
  move that would leave your front row empty at any instant is illegal (so if
  your only occupied front pit is a kichwa, you must sow it toward the
  centre).
- A takasa lap ending in your **functional nyumba** ends your turn on the spot
  (the house is never relayed in a non-capturing turn).

## The nyumba (house)

Your nyumba is **functional** while it has never been emptied and holds **6+
seeds**; with fewer than 6 seeds its powers are dormant (it is then an
ordinary pit that can come back to life if refilled). It is **destroyed
forever** the first time its contents are moved in a lap — by a safari, by
being sown as a move's starting pit, by being picked up in a relay — or when
the opponent captures it. The tax (two seeds) does not destroy it.

- **Capture turn ends in your functional nyumba** (and its opposite pit is
  empty): in the **namua** stage you choose — **stop** (end the turn, keep the
  house) or **safari** (sow the house's contents onward, destroying it). The
  choice appears as two buttons. In the **mtaji** stage the safari is
  **forced**.
- If the nyumba's opposite pit is occupied, the landing is simply a capture
  like any other (the house is your landing pit and keeps its status).

## Takasia (rare)

Master-rules blocking rule, mtaji stage only: if after your takata move
exactly **one** of the opponent's front pits is under threat of capture while
the opponent themselves has no capture available, that pit is *takasiaed* for
their turn: they may not sow it, and a lap of theirs ending in it stops there
(unless it was reached in the first lap sown from their nyumba). A functional
nyumba can never be takasiaed, nor can the opponent's only occupied front pit,
nor their only front pit holding more than one seed.

## End of the game

You **lose** when, at the start of your turn, your **front row is empty**
(however that came about — even during namua with seeds still in hand), or
when you have **no legal move** (e.g. nothing but singletons in the mtaji
stage). There are no draws in traditional play; the engine adds honest-draw
safety nets: a detected never-ending sowing, 200 consecutive plies without a
capture or introduction, or 2000 total plies score **0–0**.

## Bao la Kujifunza (option)

The attested beginners' game: **2 seeds in every pit**, no seeds in hand — the
game starts directly in the mtaji stage — and no nyumba special rules (both
houses count as already destroyed). Everything else is identical.

## Glossary

- **kete** — the seeds. **shimo/mashimo** — the pits.
- **nyumba** — the "house", each player's square pit.
- **kichwa** — "head": the two end pits of a front row.
- **kimbi** — the end + next-to-end front pits (the kichwa are also kimbi).
- **namua** — the introduction stage; **mtaji** — the main stage / a
  capturing move; **takasa / takata** — a non-capturing move.
- **safari** — "journey": relaying the nyumba's contents onward.
- **takasia** — marking the opponent's only threatened pit so it cannot dodge.
- **mkononi** — "in hand": winning while seeds remain in hand.
- **Bao hamna** — clearing the opponent's front row.

## Sources & interpretations

Primary sources, in order of authority for this implementation:

1. **Mancala World, "Bao la Kiswahili"** (Ralf Gering; Wikimanqala) — the most
   precise de Voogt-derived rules text; wins all conflicts.
2. **Rob Nierse, "Bao (Zanzibar)"** (The Game Cabinet), written directly from
   de Voogt's *Limits of the Mind* — supplied the worked examples frozen in
   `selftest.py` (its diagrams 3–23), including the four kichwa/kimbi entry
   cases, a chain capture, and a full safari.
3. **Wikipedia, "Bao (game)"** — cross-check; agrees with 1–2 throughout.
4. **Ludii, "Bao Kiswahili (East Africa)"** (.lud, after Sanderson 1913) —
   setup and geometry cross-check (its square holes are exactly this
   package's nyumba cells).

Documented decisions and divergences:

- **Ludii divergences** (Mancala World/de Voogt win): Ludii captures even when
  the last seed lands in a previously *empty* front pit; it lets chain
  captures re-choose their entry side; it has no 16-seed rule, no singleton
  ban, no front-row-first takata rule, no "front row never emptied" rule, no
  takasia, no stuck-player loss, and it forbids starting a mtaji-stage takata
  from the nyumba (de Voogt explicitly allows it).
- **BGA's help page** for its Bao la Kiswahili describes only the simplified
  sowing/capture core plus the same two loss conditions implemented here.
- **Tax then relay:** after the two tax seeds are sown, the lap continues by
  the normal relay rules (sources do not spell this out; interpreted as an
  ordinary lap).
- **Takasia scope:** applied only when both players are in the mtaji stage,
  per Mancala World's placement of the rule; threat = a first-lap capture
  existing on the current board.
- **"Front row never emptied":** stated by Mancala World under the mtaji
  stage; applied to takasa moves in both stages here (same principle, and the
  namua case is otherwise unreachable-suicidal). Capture turns are exempt
  (captures are mandatory and re-enter seeds into the front row).
- **Loss timing:** an empty front row loses immediately even during namua and
  even if the player emptied it themselves (the takasa restriction makes the
  self-inflicted case near-impossible).
- **Never-ending moves** are real Bao (Kronenburg, Donkers & de Voogt,
  *Never-Ending Moves in Bao*, ICGA Journal 2006); scored as a draw as
  described above. The selftest replays de Voogt's published never-ending
  position (Mancala World, Problem 3) from its 22-ply notation, reproduces the
  published diagram pit-for-pit, and verifies the A3L sowing cycles. The
  **measured minimal period is 228 laps** (immediately periodic; the lap-1
  state recurs at lap 229; independently re-derived during QA — board-only,
  pit-sequence and lap-length projections all have minimal period 228, all
  228 boards in the cycle are distinct, and every alternative reading of
  "A3L" terminates). Mancala World's solution caption says "period 218";
  since no projection of the verified cycle can have period 218, that figure
  is attributed to the page's own counting.

### Distinctness vs Omweso (also in this collection)

Same 8×4 board family, entirely different game: Omweso starts with all 64
seeds on the board (no introduction stage, no hand), captures **both** opposite
pits by *column* and re-sows the loot from where the capturing lap began, has
no house, no mandatory captures, no direction choice (fixed counterclockwise),
no takasa/takata distinction, and loses only by having no move. Bao captures
the opposite **front** pit only, re-enters captured seeds at the kichwa under
the kimbi/direction rules, runs the namua hand-introduction stage, and is
built around the nyumba (tax/stop/safari) and mandatory captures.
