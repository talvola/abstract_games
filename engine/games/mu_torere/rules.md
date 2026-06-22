# Mū Tōrere

Mū Tōrere is a traditional two-player game of the Māori of Aotearoa (New
Zealand). It is a game of movement and blocking with no captures: you win by
manoeuvring your opponent into a position where they cannot move.

## The board

The board is an **eight-pointed star**. The eight outer points are the **kewai**,
indexed `0`..`7` around the ring (clockwise from the top). The single central
point is the **putahi** (id `c`).

Adjacency:

- Each **kewai** is adjacent to its two ring-neighbours (mod 8) **and** to the
  putahi.
- The **putahi** is adjacent to all eight kewai.

## Setup

Each player has **four men**.

- **Player 0** (Black) occupies kewai `0, 1, 2, 3`.
- **Player 1** (White) occupies kewai `4, 5, 6, 7`.
- The **putahi starts empty**.

Player 0 moves first.

## Moving

On your turn you slide **one** of your men to an **empty adjacent** point. There
are no captures. The three move types:

1. **Kewai → adjacent empty kewai** — always allowed.
2. **Kewai → empty putahi** — allowed **only if** that kewai is adjacent to an
   **enemy** man, i.e. at least one of its two ring-neighbours holds an opponent's
   man.
3. **Putahi → any empty kewai** — always allowed.

### Why rule (2) exists (the interpretation)

The restriction on entering the centre is the defining rule of Mū Tōrere. Without
it the first player could win almost immediately: they would move a man to the
empty putahi and then, on following turns, repeatedly shuffle pieces to strangle
the opponent before any real contest develops. Requiring that the man entering
the putahi be **next to an enemy man** removes that trivial first-move win and
forces genuine play.

There are minor variant readings of this rule in the literature (some sources
phrase it as "a piece moved to the centre must be adjacent to an opponent's
piece"). **This package implements it as: a man may move from a kewai onto the
empty putahi only when one of that kewai's two ring-neighbours is occupied by an
enemy man.** This is the standard and most widely cited form of the rule and is
what prevents the quick first-player win.

## Winning

A player who has **no legal move on their turn loses**; the opponent wins. This
is the only way the game ends in normal play — there are no captures and no other
terminal condition.

## Draw / termination safeguard

The game is finite in practice (a stuck player loses), but a **defensive ply cap**
of 200 half-moves is included: if it is ever reached without anyone being stuck,
the game is declared a **draw**. This guards the engine's termination guarantee
under random play; it is not part of the traditional ruleset and is not expected
to trigger in real games.

## A note on optimal play

With best play from both sides Mū Tōrere is a **draw** — the first player cannot
force a quick win (this is exactly what rule (2) ensures). The game rewards
careful blocking rather than racing.

## Move notation

Moves are `from>to` paths of point ids, e.g. `0>c` (kewai 0 to the putahi) or
`c>5` (putahi to kewai 5).
