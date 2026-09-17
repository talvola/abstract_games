# Bug reports for AbstractPlay/gameslib

Seven rule bugs found while using `gameslib` as a differential oracle, with minimal repros
and measured rates. Written to be handed to the maintainers (Discord, issues, or wherever
they prefer).

**Who we are / why we were looking.** We maintain an unaffiliated abstract-games platform and
use `gameslib` as a *differential oracle* — we implement a game independently from the
publisher's rulebook, then replay identical games through both engines and compare
cell-sets. It is an excellent oracle precisely because each game is rule-*enforcing*; these
reports are a by-product of that, offered back. **We have never copied gameslib code.**

**Verified against `641db366` (2026-09-16).** Every issue below was re-checked against
current `main` on 2026-09-17, not just against the snapshot we originally measured. Where a
file changed since we measured it, we diffed the relevant functions and confirmed the change
was unrelated (chat-log/sidebar refactors, clone-helper swaps) and the logic identical.

**Please treat each of these as a hypothesis about which side is wrong.** We adjudicate
against the publisher's rulebook, not against our own implementation, and we have been wrong
before — see the last section, where we retract one earlier claim.

| # | File | Function | Symptom | Measured |
|---|---|---|---|---|
| 1 | `slyde.ts` | `getGroupSizes` / `getWinner` | Declares the **wrong winner** | 1.33% / 0.73% of finishes (4×4 / 6×6) |
| 2 | `hexentafl.ts` | `checkEOG` | **Hard deadlock** — `gameover:false`, no legal move | ~1 per 6,800–8,200 plies |
| 3 | `bamboo.ts` | `canPlaceAt` | Offers **illegal placements** | 15.1% of plies |
| 4 | `minefield.ts` | `buildGraph` | Wins awarded on **diagonal-only** chains | 51 of 150 games |
| 5 | `onager.ts` | `getJumps` | Jumps generated against the **pre-move** board | 56 bad + 18 missed / 12,997 plies |
| 6 | `take.ts` | `checkEOG` | Total annihilation credited to the **non-mover** | reachable in ~3% of games |
| 7 | `amoeba.ts` | `validateMove` | Accepts a move `move()` then mishandles | — |

---

## 1. `slyde.ts` — `getGroupSizes` aggregates singletons into a count, then compares it as a size

**Severity: high — flips the declared winner.**

`getGroupSizes` (line ~430) counts singleton groups and appends the **count** as the last
element of a list of **sizes**:

```ts
return [...groups.map(g => g.size).sort((a, b) => b - a), singleCount];
```

`getWinner` (line ~527) then walks the two players' lists element-wise, comparing
`player1[i] > player2[i]` — so that trailing count is compared against the opponent's real
group size at the same index.

**Repro.** A player with one group of 5 and three singletons scores `[5, 1, 1, 1]`, which this
code renders as `[5, 3]`. Against an opponent with groups `[5, 2]` → `[5, 2, 0]`:

- index 0: `5 == 5`, continue
- index 1: `3 > 2` → **player 1 declared the winner**

Truly, player 1's second-largest group is **1** and player 2's is **2**, so player 2 should
win. The `3` is a quantity of groups being read as the size of one.

**Rate.** Replaying identical move sequences through both engines, the declared winner differs
on **1.33% of 4×4 and 0.73% of 6×6 terminal positions** (independently: 6 of 400 games, and 5
of 600). Both engines agreed on every move; only the adjudication differs.

**Rule.** Kanare Kato's rulebook decides it against the current code: *"multiple groups of the
same color and size are taken as separate groups."*

**Suggested fix.** Emit singletons as individual `1`s (`[...sizes, ...Array(singleCount).fill(1)]`)
and keep the existing comparison, which is then correct.

*Untouched since the game was added (`2f9ea3cc`, 2024-06-19).*

---

## 2. `hexentafl.ts` — `checkEOG` has no "no legal move" case, so a stuck position deadlocks

**Severity: high — the game becomes unplayable, with no result.**

`checkEOG` (line ~481) handles exactly three cases: king dead, king escaped, and repetition.
There is no branch for "the player to move has no legal move." When that position arises the
game reports `gameover: false` with an empty move list and no result — neither engine nor UI
can proceed.

**Repro.** Board `{c6: King, b2: Defender, e5: Defender}`, player 1 to move: `moves()` returns
`[]` and `gameover` stays `false`.

**Rate.** ~1 per 6,800–8,200 plies under random play.

**Note.** This is *not* the `validateMove("pass")` shape — heXentafl has no `pass` move at all,
so it is reached differently.

**Suggested fix.** Add a no-legal-move branch. Which side should be credited is a rules
question (Tafl variants differ); the immediate defect is that no result is produced at all.

*Untouched since the game was added (`107f251a`, 2024-07-03).*

---

## 3. `bamboo.ts` — `canPlaceAt` checks only the group the new stone joins

**Severity: high — illegal moves offered on 15% of plies.**

Bamboo's constraint is that no group may be larger than the player's *number* of groups.
`canPlaceAt` (line ~143) places the stone, then tests only the group containing it:

```ts
const found = conn.find(grp => grp.includes(cell))!;
return found.length <= conn.length;
```

A placement that **merges** two groups *reduces* the group count, which can push a different,
untouched group over the new, smaller limit. That group is never examined, so the placement is
offered although it is illegal.

**Anchor.** The rulebook's Figure 2 prints **4** legal placements for its position; this code
yields **8**.

**Rate.** 15.1% of plies offer at least one illegal placement.

**Suggested fix.** Test every group against the post-placement count:
`conn.every(grp => grp.length <= conn.length)`.

