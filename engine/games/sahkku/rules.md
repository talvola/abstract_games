# Sáhkku

**Sáhkku** is the traditional board game of the Sámi people (North, Skolt, Inari
and Lule Sámi) — a "running-fight" dice game nicknamed the **"Devil's game"** by
the missionaries who tried to stamp it out. It is kin to the Scandinavian
Daldøs — near-identical dice, related track — but Wikipedia calls Daldøs
"different enough to be described as a fundamentally other game"
(see "How Sáhkku differs from Daldøs" below).

This package implements the **Vuovdaguoika / Gávkevuotna ruleset** as primary:
of the three well-documented regional rulesets (Lágesvuotna, Vuovdaguoika,
Návuotna) it is the one with unbroken living transmission.

## Board and setup

- **3 rows of 15 lines** (*sárgát*) — 45 points. Row nearest you is your
  **home row**; the shared **middle row** lies between.
  ("There are 3×15 *sárgát*.")
- Each player starts with **15 soldiers**, one on every line of their home row,
  all **un-activated** (shown with a dot glyph, as in Daldøs).
- The **king** (*gonagas*, ♚) starts **neutral** on the **Castle**, the
  highlighted central point of the middle row.

## The dice

**Three four-sided stick dice**, faces **X – III – II – blank**:

- **X** (*sáhkku*) — "move an activated piece 1 *sárggis*" **or** "activate a
  piece".
- **II** = move 2, **III** = move 3.
- **Blank = move FOUR** — "Blank signifies 'move four' instead of 'no move'."
- "You may use the dice in any order you like."
- "Dice may only be rethrown if a player gets 3×X": when your fresh throw is
  three sáhkku, a **`rethrow`** button appears — you may optionally re-roll all
  three dice (before spending any of them).

The platform models randomness without a chance node: the rolled triple is
stored in the state, and each die is played **one at a time** — each die is a
separate move by the *same* player. When the dice are spent, or none of the
remaining dice can be used (the turn then ends; a lone unusable remainder is
forfeit — shown as **`pass`** only when *no* die of the turn is usable), the
opponent's fresh triple is rolled.

## Activation

- Soldiers start un-activated and cannot move. An **X activates one soldier**,
  and per the general rule "When activated, a soldier is moved one *sárggis*
  ahead" — so activation advances the soldier one step.
- "Soldiers must be activated in order — frontmost soldier first": only the
  un-activated soldier furthest along the marching direction may be activated.
- Activation is **not forced** — an X may instead move any activated piece one
  step.
- **"Unlike in Lágesvuotna sáhkku, unactivated soldiers may very well be
  captured."** A sleeping soldier is a legal target.

## The track

"Soldiers move towards the right in their home row, left on the middle row, and
towards the right in the enemy row — but upon returning from the enemy's home
row and having for the second time traversed the middle row, the soldiers head
back up into the enemy's home row again, and **never return to their own home
row**."

Each row's end connects to the adjacent row at the same column. The two armies'
tracks are **mirrored** ("right" is each player's own right), so they meet
**head-on** — this pattern is called ***vuosttut*** (the default). The game
"can also be played *mieđut*": player 1's directions reverse, so the armies
**chase** each other instead (the **Movement pattern** option).

## Moving, blocking, capturing

- A die moves one **activated** piece (soldier or your recruited king) exactly
  its value along that piece's track. You may split the dice over several
  pieces or use several on one piece — each die is its own move.
- "It is not allowed to move a piece onto a *sárggis* occupied by a soldier in
  your own army" — **no stacking, ever** (see the Lágesvuotna note below).
- "Furthermore, a soldier may not jump (move past) a soldier of its own army.
  Players may agree to not use this rule, before initiating a game." — the
  **Own-army blocking** option, default on.
- **Capture:** landing **exactly** on a line occupied by an enemy soldier
  (activated or not) removes it permanently. Passing over enemy pieces is free.

## The king (*gonagas*)

- "When you move a soldier onto a point occupied by the king, you **recruit**
  it. From now on, you may use it as your own piece. The king may **never be
  captured**, but can be recruited back by your opponent at any time."
- "When moving a soldier onto the spot occupied by the king — no matter who it
  currently belongs to — the soldier **'pushes' (*cadjat*) the king one
  sárggis ahead**. If an enemy soldier is on this sárggis, the king **'rams'**
  it and it is captured."
- "The king moves as described in the rules under (A) — as an ordinary
  soldier": once recruited it moves by your dice along **your** track (X moves
  it 1, blank 4, …) and **captures** enemy soldiers it lands on, like any
  soldier of yours.
