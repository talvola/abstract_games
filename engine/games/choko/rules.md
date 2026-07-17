# Choko

Choko is a traditional stick game from the Gambia River valley in West Africa,
played by the Mandinka and Fula peoples (recorded by Parker in 1909 and by
Murray in 1952). Like its Senegalese cousin Yoté it is a drop-and-jump war game
where **every capture takes two enemy men** — but its signature is the **drop
initiative**: place a stick by choice and your opponent must answer with a
placement. These are the rules **as implemented** here.

## The board

A grid of **5 × 5** cells (traditionally 25 holes scooped in the ground), all
empty to start. Each player has **12 sticks in hand**. Player 1 (red) goes
first.

## Your turn — three choices

Unless you are forced to place (see below), on your turn you do exactly one of:

- **Drop:** place one stick from your hand onto any empty cell.
- **Move:** slide one of your sticks one step **orthogonally** to an empty cell.
- **Capture:** jump one of your sticks **orthogonally** over an adjacent enemy
  stick to the empty cell immediately beyond, removing the jumped stick. Only
  **one leap** per turn — no multi-jumps — and capturing is **not** compulsory.

You do **not** have to finish placing your sticks before you start moving.

## The double capture

Immediately after a capturing jump you also **remove one more enemy stick of
your choice, from anywhere on the board**. So each capture costs your opponent
**two** sticks. (If the jump took the opponent's last stick on the board, there
is nothing more to remove.)

## The drop initiative (Choko's signature rule)

Whenever a player places a stick **by choice**, the opponent **must also place
a stick on their following turn**. That forced reply-drop does not itself force
anything — after it, the first player is free again to place or move. In
practice, whoever holds the "drop initiative" can keep both players placing, or
switch to moving (and capturing), at which point the opponent becomes free to
move too — or to place by choice, seizing the initiative and forcing the first
player to answer in kind. (Because forced replies always pair with voluntary
drops, the forced player always has a stick in hand.)

## Winning and draws

You win by **capturing all of the opponent's sticks** — none on the board *and*
none left in hand — or by **leaving them with no legal move** on their turn. To
guarantee the game ends, it is drawn after 50 plies with no capture or drop, by
threefold repetition, or at a hard 400-ply cap.

## vs Yoté

Choko is a distinct sibling of our `yote`, not a variant: Yoté is played on a
**5 × 6** board with **free drops at any time**; Choko is on **5 × 5** and adds
the **drop-initiative** rule above, which makes the placement phase a tempo
battle (a voluntary drop compels a reply-drop). The double capture and the
one-step/short-leap movement are shared family traits.

## Documented interpretations

- **Sources.** Parker (1909, p. 604 — via Ludii's *Choko*) describes the board,
  paired placement ("if they wish to place a stick after they have already
  moved, the opponent must also place a stick on their following turn"), the
  orthogonal hop capture, and the capture-all win. Murray (1952, p. 83 — via
  Winther's transcription) adds the double capture: "Only one man can be taken
  in a move, but the player who makes the capture then removes any second man
  at choice." We implement the union, which is also how Winther and bead.game
  present the game. (Ludii's own `.lud`, following Parker alone, omits the
  second removal.)
- **Wikipedia discrepancy.** The (unsourced) Wikipedia article describes a
  phased variant in which "after all pieces have been dropped, the second
  player moves first". We follow Parker/Murray/Ludii instead: strict
  alternation throughout, drops freely mixed with moves.
- **No legal move = loss** (family convention, as in our Yoté); the historical
  sources do not address a blocked player.
- bead.game's "both players at 3 sticks = tie" is a modern house rule not in
  Parker/Murray and is **not** implemented; the no-progress draw covers dead
  positions honestly.

## Notation

A drop shows as `@c,r`, a step as `a-b`, a capturing jump as `a x b`, and the
second removal as `x c,r`. Cells are named by their `col,row` coordinate.
