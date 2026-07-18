# Jetan (Martian Chess)

Edgar Rice Burroughs' Barsoomian chess, published in *The Chessmen of Mars*
(1922, Chapter II and the Appendix) — the only game in fiction whose complete
rules the author supplied. Seat 0 = **Black**, playing from the south
(bottom, ranks 1-2) and moving north; seat 1 = **Orange**, from the north.
Black moves first here (Burroughs leaves the choice to the players). The
10×10 board is checkered black and orange.

## Setup

Back row, **left to right from each player's own side**: Warrior, Padwar,
Dwar, Flier, **Chief**, **Princess**, Flier, Dwar, Padwar, Warrior. Second
row: Thoat, eight Panthans, Thoat. The mirrored perspectives mean each Chief
starts facing the **enemy Princess**.

## Movement

Every piece moves an **exact** number of single-square steps (a "combination
move"): the direction may change with each step, but no square may be entered
twice in one move. Non-jumpers need **empty** intermediate squares; jumpers
pass over anything. A move may end on an enemy piece, capturing it; never on
a friendly piece. Captures happen **only on the final square**.

- **Panthan (P)** — 1 step: forward, forward-diagonal, or sideways; never backward. No promotion.
- **Warrior (W)** — exactly 2 orthogonal steps.
- **Padwar (Pd)** — exactly 2 diagonal steps.
- **Dwar (D)** — exactly 3 orthogonal steps.
- **Flier (F)** — exactly 3 diagonal steps; **may jump**.
- **Thoat (T)** — 2 steps, one orthogonal and one diagonal, either order; **may jump** (reaches the 8 knight squares and the 4 adjacent orthogonals).
- **Chief (C)** — exactly 3 steps, orthogonal and diagonal freely mixed.
- **Princess (Pr)** — as the Chief but **may jump**; she **cannot capture**, and may never **end** a move on a square threatened by an enemy piece (she may pass over threatened squares). Once per game she may make the **escape**: a move to *any* empty square not threatened by the enemy — click the **E** chip in your tray, then a highlighted square.

## Winning and drawing

- **Win**: land any piece on the square of the enemy **Princess**, or capture the enemy **Chief with your own Chief**.
- **Draw** (Burroughs): a Chief captured by anything **other than** the enemy Chief ends the game at once as a draw. (Option: *"Chief is lost, play on"* — the modern chessvariants.com/Zillions revision in which the Chief is simply lost.)
- **Draw**: both sides reduced to **three pieces or fewer of equal total value** (Panthan 1, Warrior 2, Padwar 2, Thoat 3, Dwar 4, Flier 4, Chief 10, Princess 0) and no win in the **ensuing ten moves, five apiece**.
- **Draw** (completeness, per Abstract Games #6): threefold repetition, or 50 consecutive captureless moves by each player; plus a hard 1000-ply engine backstop.
- A player with no legal move loses (see interpretations).

## Documented interpretations

Burroughs' two rule texts are vague and partly contradictory. This
implementation follows the *suggested standard* from **Abstract Games issue 6
(2001)** — Kerry Handscomb's "Jetan: Martian Chess" and L. Lynn Smith's
"Commentary on the Rules of Jetan": *Chained Panthan, Chained Warrior,
Chained Padwar, Chained Dwar, Chained Flier, Wild Thoat, Chained Wild Chief,
Brave Chained Wild Princess with a Brave Free Wild escape.* Concretely:

1. **Exact step counts ("Chained")** — a piece moves exactly its 2 or 3 steps, never fewer (the strict reading of "2 spaces", taken by most commentators).
2. **Warrior is orthogonal-only** — Chapter II mentions "or diagonally" but the Appendix says "straight"; AG resolves in favour of the Appendix to preserve the game's W/Pd vs D/F structure (the "diagonal" being the resultant of an L-turn).
3. **Thoat jumps ("Wild")** — Chapter II says it jumps, the Appendix is silent; jumping also dissolves the step-order ambiguity. (Thoat, Flier, Princess — the non-infantry — are the jumpers.)
4. **Chief/Princess mix directions freely ("Wild")** — the Appendix's "straight or diagonal or combination", the broadest reading, preferred by Handscomb.
5. **Panthan has no diagonal-backward step and no promotion** — the rigorous reading; both AG authors and chessvariants.com concur (a diagonal-backward Panthan playtests as too strong).
6. **Princess is "Brave"** — she may pass over, but not end on, threatened squares. Threat is evaluated with her own square vacated; the enemy Princess threatens nothing (she cannot capture).
7. **Escape = any empty unthreatened square ("Free Wild" escape)** — Handscomb: an up-to-ten-step jumping combination move reaches the whole board, so the escape is simply a one-time teleport to any safe empty square.
8. **"Three pieces or less of equal value"** uses AG's piece values, comparing the two sides' totals; the ten-move countdown restarts whenever the condition lapses and re-arises.
9. **Stalemate loses** — Burroughs is silent; being unable to move (in practice a cornered lone Princess with every safe square covered) is treated as a loss, as in other capture-the-royal games without check (and as Zillions adjudicates it).
10. **First move** — Burroughs lets the players decide; here seat 0 (Black, south) always moves first.
11. **Repetition / 50-move draws** are Handscomb's completeness suggestions, not Burroughs'.

The wagering, dueling and Odwar (non-jumping Flier) variants from the novel
and the AG articles are not implemented.

*Sources: Burroughs 1922 (Project Gutenberg #1153); Abstract Games issue 6,
Summer 2001; chessvariants.com "Jetan - Martian Chess".*
