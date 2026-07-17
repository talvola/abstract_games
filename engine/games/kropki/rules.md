# Kropki (Точки / Dots)

The traditional Russian/Polish paper-and-pencil encirclement game, in the
standard competitive **"no-territory"** ruleset (СКСТ rules as played on
playdots.ru and zagram.org). Two players, Red (moves first) and Blue.

## Placing dots

- Players alternate placing one dot on any empty, un-painted grid intersection.
  Dots never move and are never removed from the board.
- You **may** play inside an opponent's empty enclosure (see *Houses* below);
  you may never play inside painted (captured) territory.
- Instead of placing, a player may **pass**.

## Capturing

- A **chain** is an unbroken loop of one player's *live* dots, each step one
  cell horizontally, vertically **or diagonally** (8-connectivity). Captured
  (dead) dots never form part of a chain.
- After each placement, every minimal closed chain of the mover's dots through
  the new dot is considered (branching chains: the **shortest** chain is used —
  СКСТ). If the region inside a chain (interior connectivity is orthogonal,
  4-connected) contains at least one **enemy live dot**:
  - the whole interior is **painted** in the mover's colour and is dead for the
    rest of the game;
  - each enemy live dot inside is **captured**: +1 point to the mover (dots stay
    on the board, shown on painted ground);
  - any of the mover's own previously captured dots inside are **freed** — they
    become live again and the opponent's score drops accordingly
    (counter-encirclement / liberation);
  - the mover's own live dots inside simply stay live.
- The **board edge never encloses anything** — a surrounding chain must consist
  entirely of the player's own dots.
- Enclosing only your own dots (or your own dead dots) captures nothing.

## Houses (empty bases, «домики»)

- A closed chain around a region with **no enemy live dots** captures nothing
  and paints nothing, but the region is remembered as the owner's *house*.
  The owner may keep playing inside their own house freely.
- If the opponent places a dot inside your house, the dot is captured on the
  spot: the house area is painted in your colour and you score +1.
- **Exception (mover precedence, СКСТ):** if that dot *simultaneously completes
  a capturing chain for its own player*, the mover's capture stands and the
  house dissolves instead. («Исключением является тот случай, когда точка,
  поставленная в домик другого цвета, этим же ходом одновременно замыкает
  непрерывную цепь своего цвета… Тогда она не окружается, а сама окружает
  часть домика.»)

## End of the game and scoring

- The game ends when **no playable intersection remains**, or after **two
  consecutive passes**.
- Score = number of enemy dots you have captured. Higher score wins; **equal
  scores are a draw**.
- Termination is inherent: every placement permanently consumes an
  intersection, so a game is at most width×height placements long.

## Board and starting position

- Sizes: 13×13, 20×20 (default), 25×25, or the traditional school-notebook
  page 39×32.
- **Cross start** (default, the standard competitive opening — «скрест»): a
  2×2 block of four dots at the centre of the board, each player owning one
  diagonal pair (as displayed, Red holds the top-left and bottom-right dots of
  the block); Red moves first. With `start = empty` the board starts blank
  (any first move is allowed). Layout per the СКСТ rules and oppai-rs's
  `InitialPosition::Cross`.

## Implementation notes

Rules as implemented were cross-checked against the СКСТ competitive rules
(playdots.ru, via the Wayback Machine), zagram.org's no-territory rules and
Russian Wikipedia («Точки»), and the whole engine was verified move-by-move
against the reference engine **oppai-rs** (pointsgame project): 80 random
games / 10,731 moves with the complete board state compared after every move —
0 discrepancies (see `_diff_oppai.py`).

Documented dialects **not** implemented here: territory scoring (Polish rules:
optional un-painted enclosures worth 0.5/intersection), the *grounding*
(заземление) early-termination claim, first-to-N-captures, the bonus-move
variant, and playdots' "first move near the centre" restriction for
empty-board starts.

## Sources

- zagram.org rules: https://zagram.org/info/kropki-rules.en.html
- СКСТ rules (playdots.ru, archived):
  http://web.archive.org/web/20190819032440/https://playdots.ru/rules/
- Wikipedia: https://en.wikipedia.org/wiki/Dots_(game) ·
  https://ru.wikipedia.org/wiki/Точки_(игра)
- BGG: https://boardgamegeek.com/boardgame/26067/kropki
- Reference engine (test oracle): https://github.com/pointsgame/oppai-rs
