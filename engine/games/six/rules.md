# Six

**Steffen Mühlhäuser**, published by **Steffen-Spiele**, **2003**
([BGG 20195](https://boardgamegeek.com/boardgame/20195/six)). Two players.
These are the rules **as implemented**, taken from the publisher's own rule
sheets (2008 German, 2013 multilingual, 2022 German — see *Sources* below).

Six has **no board**. The 42 hexagonal tiles *are* the playing area, a single
growing cluster laid out on the table. Coordinates here are axial hex `q,r`; the
cluster may drift anywhere, and the display simply follows it.

## Material and setup

- **21 red tokens** and **21 black tokens**. Red is seat 0, Black is seat 1.
- **Two starting tokens** — one red, one black — lie side by side in the middle
  of the playing area.
- Each player therefore holds the remaining **20 tokens** of their colour.
- **Red moves first.**

## The object of the game

Get **six tokens of your own colour** into any one of these three formations:

```
ROW — six in a straight line
(any of the three lattice directions)

      O  O  O  O  O  O


TRIANGLE — a side-3 triangle
(either orientation)

            O
          O   O
        O   O   O


CIRCLE — a ring of six around one cell
(the centre may be EMPTY, yours, or your opponent's — it makes no difference)

          O   O
        O   .   O
          O   O
```

Any *one* of the three wins. Extra tokens never spoil a formation: a row of
seven contains a row of six, and a circle with its centre filled is still a
circle. The moment a formation exists the game ends.

## Round one — laying tokens

Players take turns laying **one token from hand** onto any empty cell that
touches **at least one** token already on the table. It may touch **your own or
your opponent's** tokens — the 2008 sheet says so explicitly ("*Es darf an
eigene und gegnerische Steine angelegt werden*").

Round one is exactly **40 plies** (20 each). Nothing can be captured during it.

## Round two — moving tokens

Once both hands are empty, each turn you **pick up one token of your own
colour** and **lay it down again somewhere else** — any empty cell touching the
table, including a completely enclosed token. You may not put it back where it
came from ("*an einer beliebigen anderen Stelle*" — at any *other* place).

### Capturing

Tokens that your pick-up **cuts loose from the field** are captured and taken
out of the game.

- The **largest** surviving group stays on the table; **every other group is
  captured**, whether it is a single token or a whole group.
- If two (or three) groups tie for largest, **you** — the player who lifted the
  token — choose which one survives.
- **Captures are colour-blind.** You lose your own tokens in a captured group
  just the same. The rule sheet's own figure makes this explicit: it crosses out
  four tiles, one of which is the mover's own.
- Captures are resolved **as the token comes off the table**, *before* it is laid
  down again — so the token must be laid against the group that **survived**.

## How the game ends

1. A player has six of their colour in a **row, triangle or circle** — that
   player wins.
2. A player is left with **fewer than six tokens**, so no formation is possible
   for them any more — that player loses. This applies whichever player's move
   caused it (see *Interpretations*).
3. **Both** players are left with fewer than six tokens — neither can ever win,
   so the game is a **draw**.
4. *(Added by this implementation)* **100 consecutive round-two plies with no
   capture** end the game as a draw. See *Termination*.

## Interpretations

Every point where the sheets are silent or ambiguous, and what settled it:

| Question | Ruling here | Why |
|---|---|---|
| Does the *centre* of a circle matter? | No | Stated outright: "*A complete circle is always a winning formation, no matter whether its centre is empty or it has any of the players' tokens in it.*" |
| Is "six" exact, or at least six? | Containment — a row of seven wins | "The first player to create a formation of six of his or her tokens wins"; a longer row contains one. |
| A pick-up splits the field into **three** groups | Largest survives, both others are captured; a tie among the largest is the mover's choice | The 2008/2013/2022 sheets describe only "one large and one small group", but a hex has six neighbours, so three groups are possible. **The 2024 sheet states the general rule outright**: "*If a move splits the playing field into two or more distinct parts, only the biggest part stays in play.*" Its English tie-break sentence ("choose which part is **removed**") is incoherent once there are three or more parts; its German says "*auswählen, welches Spielfeld im Spiel bleibt*" — choose which one **stays** — and that is what ships. |
| Are captures computed before or after the token is laid down again? | **Before** | The sheet ties them to the pick-up ("tokens that become separated … *when a player removes a token*"), and its figure shows the captured group without showing where the token goes. Computing them afterwards would also let the mover reconnect the field and dodge every capture, making the rule dead. |
| Is the **lifted** token itself ever captured? | No — it is in your hand | The figure crosses out four tiles around the lifted one and does **not** cross out the lifted token. |
| A player's **own** move cuts **themselves** below six | That player **loses** (the opponent wins) | The 2008/2013/2022 sheets only say a player wins by taking so many of *the opponent's* tokens. Three things settle it. (1) The 2024 sheet's tie clause — "*In the rare case that both of you end up with fewer than 6 tiles after a capture, the game ends with a tie*" — only makes sense if the below-six test is read for **both** players after every capture. (2) It makes **no difference to the result**: the sheets award the win "*as soon as*" the other player is under six, so the instant you cut yourself to five your opponent already satisfies that condition. The ruling is therefore behaviour-neutral, and the fact that self-inflicted cuts are common (**43.2%** of attrition losses over 500 measured random games) does not make it load-bearing. (3) Yucata's independent implementation states it symmetrically. Note the *deadlock* a zero-token player would face is **unreachable** under either reading: tokens leave play only on the mover's own turn and the mover always re-lays its lifted token, so a zero-token player is always the non-mover — and the game has already ended. |
| Both players fall below six at once | **Draw** | **Printed in the 2024 sheet**: "*In the rare case that both of you end up with fewer than 6 tiles after a capture, the game ends with a tie*" (the older sheets are silent, and it also follows from the fact that neither can ever form a six). Reached in ~13% of random games, so it is a real outcome, not a fabricated tie-break. |
| Which colour are the two starting tokens? | One of each | The "Preparation" figure prints a red tile beside a black one, each player receives 20 of their 21 tokens, and the 2024 sheet says it in words: "*Place a beige tile and a black tile adjacent to each other in the middle of the table.*" |
| Who moves first? | **Red** (seat 0) | The 2008/2013/2022 sheets say the opening player is drawn by lot ("*Der Anfangsspieler wird ausgelost*"); the 2024 sheet fixes it as **Black**. The two are the *same game*: the opening position is one red token beside one black token, and a 180° rotation about their shared edge swaps the two cells, so "Red first" and "Black first" differ only by a colour swap composed with a lattice symmetry — and every rule here (adjacency, the three formations, the split rule) is invariant under both. Nothing observable distinguishes them. |

## Termination

Round one is finite (40 plies). Round two can **cycle** — picking a token up and
laying it down again is reversible whenever it captures nothing — and the
printed rules say nothing about it (over the board, players would simply agree a
draw). So this implementation adds one rule: **100 consecutive round-two plies
without a capture is a draw.**

Everything else follows from it. While the game is still running both players
hold at least six tokens, so at least twelve are on the table; each capture
takes at least one token out of the game, so at most
`2×21 − 2×6 + 1 = 31` capture events can ever happen. Round two therefore lasts
at most `31 + 32×100 = 3,231` plies, so no game can exceed 3,271 plies; the hard
ply cap in the code sits at 3,272 and is unreachable — it exists only so a
future termination bug fails loudly instead of hanging.

**How load-bearing is the added rule?** In 4,500 random games the no-capture
counter never got past **30** of its 100 plies, and the rule never fired once;
the longest complete random game was 110 plies, and MCTS self-play games ran
9–29 plies (never even reaching round two). Captures are frequent enough in this
game that a capture-free stalemate does not arise by accident.

## Notation and playing in the app

- **Round one:** a move is a single cell, e.g. `2,-1` — one click.
- **Round two:** a move is `from>to`, e.g. `2,-1>4,0` — click your token, then
  its new cell. Only cells touching the group that will survive are offered.
- When a pick-up splits the field into groups of **equal** size, the move
  carries a `=` suffix naming the group you keep (by its lowest cell), e.g.
  `10,0>10,1=11,0`, and the app shows a small picker.
- The trays under the board show how many tokens each player still holds in
  round one; they disappear in round two.

## Not implemented

- **The four-player partnership variant** of the 2008 sheet (two teams of two,
  18 tokens per colour, no advice between partners). The platform fixes the seat
  count per game, and the 2022 sheet is two-player only.
- **The 2003 first edition's component count** (19 tokens per colour and a
  *single* starting token laid by the first player). The 2013 and 2022 sheets
  agree on 21 tokens and two starting tokens; that is what ships.
- **Yucata's opening house rule** ("to reduce the advantage of the starting
  player, it is currently not possible for him to place his second piece
  adjacent to his first one"). Yucata flags this as its own balance tweak; it is
  in none of the publisher's sheets.
- **No bot evaluation function — but one would probably help.** The platform's
  MCTS bot consults `heuristic()` only when a random rollout runs past its 50-ply
  cutoff, and that happens on **19% of rollouts** measured over complete games
  (72 of 379; the same figure taken at the opening position alone reads 33%, which
  is why it must be measured over whole games). So an evaluation here is *not*
  inert. A candidate (how close each side is to completing a formation, plus
  material) was written, but its strength through `MCTSBot` was **not** measured to
  a conclusion, and an evaluation whose strength was never measured through its own
  consumer is worse than none — a sign-flipped or worthless one passes every shape
  check. Six therefore ships without one; `selftest.py` asserts the absence, so
  adding one forces the measurement. (MCTS self-play games currently finish in
  9–29 plies, inside round one, by completing a formation.)

## Sources

- **Publisher rule sheets** (the authority here), from the old site
  `steffen-spiele.de`: `Six_EN.pdf` (2013, English — the primary text and all
  figures used as anchors), `Six_DE.pdf` (2008, German, four pages, the only
  sheet with the four-player variant), `SixAnl._dt_2022.pdf` (2022, German). The
  2013 sheet also exists in ES/FR/IT/NL/PT; all agree.
- **The CURRENT sheet: `Six_Rules.pdf`** (© 2024 Steffen Spiele, an imprint of
  Helvetiq; FR/DE/EN/PL/ES/IT), linked from the live product page at
  `steffen-spiele.com/products/six`. It is a genuine **revision**, and it prints
  three of the rulings below outright instead of leaving them to inference: the
  split into "*two or more distinct parts*", the **both-under-six tie**, and the
  two starting tiles being one of each colour. It also names **Black** as the
  first player (immaterial — see *Interpretations*), and its capture figure is
  geometrically identical to the 2013 one used as the anchor here.
- **[Yucata](https://www.yucata.de/en/Rules/Six)** — an independent online
  implementation, used as a third opinion on the below-six ending.
- **[BGG 20195](https://boardgamegeek.com/boardgame/20195/six)** — designer,
  year, publishers and the publisher-written game summary.