- "The main exception is that, unlike a normal soldier, **it may pass (jump)
  soldiers of its own army**" — the own-army blocking rule never applies to
  the king's own movement (it still may not *land* on your own soldier).

## Winning

**Remove ALL of the opponent's soldiers.** The king does not count — a player
with no soldiers left has lost regardless of who holds the king.

### Termination cap (this implementation)

A capture race could in principle shuffle forever, so this package adds a hard
**6000-ply cap**: if reached, the game is an honest **draw** (0 : 0). (The
platform's Daldøs predates the honest-draw policy and awards its cap to the
material leader; Sáhkku does not copy that.)

## How Sáhkku differs from Daldøs

- A shared, uncapturable, recruitable **king** — Daldøs has none.
- **Three** dice faced **X/II/III/blank** (blank = 4) vs Daldøs's **two** dice
  faced 1–4 (1 = the "dal").
- Un-activated soldiers **can be captured** here; Daldøs's undalled pieces sit
  safely (they simply can't move or capture).
- A flat 3×15 board of lines vs the boat-shaped hole board with its extra prow
  hole; mirrored head-on tracks (*vuosttut*) vs Daldøs's single circulation.
- Activation is optional per X and only the frontmost soldier activates; a
  blocking rule forbids jumping your own soldiers.

## Move encoding (for the UI)

- A move is **`"src>dst"`** (cells `col,row`; row 0 = Red's home row at the
  bottom, row 1 = middle, row 2 = Blue's). The die spent is implied by the
  distance: 1 = X, 2 = II, 3 = III, 4 = blank. Activating the frontmost
  sleeping soldier is just its 1-step move (an X).
- **`rethrow`** (button) — only on a fresh triple-X throw.
- **`pass`** (button) — only when no die of the turn can be used at all.

## Interpretations & ambiguities (documented)

- **Activation advances one step.** The Vuovdaguoika wording ("activate a
  piece") is read together with the article's general rule "When activated, a
  soldier is moved one sárggis ahead" (also the Daldøs-family norm).
- **Triple-X rethrow** is read as an *optional* full re-roll of the fresh
  throw, repeatable while all three dice keep showing X. The source says only
  "Dice may only be rethrown if a player gets 3×X".
- **"One sárggis ahead"** for the king-push is read as the next line along the
  *recruiting player's* track from the king's line. If the recruiting player's
  **own** soldier stands there, the recruiting move is **illegal** (the king —
  now yours — may not land on your own soldier).
- **Blocking** binds only a **soldier** moving past your own **soldiers**, as
  written. The king as a *mover* is explicitly exempt (sourced — "it may pass
  (jump) soldiers of its own army"); the king as an *obstacle* not blocking a
  passing soldier, and enemy pieces never blocking, are readings of the same
  sentence (it names only "a soldier … of its own army").
- **Who starts:** the source's start ritual ("Dice are thrown to determine who
  begins the game. The player who first throws a sáhkku (X) may start") is a
  symmetric lottery; this implementation simply lets Red (seat 0) move first.
- **No cohabitation:** stacking ("several active soldiers on one sárggis", with
  whole-stack capture) is a **Lágesvuotna** rule; Vuovdaguoika forbids moving
  onto any line occupied by your own army, so stacks never arise here.
- **Other rulesets are not options:** Lágesvuotna (capturable queens, mandatory
  X→III→II die order, protected sleepers, per-die X rethrows) and Návuotna
  (3×13 board, 12 soldiers, two X-I-II-III dice, king-only = loss) differ too
  structurally to be clean toggles; they are documented here instead.

## Sources

- Wikipedia, "Sáhkku": <https://en.wikipedia.org/wiki/S%C3%A1hkku> — the
  detailed per-ruleset writeup all quotes above are taken from.
- Alan Borvo, "Sáhkku, the 'Devil's Game'", *Board Game Studies* 4 (2001),
  pp. 33–52 — board form, piece counts, dice marks, king control.
- Ludii, "Sahkku" (DLP): <https://ludii.games/details.php?keyword=Sahkku> —
  "Capturing all of the opponent's pieces is a win" (citing Borvo 2001: 49–52).
