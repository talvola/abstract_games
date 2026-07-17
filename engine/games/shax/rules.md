# Shax

The national mill game of Somalia (northern name *shax*; called *jar* or *jare* — "cut" —
in the centre and south; also seen as Jare or Djelga). Rules as implemented here, following
Rick Davies, *An Introduction to Shax: a Somali game* (Mogadishu 1988, written with Somali
players; the primary written source, also the basis of the Wikipedia article), cross-checked
against Jama Musse Jama's Shax materials and modern summaries.

## Board and aim

- The standard 24-point morris board: three concentric squares joined by four mid-side
  spokes. **No diagonals.**
- Each player has **twelve men** — so the placement phase fills the board **completely**.
- A **jare** (mill) is three of your men in a row along a marked line. Reduce the opponent
  to **two men** and you win (three are needed to make a jare).

## 1. Placement phase

Players alternate placing one man on any empty point until all 24 men are down.

- Forming a jare during placement removes **nothing**. But the game remembers **who formed
  the first jare** — that player gains priority at the transition.
  > "While placing their pieces each player also aims to be the first to place three in a
  > row … This is called a jare." — Davies

## 2. Transition (the board is full)

> "When both have placed all their pieces on the board the player who first made a jare has
> the right to remove one piece belonging to the other player, from anywhere on the board.
> **Then the other player has the same right.** The player who first made a jare then takes
> the first turn to move." — Davies

- The first-jare player removes any one enemy man, then the other player removes any one
  enemy man (whether or not they ever made a jare), then the first-jare player slides first.
- **If nobody made a jare during placement**, the second placer takes over the priority
  role: they remove first, the first placer removes second, and the second placer moves
  first. Davies' rules section says only "the player who did not make the first move of
  the game now makes the first move" (silent on removals — but the board is full, so
  movement is impossible without them), and games.porg.es confirms it is the **second
  player** who removes in this case. That the removal stays symmetric (one each) is
  supported by Davies himself, describing the children's simplified game by contrast:
  > "However there is no middle stage where **each can take off one piece belonging to
  > the other, regardless of whether they have initially formed a jare or not**." — Davies,
  > "Varieties of shax"
  i.e. the full game's middle stage is one removal each *regardless of jare*.

## 3. Movement phase

- A turn is one man sliding **one step along a line** to an adjacent empty point.
- Each time a player forms a jare, they immediately remove one enemy man **from anywhere
  on the board** — men standing in a mill are **not** protected (Davies: "from anywhere on
  the board"; unlike Nine Men's Morris). Breaking and re-forming a mill captures again.
- **No flying**, ever — even with only three men you may only slide to adjacent points.

## 4. Blocked players — *oodan* (the signature rule)

A player with no legal move does **not** lose. They call *"jid i sii aan jar aheyn"* —
"give me a way without a jare":

> "The besieger is bound to open up a space to move by moving one of his pieces without
> scoring a jare. If such a move happens to result in the besieger scoring a jare, that
> player is not allowed to exercise his normal right to remove one of his opponents pieces
> from the board. Oodan (closed) is the term used to describe this situation." — Davies

("Without scoring a jare" is read per Davies' own next sentence — and per games.porg.es —
as *without profiting from a jare*: a jare-scoring freeing move is legal but captures
nothing, rather than being forbidden when a jare-free alternative exists.)

- The blocked player's turn is taken instead by the opponent, whose legal moves are exactly
  those that leave the blocked player able to move (free choice among them). A freeing move
  that happens to form a jare captures **nothing**. Play then continues with the freed
  player.
- *Documented interpretation:* if **no** move of the opponent can free the blocked player
  (or both players are simultaneously blocked), the sources are silent; the position is
  scored an honest **draw** — the blocked player cannot lose by blockade, and the game
  cannot continue.

## 5. End of the game

- **Win:** the opponent is reduced to two men. (Resigning/forfeiting is always possible.)
- **Draw (engine backstops, matching the platform's morris family):** 50 consecutive plies
  with no placement and no capture, threefold repetition of a position, or an unopenable
  blockade (above). A genuine tie scores 0 for both.

## How Shax differs from Nine / Twelve Men's Morris

1. Twelve men and a **completely full** board after placement; no diagonals (unlike Twelve
   Men's Morris).
2. Placement mills capture nothing — only **jare priority** (first mill) matters.
3. The **double removal** at the transition: priority player first, then the other player
   regardless of mills.
4. Captures may take men **out of mills**.
5. **No flying.**
6. A blocked player is freed by the opponent (*oodan*) instead of losing.

*Sources: Rick Davies, "An Introduction to Shax: a Somali game" (1988, PDF at
mogadishuimages.wordpress.com); Wikipedia, "Shax (board game)"; games.porg.es/games/shax;
Jama Musse Jama, "Shax: the preferred game of our camel-herders" (Sun Moon Lake, 2000) —
cultural background; BGG 63875.*
