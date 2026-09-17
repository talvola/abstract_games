# Tawlbwrdd (Welsh tafl, 11×11)

**Tawlbwrdd** ("throw-board") is the Welsh member of the Norse **tafl** family.
It is named in Welsh law codes before 1250 and described — partially — in a
manuscript by **Robert ap Ifan** in **1587**. Player 0 is the **Attackers**
(24 men) and moves first; player 1 is the **Defenders** — a **King** and 12 men.

> Tawlbwrdd is *not* a re-skin of the **Hnefatafl (Copenhagen)** in this library. The King here is caught between just **two** attackers, he escapes to
> **any edge square**, and the board has **no special squares** at all. He is a
> weak piece who must be escorted every step of the way, and the game is much
> sharper and shorter than the Copenhagen game.

## Setup

- The **King** stands on the central square (f6 / `5,5`).
- **12 defenders** form a diamond around him — a 1-3-5-3-1 block with the King
  at its centre.
- **24 attackers** sit in four groups of six, one at the middle of each edge.
- **Attackers move first.**

The attackers' formation is the one genuinely open question in the
reconstruction, so it is an **option**:

| Option | Formation |
| --- | --- |
| **T-shape** (default) | Five men along the edge plus one stepping inward — the starting position illustrated on Cyningstan. |
| **Arrow (Bell 1969)** | A 3-2-1 wedge pointing inward, from R. C. Bell's reconstruction. |

```
  T-shape (top edge)         Arrow / Bell (top edge)
  . . . # # # # # . . .      . . . . # # # . . . .
  . . . . . # . . . . .      . . . . # . # . . . .
  . . . . . . . . . . .      . . . . . # . . . . .
```

## Moving

Every piece — the King included — moves like a **rook**: any number of empty
squares orthogonally, never diagonally, never jumping.

**There are no special squares.** The centre gives the King no shelter and
blocks nobody, and the four corners are ordinary squares that any piece may
enter, stop on or pass through.

## Capturing

Capture is **custodial** and **active**: when you move a piece so that an enemy
is left between the piece you just moved and another of your own pieces, on
directly opposite sides, that enemy is removed.

- A piece that **moves of its own accord between two enemies is safe** — the
  "gwrheill" clause of the manuscript.
- You may capture **two or three pieces at once** if your move flanks them in
  different directions.
- You may **not** capture a **row** of two or more pieces sandwiched together.
- The **King helps capture** like any of the king's men.

## Capturing the King

> *"If the king himself comes between two of the attackers … and he is unable to
> escape, you catch him."* — Robert ap Ifan, 1587

The King is captured **exactly like any other piece**: between **two attackers
on opposite sides**. There is no four-sided surround, and no square on the board
substitutes for an attacker.

## Winning

- **Defenders win** if the King reaches **any square on the edge** of the board
  — *"if the king can go along the line that side wins the game"*. A corner is
  simply one of those edge squares; it is not special.
- **Attackers win** if they capture the King.
- A side with **no legal move loses**.
- A game reaching **400 plies** is an honest **draw**. Random play reaches
  it 5.1% of the time (41 of 800 games); real play ends far sooner — the
  median random game lasts about 150 plies.

## Ruleset choices and omissions

Ap Ifan's account is incomplete, so the gaps are filled from the much better
documented **Tablut**, following Damian Walker's reconstruction. The decisions:

- **Edge escape**, not corner escape, and **two-sided King capture** — both are
  stated in the manuscript itself.
- **No special squares.** The manuscript claims none, and the game works
  without them. Because that reading is disputed, the option
  **"Central square: reserved to the King"** adds the Tablut-style throne: only
  the King may *stop* there, though anyone may pass over it. Aage Nielsen's
  balance testing of the reconstructions favours having a throne.
- **Attackers move first** — the usual tafl convention; ap Ifan does not say.
- **"Watch your king"** — the manuscript requires the attacker to *warn* before
  capturing the King, like *"check"* in chess. That is a courtesy between two
  people at a board, not a rule the engine can enforce, so it is **omitted**.
- Ap Ifan's "six in the centre of every end of the board **and in the six
  central places**" would give more than 24 men; R. C. Bell read the second
  phrase as "four central places". Both layouts offered here total 24.
- Edge escape is known to favour the defenders, and it does here: over 800 random
  games the defenders took **78.5%** of the decided ones (596 to 163), on both
  layouts alike. Historical rulesets made no
  promise of balance — Copenhagen's corner escape is the modern *fix* for this.

## Sources

- H. J. R. Murray, *A History of Board-Games Other Than Chess* (1952), p.63 —
  the translation of Robert ap Ifan's 1587 passage (Peniarth MS 158).
- F. R. Lewis, "Gwerin Ffristial a Thawlbwrdd" (1941); R. C. Bell, *Board and
  Table Games from Many Civilizations* vol. 2 (1969), p.44.
- Damian Walker, [Tawlbwrdd](http://tafl.cyningstan.com/page/172/tawlbwrdd) and
  [Tawlbwrdd According to Robert ap
  Ifan](http://tafl.cyningstan.com/page/166/tawlbwrdd-according-to-robert-ap-ifan).
- Aage Nielsen, [Summary on the Welsh
  Tawlbwrdd](https://aagenielsen.dk/tawlbwrdd_summary.php) — the reconstruction
  comparison and balance testing.