*Untouched since `49103941`, 2026-01-29.*

---

## 4. `minefield.ts` — the win graph uses 8-adjacency, so diagonal-only chains win

**Severity: high — wins awarded to players who have not connected.**

`buildGraph` (line ~479) builds the connection graph with

```ts
grid.adjacencies(x, y, true)
```

and `RectGrid.adjacencies`'s third parameter is `diag` — passing `true` adds NE/SE/SW/NW. The
win test therefore treats a purely **diagonal** chain as a connection. (For contrast, 30 call
sites elsewhere in `src/games` pass `false`.)

**Rate.** 51 of 150 games diverge. This is demonstrated, not inferred: in *every* divergent
game the crowned player was 8-connected but **not** orthogonally connected.

**Rule.** The rulebook specifies orthogonal connection, and the game's own **SPO/OO/SCG**
design note in the sheet depends on it.

**Suggested fix.** Pass `false`.

---

## 5. `onager.ts` — jump chains are generated against the un-updated board

**Severity: medium-high — both offers illegal moves and hides legal ones.**

`getJumps` (line ~172) reads pivots via `this.getTopPiece(checkCell)`, i.e. from `this.board`,
which still holds the mover's piece on its **vacated start square**. That square therefore acts
as a jump partner for the rest of the chain. The `froms` array excludes already-visited
*destinations* but does not vacate the origin.

**Rate.** Over 12,997 plies: **56 forbidden destinations offered and 18 legal ones missed.**

**Isolation.** Changing exactly one thing inside your own algorithm — refreshing the board
between hops — drops disagreements from **67 to 0**. Nothing else was altered.

**Rule.** The 2018 rulebook's "cannot end where it started" clause would be entirely *vacuous*
if the jumper were still standing on its origin, so the square must be treated as vacated.

**Note.** `1f7ab9d6` (2026-08-10) added `postMoveBoard`, but it is used for the superko check,
not for jump generation, so this is unaffected.

---

## 6. `take.ts` — total annihilation is credited to the non-mover

**Severity: medium — wrong winner in a reachable case.**

`checkEOG` (line ~367) branches on `currplayer` — the player to move *after* the move, i.e. the
player who did **not** just move:

```ts
if (this.currplayer === 1 && blues.length === 0)      { this.winner = [1]; }
else if (this.currplayer === 1 && reds.length === 0)  { this.winner = [2]; }
```

When a placement eliminates **both** colours at once, the first matching branch wins, which
awards the game to `currplayer` — the non-mover.

**Rule.** The sheet is explicit: *"If your placement eliminates all red and blue stones,
**you** win."*

**Rate.** The both-empty case is reachable in ~3% of random games.

**Suggested fix.** Test the both-empty case first and credit the player who just moved.

---

## 7. `amoeba.ts` — `validateMove` checks path *length*, not straightness

**Severity: medium — the UI green-lights a move the engine cannot execute.**

`validateMove` (line ~244) validates a destination with

```ts
const path = g.path(from, to);
if (path === null || fstack.length !== path.length - 1) { /* invalid */ }
```

`g.path` is a shortest path, so this accepts any cell at the right *distance*, including ones
not on a straight line. `move()` (line ~296) then requires a bearing:

```ts
const bearing = g.bearing(from, to)!;
const ray = g.ray(fx, fy, bearing).map(...);
```

For a non-straight `to`, `bearing` is `undefined` and the non-null assertion `!` hides it, so
`g.ray` is called with an undefined direction rather than the move being cleanly rejected.

**Suggested fix.** Check `g.bearing(from, to) !== undefined` in `validateMove`, and drop the
`!` in `move()` in favour of an explicit error.

*(Same class as the general `moves()`/`validateMove` disagreement seen elsewhere.)*

---

## Already fixed — no action needed

**`carnac.ts` `compareDolmenScores` — fixed by `2e5dabb4` "Fix Carnac EOG!!" (2026-08-19).**
When we measured it (snapshot 2026-08-05) the function padded the shorter list with zeros and
compared element-wise, ignoring the *number* of dolmens — the game's primary win criterion — so
`[8]` beat `[3,3,3]`. It flipped the declared winner on **46.0% / 33.3% / 17.3%** of complete
games at 8×5 / 10×7 / 14×9. Current code compares `a.length` first and is correct. Noted here
only so you know it was independently confirmed from the outside, and that your fix resolved a
real and high-frequency defect.

## Checked and found clean

- **`carnac.ts`** — no dead `pass` handling; in a real tip position `validateMove("pass")`
  returns `{valid: true}` and all 469 passes were accepted.
- **`quax.ts`** — `checkEOG` has no no-legal-move case, but we proved it **vacuous**: on a
  checkerboard square a bar is always available to both colours, so a stuck position is
  unreachable. No fix needed.
- **`ccorridor.ts`**, **`slyde.ts`** — clean of the `validateMove("pass")` shape.

## A claim we retract

We previously believed there was a **systemic "dead-skip"** defect — that `minefield.ts`,
`clearcut.ts` and `nakatta.ts` rejected the `"pass"` their own `moves()` offers, because
`validateMove` fell through to `algebraic2coords("pass")`.

**That is wrong, and we never reported it.** All three have had an explicit
`if (m === "pass")` guard at the top of `validateMove` since long before we looked
(`clearcut` 2023-07-26, `nakatta` 2025-02-02, `minefield` 2026-03-11), and the guard correctly
defers to `this.moves().includes("pass")`. We have verified this against the code as it stood
on the exact dates we made the claim. The error was ours.

Issue **#4** above (minefield's 8-adjacency win test) is a separate, independently evidenced
finding and is unaffected by this retraction.
