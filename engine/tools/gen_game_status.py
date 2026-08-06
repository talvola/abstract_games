"""Regenerate ../../GAME_STATUS.md -- the living catalogue of every bundled game
with its board, verification anchor, and testing state.

Run from engine/:  PYTHONPATH=. python3 tools/gen_game_status.py

Board shape + selftest/rules presence are read live from each package; the
verification anchors and browser/UX status are curated below (update them as new
games are added or boards get a human eye).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agp import load  # noqa: E402

ENGINE = Path(__file__).resolve().parents[1]
OUT = ENGINE.parent / "GAME_STATUS.md"

# Verification anchor per game (from GAMES_QUEUE batch notes + capability sessions).
ANCHOR = {
 "alquerque": "selftest (12v12 setup, mandatory jump-capture + chains, annihilation/stuck win); reuses the verified alquerque board + lines",
 "amazons": "move-gen anchored on the known 2176 opening moves; conformance",
 "antichess": "python-chess AntichessBoard differential (perft d5, 789 terminals)",
 "ard_ri": "independent tafl rule re-derivation; conformance",
 "atari_go": "independent re-derivation; liberty/group-capture + superko probes",
 "atomic_chess": "python-chess AtomicBoard differential (kiwipete perft d4)",
 "bagh_chal": "independent adversarial rule review (alquerque topology / jumps / "
              "win-conditions all MERGE; capture-inference fuzzed 20k boards) + selftest",
 "berolina": "shared chesslike core; perft; conformance",
 "borderline": "conformance + targeted tests (neutral shared-king rule)",
 "brandub": "documented tafl ruleset; conformance",
 "brazilian_draughts": "perft 7/49/302/1469 = published 8×8 counts",
 "breakthrough": "conformance (forward-only ⇒ always terminates)",
 "capablanca_chess": "independent adversarial review; castling probes",
 "checkers": "forced-capture/multijump tests + conformance",
 "chinese_checkers": "computationally-verified 121-point star geometry (6-fold symmetric, six 10-point camps) + selftest (chain-jumps, fill-opposite win, 6-seat cycle)",
 "chess": "perft 197281 (depth 4)",
 "connect6": "1-then-2-stone + gap-six review; conformance",
 "connect_four": "conformance + targeted tests",
 "courier_chess": "independent review (caught+fixed an insufficient-material bug)",
 "crazyhouse": "python-chess CrazyhouseBoard: perft 20/400/8902/197281 + 62/4715/197413 "
               "(drop midgame) + 400-game/46,427-ply synchronized walk, 0 mismatches",
 "dao": "re-derived vs US patent + BGG; 4 win conditions",
 "dou_shou_qi": "full rank/river/trap/den rule re-derivation",
 "einstein": "selftest (dice-stored model, die-number + nearest-higher/lower rule, forward-only movement, capture on landing, both win conditions); first has_randomness game",
 "fanorona": "re-derived vs Wikipedia; approach/withdrawal chains",
 "fox_and_hounds": "conformance (hounds advance-only ⇒ terminates)",
 "foxsox": "ZRF port (zillions skill); conformance",
 "freeform_chess": "freeform/unenforced mode (lighter conformance path)",
 "frisian_draughts": "review REJECTED+fixed weighted capture; king=1.5",
 "gomoku": "conformance + targeted tests",
 "go": "independent adversarial rule review (Tromp-Taylor area scoring / ko-superko / "
       "suicide / two-pass) + selftest; liberty core shared with Atari Go",
 "gonnect": "Go capture (atari_go core) + edge connection; rulebook review",
 "goose_chase": "ZRF port (zillions skill); conformance",
 "grand_chess": "shared chesslike core; conformance",
 "havannah": "ring/bridge/fork exhaustive shape tests",
 "hex": "connectivity BFS; can't-draw ⇒ terminates",
 "hnefatafl": "Copenhagen ruleset review + probes",
 "horde_chess": "python-chess HordeBoard differential (perft d4 + 2000-game)",
 "international_draughts": "published WDF perft 9/81/658/4265/27117/167140",
 "kalah": "selftest (skip-opponent-store sowing, extra-turn, capture conditions, end-sweep, seed conservation) + independent adversarial rule review",
 "janggi": "hand-derived 31-move opening + full cannon/palace; perft baseline",
 "king_of_the_hill": "chess perft 20/400/8902 + center-king win",
 "konane": "3000-position move-gen cross-check",
 "lasca": "independent adversarial rule review (tower-capture / liberation / "
          "forced multi-jump / promotion) + selftest of the tower mechanics",
 "lines_of_action": "connectivity win + conformance",
 "los_alamos_chess": "6×6 move-gen + mate/stalemate tests",
 "makruk": "independent review; 6th-rank promotion probes",
 "mini_shogi": "published 5×5 minishogi perft 14/181/2512 (depth-1 hand-checked) "
               "on the python-shogi-verified ShogiLike core",
 "nine_mens_morris": "independent adversarial rule review (topology/mills/flying/"
                     "removal/win — all MERGE) + topology-invariant selftest",
 "nogo": "independent re-derivation; capture+suicide both illegal",
 "onitama": "selftest (card-driven two-step turn, card rotation used->middle->hand, per-player offset mirroring, capture, both win conditions); deal is the only randomness",
 "order_and_chaos": "conformance (exercises the =CHOICE picker)",
 "oust": "event-based win; never-draws check; conformance",
 "oware": "re-derived vs Awari; 2000-game seed-conservation proof",
 "pente": "custody-capture tests + conformance",
 "quoridor": "independent adversarial rule review (wall blocking / no-overlap-cross / the pathfinding-seal gate built+verified / jumps — all MERGE) + selftest",
 "pentago": "rotation algebra (4×twist = identity) + win-judged-after-rotation "
            "selftest; place+rotate via the =CHOICE picker",
 "racing_kings": "shakmaty perft 21/421/11264 + 31,920 python-chess positions",
 "rolit": "selftest (Reversi flip incl. mixed-colour lines, 4-seat cycling, "
          "board-fill termination, sole-leader/tie scoring); first >2-player game",
 "reversi": "flip/pass/terminal tests + conformance",
 "shatranj": "independent review; Alfil leap / bare-king probes",
 "shogi": "python-shogi differential: perft 30/900/25470/719731 (depth 4, = published) "
          "+ 300-game synchronized move-set walk, 0 mismatches",
 "tablut": "capture/escape positions; king-assist from Cyningstan",
 "tanbo": "Steere's official PDF; bounded-root capture",
 "three_check": "chess perft 20/400/8902 + 3-check win",
 "tic_tac_toe": "MCTS never loses as X (optimal-play signature)",
 "twixt": "selftest (bridge-crossing geometry, peg-ownership rules, auto-knight-bridge + crossing suppression, connection win, draw); shares the connection family with Hex/Y",
 "turkish_draughts": "40k-position + 489k jump-chain cross-check, 0 double-jumps",
 "wildebeest_chess": "review REJECTED+fixed castling ⇒ NoCastling",
 "xiangqi": "independent review + perft baseline; cannon hopper",
 "y": "selftest (three-edge connection win, the can-never-draw property verified over random full boards, swap/pie); shares the connection family with Hex",
 "yodd": "parity win; never-draws; conformance",
 "yote": "selftest (drop/step/jump, the bonus-removal double-capture, optional capture, annihilation/stuck win) + independent adversarial rule review",
 "abande": "AbstractPlay gameslib differential (~8,467 positions, both boards, 0 mismatches) + FOUR published diagrams pixel-reconstructed, incl. two fully scored finals (W13-B15, W12-B15) matching their printed captions; 36 mutants",
 "attangle": "AbstractPlay gameslib differential (17,453 positions ours-driving + 82,041 in-package, 0 mismatches) + the designer's figures pixel-verified; 48/48 mutants; termination proved (76/110 plies, no cap)",
 "fendo": "AbstractPlay gameslib differential (17,263 positions, 3 policies, 0 mismatches) + two designer diagrams pixel-transcribed (21/21 marked entry cells); 38 mutants; termination structural (193-ply bound, no cap)",
 "manalath": "AbstractPlay gameslib differential BOTH directions (10,289 positions, 0 mismatches, mapping proved bijective 61 cells/156 edges) + both designer diagrams executed + 2,400-case constructed sweep; 26 mutants",
 "lielow": "AbstractPlay gameslib + O'Dwyer's JS engine (3 implementations agree) — 61,103 + ~34,600 independent positions, 0 mismatches, incl. 21,146 exhaustive per-move crown edge cases; 62 mutants; termination proved (352-ply potential bound, no cap)",
 "neue_dame": "NO reference engine — anchored on all 4 composed problems from Abstract Games #18 replaying exactly (5 magazine errata proved, incl. an illegal printed move refuted against 3 rival rulesets) + TWO independent re-implementations (311,872 + 117,347 positions, 0 mismatches); 44 mutants",
 "taiji": "AbstractPlay gameslib differential (81,116 + 52,391 independent positions, 9 configs, 0 mismatches) + the rulebook's page-1 figure transcribed by TWO agents independently and replayed to its printed 13-10 score; 50 mutants",
 "terrace": "AbstractPlay gameslib differential (110,208 + 14,943 independent positions across all 8 option combinations in two modes, 0 mismatches) + the publisher's worked-example GIFs pinning branching factor; 57 mutants",
 "hexagonal_y": "AbstractPlay gameslib differential (74 games/8,409 plies + 18 games/1,103 positions, sizes 4-11, 0 mismatches; the oracle chains the arc greedily where we use a max-gap formula, so agreement is structural) + all four rule-sheet figures vector-decoded TWICE independently, incl. Figs 2/3 whose printed dots pin the arc itself (12/18 win, 8/18 non-win); win predicate swept over 675,456 rim subsets vs an independent minimal-window computation; drawlessness exhaustive (8,192/8,192 at n=3, vs 54,480/524,288 draws without the pairing invariant); termination proved, no cap",
 "blast_radius": "AbstractPlay gameslib differential (1,028 positions, both directions, 0 mismatches) + an independent from-scratch reference model (800 games/53,037 plies) + adversarial search under 3 hostile policies (1,260 games/36,646 plies, 0 stuck, 0 invariant leaks); all four figures vector-decoded (QA corrected a mis-read printed stack height); separation invariant proved ⇒ the ground-zero exception is vacuous; termination proved (lexicographic height vector, bound tight at the game-ending move), no cap; 28/28 + 26/26 mutants",
 "bounce": "EXHAUSTIVE 4×4 solve (29,602 positions, on-line repetition assertion never fired ⇒ cycle-freedom + drawlessness + a game value) + gameslib differential (523 plies, 439/440 forced rejections) + an independent brute-force movegen over 102 games/4,000 arbitrary/1,200 articulation-point boards, 0 mismatches; all three figures decoded twice by unrelated methods (vector paths vs raster sampling), incl. the sheet's own 11→20; termination proved (lexicographic group-size multiset), NO cap and no repetition rule; 25/25 + 28/28 mutants",
 "bamboo": "the rule sheet's Figure 2 decoded and its printed set of 4 available placements reproduced, after SIX candidate readings of the group-size clause were scored against both figures and exactly one survived (not the oracle's) + gameslib differential, which exposed a real ORACLE bug: `canPlaceAt` tests only the group the new stone joins, offering illegal placements on 15.1% of plies; termination proved, NO cap and no repetition rule; heuristic measured indistinguishable from no eval at the shipped settings and documented as such",
 "take": "EXHAUSTIVE side-2 solve + gameslib differential, which exposed a real ORACLE bug: `checkEOG` tests reds before blues, so a placement annihilating BOTH colours awards the win to the NON-mover (~3% of random games, ~40% on the smallest board); sheet-adjudicated to the mover. Known blind spot, recorded deliberately: a `before_other > 1` mutant SURVIVES the whole selftest — a real reachable bug at side 3 (15 hits in 2,500 games) that the exhaustive side-2 solve is structurally unable to exhibit; termination proved, NO cap",
 "minefield": "Figure 3's ANCHOR DISCRIMINATING POWER measured (kills 9 of 12 wrong glyph-set variants, blind to three incl. tall-orientation-only switches — Figure 2 prints only the tall orientations, so a literal transcription of the artwork would pass; the selftest was then shown to kill all three) + gameslib differential, which exposed TWO real ORACLE bugs: win detection using 8-adjacency (wins on purely DIAGONAL chains, 51/150 games) and `validateMove(\"pass\")` always throwing (its skip rule is dead code); built from the live 2026-05-17 sheet, whose PIE RULE has never been archived anywhere; termination proved, NO cap",
 "narrows": "gameslib differential CLEAN (0 divergences over 3,392 plies) + the no-capture branch proved VACUOUS on 551,853 + 4,553,496 constructed boards with a mutation control where deleting the clause correctly survives; the pie swap — which the oracle gives ZERO coverage of — is covered by constructed inputs pinned to board ground truth (the owner of Figure 1's top-left pit), after QA found the swap inverted every colour name in the caption and ANNOUNCED THE WRONG WINNER, with the selftest's only caption assertion encoding the identical wrong mapping; termination proved, NO cap",
 "invector": "gameslib differential (~9,000 plies, both directions, 0 mismatches — and its `validateMove(\"pass\")` genuinely works, so the skip rule got real coverage) + Figure 3's discriminating power measured (kills 8 of 10 wrong centre definitions; the two survivors killed by a bracketed sentence and a behavioural-identity proof, not by more figures); built from the live sheet, whose ENTIRE PIE RULE was added after every Wayback capture; the 4×3 board is structurally unable to exhibit the Manhattan-vs-blocked-path distinction (0.0% of plies vs 86.6% at 8×7), so paired with a directed search at a real size; termination proved, NO cap",
 "unane": "gameslib differential (~9,800 plies, both directions, 0 mismatches; its `checkEOG` independently agrees with our win-condition reading) + Figure 4 — the single artefact that decides the win condition, and one the only Wayback capture does not contain — decoded, with its discriminating power measured at 1 of 5 wrong readings killed; the gap closed by CROSS-SHEET adjudication: the designer's Narrows sheet states the identical clause with the word \"simultaneously\", proving it is a tie-break awarded to the mover; termination proved, NO cap",
 "necklace": "the drawlessness PROOF used as a bug detector — a live position contradicted step 1 and exposed a real, high-frequency move-generation bug in our own `encloses()` (one `seen` set shared across four flood fills ⇒ false enclosures silently deleting legal moves on 29.2%/48.8%/71.9% of plies at 5×5/7×7/9×9), found INDEPENDENTLY by both agents and nearly shipped as a fabricated \"genuine tie\"; Figure 3 is completely blind to it (both full illegal-placement sets are identical under the bug) + gameslib differential (~5,000 plies, 0 rule bugs — the oracle's odd-looking per-flood `seen` reset is load-bearing and correct, i.e. precisely the bug we had); termination proved, NO cap",
 "churn": "a PUBLISHED NUMBER as the primary anchor: side-5 game length measured 7,404 turns vs the designer's \"about 7,400\" (0.05%), an anchor that discriminates violently — a `<=` removal threshold NEVER terminates at that size and pre-merge minimisation gives ~660; it also refutes the superseded sheet's \"about 8,500\" at >5σ + gameslib differential (~10,800 plies, 0 mismatches: move-gen, the strict `<` and the post-removal EOG check all match) + Figures 1+2 measured to kill 7 of 9 wrong readings and to be blind to BOTH \"what counts as isolated\" readings, settled by the superseded 2025 sheet whose Figures 3/4 were redrawn precisely to fix when majority is counted; the exhaustive side-2 solve contains 0 multi-group and 0 multi-stone removals, i.e. cannot see the signature mechanic, so paired with a directed search; termination proved, NO cap",
 "halfcut": "all SEVEN rule-sheet figures decoded TWICE by unrelated methods (vector paths vs pixels) — character-for-character identical, all 11 printed group sizes and every printed verdict reproduced + gameslib differential (6,811 played + 720 planted positions, 10,858 legality adjudications, 0 rule mismatches, transpose control diverges) + an independent reference model (18,965 plies, 5 sizes); termination + drawlessness PROVED (lexicographic group-size multiset; Crossway theorem exhaustive to 5×5 = 5,735,478 boards), NO cap and no repetition rule; 42/42 + 27/27 mutants; adversarial QA verdict MERGE with zero edits",
 "clearcut": "distinctness from Halfcut PROVED (Figures 1-4 byte-identical artwork, Fig 4 opposite printed verdicts; rulesets disagree on 17% of crosscut placements) + gameslib differential vs the `clearcut` VARIANT (~4,300 positions + 1,536 constructed simultaneous crosscuts, 0 mismatches, 3 controls all diverge) + all 8 figures decoded twice; termination + drawlessness PROVED (the stricter legality clause is what makes the monovariant survive unconditional removal), NO cap; 3×3 solved exhaustively (7,631 states, 0 draws); 20/20 mutants twice; superseded 2023-07-18 sheet identified as a COMPLETELY DIFFERENT ruleset",
 "nakatta": "Figures 2 and 3 decoded independently twice and their printed counts (6 hard corners / 7 naked attachments) reproduced from first-principles predicates, with anchor DISCRIMINATING POWER measured (5 of 7 and 4 of 5 wrong readings killed; the edge-overhang shape invisible to Figs 1-2) + gameslib differential (~7,900 + ~6,300 positions, both directions, 0 disagreements; transpose control diverges on winner only) + drawlessness hardened (0 stalls in all 926,713 reachable and all 7,383,545 legal 4×4 positions, 16,000 greedy fills, ~7,000 adversarial games); pie swap covered by constructed inputs pinned to Figure 1's artwork; 26/28 mutants",
 "onager": "all five rulebook figures decoded from embedded artwork by two agents independently (exact to stack composition) + gameslib differential with the coordinate map proved by ADJACENCY ISOMORPHISM against the oracle's own graph (rot60/rot180 controls diverge; the mirror is a genuine automorphism and was rejected as evidence) + an independent reference model (100 complete games, 4 sizes, every move/position/terminal) + route-independence proved over 71,444 enumerated routes; three language editions diffed, exposing an unadvertised 2018 revision that ADDED a rule; 37/37 mutants after QA fixed a caption that conflated the two win conditions and a SEAT_NAMES mapping never pinned to ground truth",
 "yonmoque": "tile map derived from PROSE (census + the 2016 page revision) then confirmed by pixel-decoding the publisher's artwork on all 25 cells + an independent reference model (1,600 games/44,443 plies, both directions) + gameslib differential (550 games, 0 mismatches, ~10k invented illegal moves all rejected); D4-invariance asserted as a lemma with a non-D4 control diverging 40/40; five-outranks-four shown forced (574/574); ply cap proved REQUIRED (pacifist policy reaches it 12/12) and non-load-bearing (50,000 games, max 125 plies); 25/26 mutants",
 "nakatta_pro": "THE DESIGNER'S SHEET IS DEFECTIVE, proved three independent ways by two agents decoding the figures by UNRELATED methods (vector-path parsing vs 600dpi pixel classification): Figure 3 marks 7 illegal placements where Figure 2's glyph set implies 24. (a) The same pipelines reproduce the sibling Minefield sheet EXACTLY (13/13 reds, 0 extras) — a passing control on the same template; (b) a figure-INTERNAL contradiction needing no pipeline at all: Black at (5,4) and at (7,5) produce a byte-identical 3x2 window with the stone at the same relative position, yet only (7,5) is marked (two more such pairs exist); (c) a rigorous refutation — legality is monotone in the glyph set, so the MAXIMAL admissible closed set still leaves (0,1) and (7,5) legal, and isolating them needs a 2x5 window, larger than anything Steere has ever printed. Figure 2 implemented; all 17 omissions pinned. Containment PROVED (Nakatta-illegal > NP-illegal > Minefield-illegal, 0 violations / 39,690 placements, divergences 2,688 and 6,587) so the 'Middle-earth' framing is literally a theorem. Anchor power 43/43 wrong readings killed (QA's enumeration beat the builder's 12). Exhaustive solves 2x2/3x3/4x4 (2,394,331 states, 0 draws, 0 stalls); size^2 bound derived and tight. NO ORACLE EXISTS (no BGG, no gameslib, no BGA). Heuristic replicated 20-0 twice at independent settings; 24/26 mutants + a real caption survivor fixed",
 "slyde": "THREE published numbers matched (designer's 8x8 '16-23 moves each' -> 20.6; Ai Ai's 12x12 random playout '94 plies SD 4' -> 93.75 SD 3.80 over 1,000 games; Ai Ai's '528 distinct actions' = exactly 2x our 264 opening moves) + two INDEPENDENT gameslib differentials (builder ~9,300 plies / QA 8,869 plies over 630 games, sizes 4-12, both drive directions, a mirror policy forcing 302 symmetric plies and 10,712 state-change moves through the oracle's own validateMove, 0 mismatches; mapping proved by adjacency isomorphism AND a parity-flipping control that diverges at ply 0, while the parity-preserving half of D4 is a genuine automorphism and proves nothing) + the Kanare GROUPS figure transcribed by pixel classification (its caption kills 1 of 5 wrong readings, its printed label multiset kills 5 of 5 — measured) + the designer's worked example replayed move-for-move WITH a parity control proving the unmirrored line is illegal in this parity, so the replay cannot be self-fulfilling. EXHAUSTIVE 4x4 solve (1,607,132 states; monovariant asserted on all 4,397,292 edges of the state graph with a positive control on a synthetic 3-cycle; 13.34% honest ties). Anti-mirroring lemma verified over all 130,816 symmetric positions / 2,093,056 toggles — the shipped test had covered only the 65,536 left-right family, half the domain of the lemma it proved. Heuristic load-bearing and size-dependent (cutoff fires on 46.8%/24.1%/0% of rollouts at 12x12/10x10/8x8; 0 heuristic calls at 8x8, which is why that head-to-head is exactly 0.500). 34/34 + 29/29 mutants",
 "cairo_corridor": "72-pentagon Cairo tiling DERIVED analytically then verified twice independently: (a) all three embedded figures segmented by pixel classification recovering exactly 72 regions each, 72/72 bijection, 156/156 interior + 48/48 boundary edges probed (2*156+48 = 360 = 72*5), no overlaps or gaps, 25 degree-4 vertices confirming corner-touching cells are NON-adjacent; (b) an adjacency-ISOMORPHISM check against the oracle's hand-written neighbour table — which never touches move-gen — 0 mismatches / 72 cells and all four side sets identical, with a swap-side-NS control diverging on 72/72. Every printed figure reproduced cell-for-cell incl. captions (14-11, 14-13, and Ex 3's three components of sizes 4/2/2). gameslib differential 3,120 plies, 0 mismatches; rot180 proved a genuine automorphism (a lemma, not a gap) while mirror/partner/shift controls diverge hard. THE DEAD-ZONE READING: we allow placements outside the corridor, gameslib forbids them (9.6% of all legal moves, 71% of finished games end with an empty dead zone) — settled by the literal EN *and* JP text, the 'adjacent to it' qualifier and BGA's help page, AFTER QA DISPROVED the builder's own piece-count justification by making AbstractPlay's restricted implementation replay the 60-placement witness game (60/60 accepted, 0 rejected: restricted max = open max = 60, so the box contents cannot discriminate). Ties honest and reachable (11.0%). NO heuristic, with the measurement that justifies it (0.958 vs none at a forced cutoff but 0.521 at the platform default, where the cutoff fires on only 5.3% of rollouts). Figures kill just 2 of 11 side-set variants — the gap is closed by structural assertions, which kill all three",
 "hexentafl": "the two figure ambiguities the builder honestly flagged (throne 'three NON-ADJACENT sides' vs literal 'any three'; corner 'the two rim neighbours' vs 'any two of three') settled not by oracle agreement but by a THIRD implementation QA found — SkudPaiSho (2019, five years older than and independent of gameslib), which the designer himself announced and thanked the author for, whose source reads `/* King on Throne captured by 3 non-adjacent Attackers */` and tests the alternating triples + gameslib differential 56,130 plies (both sizes, both first-player orders) PLUS a constructed-position differential of 264 positions / 8,004 move-results covering what random play cannot reach — which earned its keep, since the random harness MISSED an injected throne_adjacent bug over 991 plies while the constructed one caught all three throne/corner mutants. Mapping proved by adjacency isomorphism: at 4x4 the asymmetric defender triple cuts D6 to D3 so exactly 6 of 12 maps are automorphisms and all 6 valid controls diverge at ply 0; at 5x5 the whole group is an automorphism so orientation is provably UNOBSERVABLE (a lemma, not a gap). orientation:'flat' pinned by measuring the six corner attackers' bearings from the throne (+/-90.2, +/-31, +/-149 degrees — corners up/down, none at 0/180; 0.2 degree residual against a 30 degree separation). Decisive-outranks-counters: 0 failures over 4,000 decisive terminals re-scored with ply=1e9 and a poisoned reps table. Reachability measured per win condition (escape 59.0%, regicide 39.9%, stuck-attackers 0.70-1.03%, repetition and cap 0 in 7,600 games ⇒ selftest-only). The rulebook has NEVER been archived by Wayback. 26/26 + 17/18 mutants (the survivor proved a semantic no-op over 597,536 states)",
 "carnac": "the HUCH! 2014 rulebook's printed FINAL-SCORING figure decoded independently by both agents (grid-line detection + per-cell classification, then QA's own transcription) agreeing cell-for-cell on all 126 squares and reproducing all six printed numbers — red (8,5,4,4,4) vs white (8,6,4,3,3), 5 dolmens each, 'Weiss gewinnt' — a SELF-CHECKING decode whose own printed totals caught two misreads. Its DISCRIMINATING POWER was measured and it is BLIND to the game's most important rule (5 vs 5 dolmens means count-first and size-lex agree), a gap closed by constructed positions. FOUND gameslib RULE BUG #13: `compareDolmenScores` omits the PRIMARY criterion (the NUMBER of dolmens) and compares only sorted size lists, flipping the declared winner on 46.0%/33.3%/17.3% of complete games at 8x5/10x7/14x9 (QA's independent 150-game measurement; builder 42.5/30.8/19.8 — same within noise) in replays where both engines agreed on every dolmen SIZE; adjudicated against the oracle by four textual sources plus an INTERNAL CONTRADICTION in the rulebook's own GAME TIPS (merging 3+3 into 6 'minimizes points already scored', which is nonsense under size-only). 52-game/3,034-position differential, 0 mismatches, driven from our side so the oracle had to ACCEPT (0 rejects). CONFIRMED `carnac.ts` is CLEAN of the systemic dead-skip: in a real tip position `validateMove(\"pass\")` returns {valid:true}, all 469 passes accepted. New lemma: a topple consumes 2 empty cells and frees 1, so a topple can NEVER fill the board — which makes our two-ply split provably equivalent to the oracle's bundled turn. Bound 2*STOCK-1 = 55 derived and TIGHT (55 observed); no cap, no counter of any kind exists. QA's mutation matrix found the builder's 28/28 missed a whole hole — render()'s CONTENT payload was unasserted (7 live mutants incl. `render_owner_flipped`, which draws every square in the opposite colour, and in Carnac the colour map IS the score); 67/67 after the fix. No heuristic, justified over COMPLETE games (rollouts reach a real terminal on 100/98.4/92.5% of plies)",
 "amoeba": "THE ENGLISH RULEBOOK IS INCOMPLETE and the JAPANESE edition of the same nestorgames sheet carries a whole end-of-game rule it omits (threefold repetition ⇒ more controlled stacks wins, level ⇒ honest draw) — the builder had ALREADY written, tested and documented an INVENTED ply-cap draw before reading AMOEBA_JP.pdf, and gameslib has no repetition rule either, so nothing but the other-language edition would have found it; QA confirmed the quote verbatim (after suspecting a misattribution and RETRACTING) and found the designer's own nakajim.net pages carrying the same paragraph, a 3rd and 4th attestation. THE KERNEL COUNTS toward stack height, pinned by the oracle's opening count as a clean discriminator (counting it = exactly 52 moves, excluding = 46) and settled more strongly by the JP text. THE ENGLISH SETUP FIGURE IS WRONG (9 white discs where its own MATERIAL list and the 180° symmetry of the other 36 points require 10) — derived independently by both agents via two different pixel methods with the JP edition's independently drawn figure as the PASSING CONTROL (11+11); `pdftocairo -svg` is useless here (5 embedded rasters, 0 disc paths). Figures CANNOT discriminate the sow order (the pile both editions draw is palindromic white-black-white ⇒ kills 0 of 2 readings), proven bottom-first on a non-palindromic pile instead. Left-right mirror ambiguity is a LEMMA not a gap ((q,r)→(-q-r,r) is x↔y in cube coords; predicted before testing — mirror passes 284 plies while 60° and 180° diverge AT THE SETUP). 180-game/8,764-ply differential both drive directions + 193 constructed positions/13 hand witnesses, 0 mismatches; harness vacuity 7/7 injected bugs caught. Rates over COMPLETE games (20,000): kernel 96.36%, immobilisation 3.58%, repetition 0.065%, PLY_CAP 0. Found a 13th gameslib issue (`validateMove` accepts NON-STRAIGHT destinations at the right distance). 50 mutants, 4 real survivors — incl. THE 10th INSTANCE of the decisive-outranks-counters family in a NEW SHAPE: the guard was VACUOUS because both poison positions had the winner AHEAD on the stack tiebreak, so a mutant resolving repetition BEFORE the wins passed all 335,077 checks; fixed with positions where the winner TRAILS. First wave in six with NO silent revision (both editions md5-identical to their only captures)",
 "six": "NO ORACLE EXISTS (gameslib has no Six) — the only such game in its wave, so the anchor is the publisher sheets plus exhaustive enumeration. MY BRIEF WAS WRONG ON THE CENTRAL MECHANIC and the builder overrode it: all four official sheets PERMIT splitting the group and the split IS the capture (the no-split reading is the FoxMind simplification); my brief was also wrong that a nestorgames edition exists and that any sheet has a stalemate rule. FOUR rule generations found (2008: 19 tiles/ONE start stone/2-or-4p → 2013: 21 tiles/TWO start stones → 2022 → 2024), the last recovered by QA from the LIVE Shopify CDN after the builder worked only from the archived TYPO3 tree — it PRINTS three of the shipped 'interpretations' outright and contradicts one rule (Black first vs our Red), proven immaterial by a lemma (180° rotation about the start tiles' shared edge = colour swap ∘ lattice symmetry). Its EN and DE sections CONTRADICT each other on the tie-break (which part is REMOVED vs which STAYS); the German is coherent and ships. Main anchor: the 'Chance to beat' figure settles FOUR readings at once (smaller group captured; captures COLOUR-BLIND since the crossed-out group holds the mover's own tile; the lifted tile is never captured; whole groups go) and marks only the PROFITABLE lifts. Shape predicate cross-checked against an independent algebraic predicate over ALL 54,264 six-cell subsets with the census (6 rows/5 circles/10 triangles) hand-derived, then re-derived by QA which enumerated the template set from scratch in cube coords (byte-identical) and found an EIGHTH wrong reading the builder missed ('circle = any closed 6-loop' admits 12 extra shapes) plus a real gap (the 7x3 test region fits only 1 of 3 row directions). TERMINATION: round two genuinely CYCLES — QA exhibited an explicit 4-ply cycle returning a byte-identical position with 0 tiles lost — so the 100-ply capture-free draw is provably NECESSARY (PLY_CAP is not independent of it) though it appears in NO sheet and is labelled as such; fires 0/400 games, counter max 19/100, max reachable ply 3,271 vs cap 3,272 (NOT off by one). 42 mutants, 39 killed, both survivors proved no-ops. QA built its OWN engine from the sheets and ran 48 games/2,636 plies incl. ~1,000 round-two plies, closing the hole that MCTS never reaches round two at all. No heuristic (cutoff 19% over complete games; the ply-0 snapshot reads 33% — trap avoided)",
 "quax": "'WAYBACK IS THE ONLY COPY' WAS WRONG AND IT MATTERED: the dead-looking 386-byte di.fc.ul.pt URL is a JS REDIRECT to a live 39,018-byte page carrying Bill Taylor's verbatim 1992 `RULES OF LINK` post — 'north-south for black, east-west for white' — so the designer's OWN first and most explicit statement AGREES with igGameCenter, gameslib and this package, and NO Wayback capture contains it (6 captures, 5 distinct digests, 2003-2025, all byte-checked). The builder's apparent 'designer contradicts every implementation' finding was really the 2000 prose vs the designer's own 1992 rules ON THE SAME PAGE. The frame contradiction is real but IMMATERIAL, proved three ways (transpose is an automorphism exchanging the goals with an empty start; a value anti-automorphism over all 1,937 3x3 states; a transposed-relabelling differential control that DIVERGED as required) while the Klein-group flip control lies INSIDE the symmetry group and cannot fail — stated, not banked. New anchor: the 1992 COMPLETED 4x4 game decoded two independent ways (an arithmetic argument from 'Black has played 7 moves and white 6' forcing a unique bar assignment, plus glyph geometry landing on the predicted midpoints), with its power MEASURED (kills 3 of 5 wrong readings, blind to two, both covered by igGameCenter). THE CROSSING RULE IS OVER-DETERMINED and the rival reading provably cannot matter: the 1992-literal 'opposite color' wording offers an extra bar on 16.594% of plies over 490 complete games and EVERY ONE is connectivity-redundant, so the readings cannot differ in game value at all. Implemented STRUCTURALLY (links keyed by 2x2 square ⇒ a crossing bar is inexpressible). `quax.ts` is CLEAN, not bug #14: it has no `pass` and no no-legal-move case, but a stuck position is UNREACHABLE (a checkerboard square offers a bar to BOTH colours — exhaustive over all 16 block colourings). Bound 1+n²+(n-1)² derived and ATTAINED (14/14 at 3x3 over 8,000 games); the `swap` ply places NOTHING, exactly the off-by-one that bit three previous waves. 10,969 differential plies across ALL EIGHT sizes (QA closed the builder's 7/9/13 gap), move-set equality every ply, oracle forced to ACCEPT, 400 spurious moves rejected. Pie swap TRANSPOSES (c,r)→(r,c), verified for every opening cell at all 7 sizes — and the 3x3 pie-rule game value is BLIND to a recolour-in-place swap (-1 either way), so what kills that mutant is the anti-automorphism (795/1,937 violated, reproduced to the digit by both agents). Drawlessness exhaustive only to 4x4 and honestly flagged, backed by 26,600 complete games/839,687 plies/0 draws and a proof the [0,0] branch is DEAD. 42 mutants, 40 killed — incl. THE WORST INSTANCE YET of the library's unpinned-attribution family: `returns()`'s seat test was pinned by NOTHING (shape + zero-sum are blind to WHICH seat gets +1), so flipping it survived all 585,929 checks — 100% of finished games, every stored result and Glicko update inverted and MCTSBot playing to LOSE while the board reads correctly. No heuristic, justified STRUCTURALLY (the eval is consulted 0/200 times at 5x5 with the shipped max_rollout, so the 24-0 win there was never about the eval)",
 "clusterfuss": "Steere's Figures 5 and 6 SOLVED EXHAUSTIVELY (both published puzzle claims confirmed move for move, by two independent engines) + gameslib differential (658 positions + 502 on the shipped code, 0 mismatches, 4 injected bugs each diverging 25/25) + an independent model over 270 games/9,333 positions across 5 sizes; turn-skipping proved vacuous exhaustively (590,812 board×player pairs + 523,175 reachable states, 0 immobile); full solves of 2×2/3×3/4×4; 29/29 + 35 mutants",
}
# Browser / UX eyeball status (default: rendered by the generic renderer, never
# individually eyeballed -- logic is conformance-tested either way).
BROWSER = {
 "alquerque": "✅ verified (5×5 alquerque board + lines — shares the Bagh-Chal/Fanorona path)",
 "bagh_chal": "✅ verified (alquerque board + lines, placement, capture/5 caption)",
 "lasca": "✅ verified (NEW stacking renderer — towers as layered bands + height badge)",
 "crazyhouse": "✅ verified (drops + reserve trays, capture→drop lifecycle)",
 "go": "✅ verified (NEW territory scoring — Pass button, capture, live komi score)",
 "shogi": "✅ verified (9×9 setup, reserve trays, promotion picker)",
 "mini_shogi": "✅ verified (5×5 setup, reserve trays — shares the Shogi UI path)",
 "nine_mens_morris": "✅ verified (board diagram + lines, placement, mill log)",
 "dou_shou_qi": "✅ verified (river/traps/dens now colour-tinted)",
 "einstein": "✅ verified (NEW dice — roll shown in caption, matching stone highlighted, re-rolls each turn)",
 "fanorona": "✅ verified (alquerque connecting lines drawn)",
 "kalah": "✅ verified (mancala pits + counts, extra-turn after store landing)",
 "onitama": "✅ verified (NEW card UI — 5-card strip with movement-pattern grids, pick→move flow)",
 "oware": "✅ verified (seed counts + own-row clicking correct)",
 "pentago": "✅ verified (quadrant divider lines + 8-option rotation picker)",
 "rolit": "✅ verified (NEW >2-seat UI — 4 player chips/colours, full P1→P4 round)",
 "quoridor": "✅ verified (NEW wall primitive — ghost slots in grooves, place→solid wall, goal tints)",
 "chinese_checkers": "✅ verified (full 6-pointed star, all SIX seat colours, step+jump)",
 "twixt": "✅ verified (NEW overlay primitive — bridges drawn over cells + owner edge tints)",
 "xiangqi": "✅ verified (UI review: legible, uncramped)",
 "janggi": "✅ verified (UI review: legible, palace pieces correct)",
 "y": "✅ verified (NEW triangular-hex polygon board renders cleanly)",
 "yote": "✅ verified (5×6 board, drops with hand count, capture flow)",
 "abande": "✅ verified (drops on both boards, stack move recomputes the score caption, 2-stack tower + height badge)",
 "attangle": "✅ verified (central void as dark 'x', one-click placement, counter-only tray falls through, 3-click capture logged b1+d7xb5)",
 "fendo": "✅ verified (NEW board.fences primitive — the fence bar lands on the edge the move log names; two-click move-then-fence flow + 'Place a fence' picker)",
 "manalath": "✅ verified (NEW reserveOwners — both trays show R red / B blue; a stone from seat 0's B chip lands blue)",
 "lielow": "✅ verified (walk-off as labelled buttons — the crowned stack's reads 'RESIGNS (your king)'; a second click on a selected stack is inert; ♚ + height badge)",
 "neue_dame": "✅ verified (12+12 on the dark squares, bashni-identical tower render, move log 'c3-d4')",
 "taiji": "✅ verified (three option dropdowns; 121 cells at 11x11 with no phantom column; two-click domino; log 'k11(L)-k10(D)')",
 "terrace": "✅ verified (8 levels legible on every square incl. the highest after the contrast fix; size-scaled piece discs 1-4; goal corners tinted per seat)",
 "hexagonal_y": "✅ verified (127 cells at side 7; ONE click on a rim cell places TWO stones and logs 'g1+g13'; rim tints; rules modal 3 tables, 0 raw markdown)",
 "blast_radius": "✅ verified (91 cells at side 6; one placement tints exactly 7 cells = ground zero + 6 neighbours, i.e. radius 1 incl. ground zero; stack towers with height badges; caption tracks stacks/checkers)",
 "bounce": "✅ verified (64 cells, 30/30 with the four corners empty exactly as Figure 1; teleport move accepted, log 'b1-a1 (1→2)' showing the group-size change)",
 "clusterfuss": "✅ verified (64 cells, full 32/32 checkerboard; capture by replacement 'R 1,0x0,0' takes Blue to 31; rules modal 4 fenced blocks + 1 table, 0 raw markdown)",
 "bamboo": "✅ verified (wave-18 browser check; details not recorded per-game)",
 "take": "✅ verified (wave-18 browser check; details not recorded per-game)",
 "minefield": "✅ verified (wave-18 browser check; details not recorded per-game)",
 "narrows": "✅ verified (wave-18 browser check; details not recorded per-game)",
 "invector": "✅ verified (wave-19 browser check; details not recorded per-game)",
 "unane": "✅ verified (wave-19 browser check; details not recorded per-game)",
 "necklace": "✅ verified (wave-19 browser check; details not recorded per-game)",
 "churn": "✅ verified (wave-19 browser check; details not recorded per-game)",
 "carnac": "✅ verified at BOTH 10×7 (70 cells) and 14×9 (126 — the largest board this renderer draws): the 4-way orientation picker fires on a single-cell click with untruncated labels ('Red up · N/S→Blue · E/W→Red'), and its 'Red up · N/S→Red' option empirically CONFIRMS QA's D2 finding that a topple can show the colour that was standing; a toppled menhir renders as two cells joined by a dark bar reading as ONE stone while a standing one carries a diamond, unambiguous even at 14×9's smallest cells; the 'Leave it standing (they place again)' button correctly returns the turn to the PLACER with stock unchanged; move log 'stand e4 (Red up, N/S Blue, E/W Red)' / 'topple e4 north onto e5-e6 (Blue up)' / 'leave c3 standing'",
 "amoeba": "✅ verified (37 hexes, tower glyphs as stacked bands, legible 'K1' kernel labels on the tower, caption carrying stack counts and BOTH kernel positions, sow's multi-cell last-move highlight reading as one line) — and crucially the NOVEL move-vs-sow picker, a bare move and a '=S' sow sharing the SAME two cells, which no shipped game had exercised: both options render as 'Move whole stack' / 'Sow along the line' and each plays what its label says ('0,1>0,3 sow x2' vs 'move x1')",
 "six": "✅ verified end to end on a GROWING, negative-coordinate board: 2 start tokens + 8 frontier targets, the cell list growing 10 → 129 as the cluster drifts, hand counts tracking (20→18), reserve trays present in round one and VANISHING in round two, both captions, 40 plies driven to round two, select-then-move with correct per-source filtering (82 targets offered), and a capture landing ('Red -36,0→-36,1 (captures 1)', 42→41 tokens). ⚠ COSMETIC LIMIT FOUND: the auto-fitting viewBox has no minimum span or padding, so a long thin cluster (which degenerate play reaches) scales down to an unreadable strip — rules, containment and clicking unaffected; worth a Board.jsx follow-up for the whole growing-board family. The equal-split =CHOICE picker (2.07% of round-two plies) was traced statically but not reached by hand",
 "quax": "✅ verified at 11×11 (121 cells, matching the oracle's 121 opening moves) and 15×15 (225): 18+18 edge cells with FOUR BLENDED CORNERS (a corner belongs to both adjoining edges), algebraic move log ('c6', 'h8', 'f3-g4', 'swap (pie)'); the PIE SWAP visibly TRANSPOSES the stone from (2,5) to (5,2) and recolours it, returns the turn to Black and does not reappear — the exact check QA's whole pie section depends on, and the bug shape fixed in rhode/cation; the LINK OVERLAY draws as a clearly legible line in the mover's colour at both sizes; and the CROSSING PAIR offers no target at all once a bar occupies the square (a dead click, as QA predicted)",
 "nakatta_pro": "✅ verified (169 cells at the 13×13 default; red top/bottom + blue left/right edge bars, dashed last-move box; placements log 'g7'/'g9'/'d4'/'j10'; caption 'Black to move (top–bottom)' — the edge pair QA pinned to Figure 1's artwork)",
 "slyde": "✅ verified (144 cells at the 12×12 default, board starts COMPLETELY full — 144 discs in a checkerboard; a swap logs 'f6-f7' and the frozen piece gains an inner ring, so mobile vs fixed is legible at a glance; caption carries the compacted group tally 'White 4 +68×1 · Black 4 +68×1'. The from==to state-change move was traced through Board.jsx but not clicked — it needs a symmetric position)",
 "cairo_corridor": "✅ verified (72 pentagons in the true Cairo tiling; NEGATIVE-ORIGIN polygons board — viewBox auto-fits to -43.6 -63.6 427×427, the first such board in the library, no clipping and correctly centred; apex hit-testing exact on 5 probes incl. 2,5 and 1,4 despite interlocking tiles; shape:'fill' pieces keep visible cell strokes; the pale dead-zone grey reads clearly against the green corridor; move log carries the orientation letters '0,0 N'/'5,5 E')",
 "hexentafl": "✅ verified (37 hexes at size 4 with orientation:'flat' — corners straight UP and DOWN exactly as the rulebook figure measures; 6 blue attackers on the six goal-highlighted corners, ♚ king glyph on the tinted throne, 3 red defenders on the throne's N/SE/SW neighbours matching the setup figure's only asymmetry; caption 'Defenders to move', and defenders move first)",
 "halfcut": "✅ verified (121 cells at 11×11, red top/bottom + blue left/right edge bars; placements log 'f6'/'f7'; a constructed capture removed two blue checkers)",
 "clearcut": "✅ verified (121 cells at 11×11, same edge-bar render as Halfcut; placements log 'f6'/'f7')",
 "nakatta": "✅ verified (169 cells at the 13×13 default; caption 'Black to move (top–bottom)'; placements log 'g7'/'g9')",
 "onager": "✅ verified (91 hexes at side 6; 13 red + 13 white discs and exactly 3 grey lakes; the lake phase runs first and WHITE moves first after it, log 'lake e6/f7/e5' then walk 'j2-i3'; jump onto an enemy builds a 2-tall tower with a height badge)",
 "yonmoque": "✅ verified (25 cells; tint census exactly 8 first-player / 12 second-player / 5 neutral, matching the publisher's artwork; placements log '@2,2' and the in-hand counts decrement)",
}
DEFAULT_BROWSER = "— generic renderer (logic tested; not individually eyeballed)"


def board_shape(spec):
    b = spec["board"]
    if b["type"] == "square":
        return f"{b['width']}×{b['height']}"
    if b["type"] == "hex":
        return f"hex {b.get('shape', '')} {b.get('size', b.get('width', ''))}".strip()
    return f"polygons ({len(b.get('cells', []))})"


def main():
    rows = []
    for pkg in sorted((ENGINE / "games").iterdir()):
        if not pkg.is_dir():
            continue
        man, g = load(pkg)
        uid = man["uid"]
        shape = board_shape(g.render(g.initial_state()))
        rows.append((
            man.get("category", "Other"), man.get("name", uid), uid, shape,
            "✓" if (pkg / "selftest.py").exists() else "·",
            "✓" if (pkg / "rules.md").exists() else "·",
            ANCHOR.get(uid, "conformance"),
            BROWSER.get(uid, DEFAULT_BROWSER),
        ))
    rows.sort(key=lambda r: (r[0], r[1]))
    cats = {}
    for r in rows:
        cats.setdefault(r[0], []).append(r)

    L = []
    L.append("# Game Status — bundled library\n")
    L.append("> **Living catalogue of every bundled game: board, how its rules were "
             "verified, and its testing state.** Auto-generated by "
             "`engine/tools/gen_game_status.py` (board shape + selftest/rules columns "
             "are read live; verification anchors + browser status are curated in that "
             "script). Regenerate after adding a game.\n")
    L.append(f"**{len(rows)} games.** Every game passes the engine conformance harness "
             "(`agp validate`: random self-play to a terminal, purity, serialize "
             "round-trip) and runs in the full suite (`engine/tests/test_games.py`). The "
             "**Anchor** column is the *independent* correctness check beyond conformance "
             "(a published perft/result, a differential vs a reference engine, or an "
             "adversarial rule review).\n")
    L.append("**Legend** — Selftest: ✓ ships a `games/<uid>/selftest.py` (pure-stdlib "
             "anchor run by the suite). Rules: ✓ ships a one-page `rules.md` (rules as "
             "implemented). Browser/UX: ✅ eyeballed in-app · 🔍 under review · — "
             "rendered by the generic renderer but not individually eyeballed.\n")
    for cat in sorted(cats):
        L.append(f"\n## {cat}\n")
        L.append("| Game | Board | Selftest | Rules | Verification anchor | Browser/UX |")
        L.append("|---|---|:--:|:--:|---|---|")
        for (_, name, uid, shape, stf, rul, anc, brw) in cats[cat]:
            L.append(f"| **{name}** (`{uid}`) | {shape} | {stf} | {rul} | {anc} | {brw} |")
    L.append("\n---\n")
    L.append("## Capabilities & known gaps\n")
    L.append("- **Shipped UI capabilities:** square/hex/polygon boards, the `=CHOICE` "
             "move picker (promotion), pie-rule/pass/action buttons, a move-log, the "
             "freeform (honor-system) mode, and an **off-board reserve + drops** "
             "(Crazyhouse, Shogi — seat-colored reserve trays + click-to-drop).\n")
    L.append("- **Next capability frontiers** (see `GAME_BACKLOG.md`): **stacking** "
             "(Tak, DVONN, TZAAR), **Go territory scoring** (the liberty core already "
             "ships via Atari Go/NoGo/Gonnect/Tanbo), point-and-line boards (TwixT), and "
             "the >2-seat UI (Chinese Checkers).\n")
    OUT.write_text("\n".join(L) + "\n")
    print(f"wrote {OUT} ({len(rows)} games)")


if __name__ == "__main__":
    main()
