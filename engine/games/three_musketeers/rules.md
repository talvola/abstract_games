# Three Musketeers

An asymmetric hunt game for two players, designed by **Haar Hoolim** and published
in Sid Sackson's *A Gamut of Games*. One player commands the **three Musketeers**;
the other commands the **22 enemy pieces** (Cardinal Richelieu's men). The two
sides have completely different pieces, moves, and goals — the "principle of
unequal forces".

## Board & setup

- A **5×5** grid. All 25 squares start occupied.
- The **Musketeers** (seat 0, dark, labelled **M**) sit on **two opposite corners
  and the centre**: in this implementation **a1, c3, e5** (cells `0,0`, `2,2`, `4,4`).
- The **enemy** (seat 1, light) fills **all 22 remaining squares**.

## Movement

Players alternate, **the Musketeers moving first.**

- **Musketeer move (always a capture):** move one Musketeer one square
  **orthogonally** onto an adjacent square that is occupied by an **enemy**,
  removing that enemy from the game; the Musketeer takes its place. A Musketeer
  may **never** move onto an empty square — it can only ever capture.
- **Enemy move:** move one enemy piece one square **orthogonally** onto an
  adjacent **empty** square. The enemy never captures.

## Winning

- **The enemy wins** if the three Musketeers ever lie in the **same row** or the
  **same column** (a straight line of three). Because the Musketeer player *must*
  capture on their turn, if every available capture would line the Musketeers up,
  they are forced into a losing line and the enemy wins.
- **The Musketeers win** if, on **their** turn, they have **no legal move** —
  i.e. no Musketeer has an adjacent enemy to capture — *and* they are not in a
  line. (If they were in a line the enemy would already have won.)

## Interpretations / implementation notes

- The line check is applied **after every move by either side** (the enemy can
  steer the Musketeers into a line, and a forced Musketeer capture can self-line).
  The enemy wins the instant the three are collinear.
- Standard sources impose **no restriction** forbidding the Musketeer from moving
  into a line; a forced self-line is a loss for the Musketeers, as above.
- **Termination.** Each Musketeer move permanently removes one enemy, so at most
  22 captures can ever occur — the game cannot loop on the Musketeer side. The
  enemy could in principle shuffle empty squares forever, so a hard cap of
  **400 plies** declares a **draw** if no win condition has fired (this is a
  safety net for self-play; in normal play the game ends well before then).
