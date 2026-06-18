# Borderline

A minimalist 7×7 chess variant by Gerd P. Degens (2022), with a single shared king.

## Objective
Trap the **neutral king** beyond the borderline so your opponent cannot save it.

## Board & setup (7×7)
Each side has **R N B Q B N R** on its back rank — no pawns. A single **neutral king** sits in the centre (d4). Rank 4 is the **borderline**.

## Play
On your turn you move one of your own pieces **or** the king.
- Pieces move by standard chess rules but **cannot capture each other** — they move to empty squares only. **Only the king can be captured.**
- The **king** may stand only on ranks 3–5, moves one square, and may be moved by **either** player. You may not move the king into the opponent's attack ("own check"), but you may push it into your own attack zone.

## The borderline rule
A piece can attack the king only once **that piece has crossed the borderline** — a White piece from ranks 5–7, a Black piece from ranks 1–3. Where the king stands doesn't matter: it is **not** safe just for being on the borderline (a bishop that has crossed can pin it there).

## Winning & draws
If, on your turn, the king is in check (the opponent threatens to capture it) and you cannot remove the threat, **you lose**. With no captures the material never changes, so a ply cap declares a draw if neither side can force a win.

## In this implementation
- The base version only (the optional capture-with-respawn variant is omitted).
- Source: <https://www.chessvariants.com/rules/borderline>
