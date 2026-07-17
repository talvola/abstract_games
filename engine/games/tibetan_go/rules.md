# Tibetan Go (Mig-mang)

The traditional Tibetan form of Go, as documented by John Fairbairn ("Tibetan
go — the mists are lifting", GoGoD *New In Go*, 2005) from the played-out
professional exhibition games at the 1st Shangri-la Tibetan Board Games
Festival (Diqing, June 2005). Fairbairn: "The rules of Tibetan go follow
Chinese rules with the following exceptions."

## Board and setup

- **17×17** board. Play begins with **six Black and six White stones at fixed
  points on the third line** — the *Bo* ("scarecrows", protectors of the
  fields, per Shotwell). They are ordinary stones with no special powers.
- In Go coordinates (columns A–R skipping I, rows numbered from your side):
  **Black** C15, L15, P11, C7, G3, P3 — **White** G15, P15, C11, P7, C3, L3.
  Each 3-3 corner point is taken, alternating in colour around the board; the
  whole setup has 90°-rotation colour-swap symmetry.
- **White plays first.** Komi 0.

## Play

Chinese rules: place a stone on an empty point; enemy groups with no liberty
are captured; suicide is illegal; two consecutive passes end the game.

**The one special rule — the vacated-point ban.** *"It is not permissible to
play immediately on any point just vacated by a captured piece."* If a move
captures stones, the opponent's very next move may not be placed on **any** of
the points those stones just left; the ban lapses after that one move. It
applies "to kos, snapbacks and throw-ins — to all captures":

- **Ko:** the immediate recapture is illegal (this subsumes the ordinary ko
  rule); take the ko back only after playing one move elsewhere.
- **Snapback / killing a group (Fairbairn's worked example, NIG part 3):**
  after your stone is captured, you cannot recapture at once on the vacated
  point — you "must first make one or more moves elsewhere, hope that the
  opponent answers them, and then come back"; the opponent is equally free to
  defend there first. This caught out at least one of the pros in the anchor
  game.

## Scoring

Chinese **area scoring** (Tromp-Taylor): your stones on the board plus every
empty point in a region that touches only your colour. Captured stones are
ignored once removed. Bonuses:

- A player whose area contains **all four corner 1-1 points** scores a bonus
  of **20 zi (40 points)**.
- If that same player **also** controls the **centre point**, a further
  **5 zi (10 points)**.
- "Control here also means occupation": a bonus point counts whether your
  stone sits on it or it lies inside your territory.

Higher total wins; **an equal total is a draw** (komi is 0 and all quantities
are integral points, so ties are genuinely reachable). Traditionally the
margin is quoted in *zi* (1 zi = 2 points): the anchor game was W+0.5 zi.

## Implementation notes / interpretations

- **Positional superko** is kept as a repetition backstop in addition to the
  vacated-point ban (base Chinese rules ban whole-board repetition anyway);
  a hard ply cap guarantees termination.
- The traditional **match-play komi convention** (the next game's komi equals
  the previous game's margin) is a rule about a *series* of games and is not
  modelled — every game here starts at komi 0.
- Shotwell's reported extra rules (e.g. that each move must be played close to
  the previous one) are **deliberately omitted**: Fairbairn found the rule
  "does not appear to exist here" (possibly a Mongolian variation), and
  Sensei's Library calls those reports "either wrong or not mainstream".
- Disambiguation: there is an unrelated traditional Tibetan **custodial
  -capture** game that is also called Ming Mang / mig-mang. That is a
  different game; this package is Tibetan *Go*.

## Sources

- John Fairbairn, *Tibetan go — the mists are lifting*, GoGoD New In Go parts
  1–5 (via Wayback: `web.archive.org/web/2017/http://www.gogod.co.uk/NewInGo/Tibet_1.htm` … `Tibet_5.htm`) — the authoritative ruleset.
- Anchor game SGF: Jiang Zhujiu 9d (W) vs Yue Liang 4d (B), Shangri-la 2005,
  `RU[Tibetan] RE[W+0.5 zi]` — `…/NewInGo/sgf/TibetanGo2.sgf`; its full
  217-move record replays legally under this engine (see `selftest.py`).
- [Sensei's Library: Tibetan Go](https://senseis.xmp.net/?TibetanGo) (setup
  diagram, mirrors NIG).
- Wikipedia, *Go variants → Tibetan Go* — its "40 points + 10" bonus equals
  NIG's "20 zi + 5 zi" (1 zi = 2 points; a unit conversion, not a conflict).
