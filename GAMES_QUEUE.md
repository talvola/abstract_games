# Game Factory — Queue & Status

On-disk state for the autonomous game-integration loop (the "factory"). The
universe map and capability gaps live in `GAME_BACKLOG.md`; this file is the
*queue* and the *human-escalation digest*.

---

## ⭐ SESSION HANDOFF (read this first) — updated 2026-07-21 (AG-magazine tier-2 wave 7 → 362 games)

### ✅ AG-MAGAZINE WAVE 7 COMPLETE (2026-07-21) → **362 games**, #359–362
Tier-2 pool screened by a scout agent (18 candidates from issues 2–16 + Winkel-Advokat i23) —
**dedup came back CLEAN across all 18, none a clone.** Built the 4 best-anchored; all deep-QA'd,
browser-verified, one commit each. NOTE: this session's scratchpad survived AND the prior
session's `agmag/` was still on disk — re-fetched only the 11 missing issues (2–5,11–16,23).
Session hit the **Fable 5 usage limit** early → Erik switched to **Opus 4.8**; all agents
relaunched fine on Opus (co-author line = "Claude Opus 4.8 (1M context)").
- **domain #359** (`a5f6c22`) — Larry Back / Parker Bros 1983 (AG#12): 9×9, 26 reversible
  polyomino tiles/side, orthogonal touch-flip (NOT Reversi — no outflanking/lines), most-covered
  wins, honest draw; basic/intermediate/advanced options. QA MERGE 0 fixes: independent tile-set
  reconstruction cell-for-cell + from-scratch orbit oracle reproduced 1,149 raw / 171 symmetry
  opening moves (sym-diff 0). palette + piece.shape:"fill". BGG 754.
- **vai_lung_thlan #360** (`9f648b4`) — Mizo single-lap sowing (Shakespear 1912; AG#12): 2×6/5,
  single-lap, origin-inclusive loop (12-seed always captures), backward chain-of-singles capture,
  30-30 honest draw. QA MERGE 0 fixes: sowing orientation PINNED by brute-forcing the printed
  endgame (only one loop replays 4/2/5/1/6 to the 30-30 terminal). oware render. BGG 39620.
- **sleeping_beauty_draughts #361** (`6c87e8f`) — Dornröschendame (Gering 1986; AG#14): 8×8
  draughts, forward-men/backward-lady capture, max-majority by count, one-lady rule w/ frozen
  "sleeping beauty" (label-only piece), wake-on-lady-loss + jump-of-joy, Royal Privilege,
  anti-loop, piece-count scoring. QA MERGE 0 fixes: all 5 composed problems pixel-read from
  figures + replayed to printed results (incl. P3 "Gundi" 37-move + P4/P5 zugzwangs); beauty
  owner-by-rank confirmed. draughts render. No BGG (magazine-only).
- **ley_lines #362** (`7cac2ad`) — Eric Solomon 2019 hex route-finding (AG#17): 18×18 pointy-top
  hex, random zone-quota deal (has_randomness), ring step/jump-chain, complete-line×2 bonus gated
  on a preceding step, honest draw. QA MERGE-WITH-FIX: resolved 63-vs-64 stones — article says
  63; phantom 64th (false blob from the "2" label at empty (10,8), off both ley-lines) removed
  from selftest. polygons 324-hex + zone tints + ring-on-stone label. Non-blocking: "to or from
  a vacant cell" step wording ambiguous, permissive reading documented. Magazine-only.
**Wave-7 lessons:** (1) tier-2 dedup was clean — the traditionals (Vai lung/Sleeping Beauty)
are genuinely distinct from our existing mancala/draughts families (verified vs closest rules.md);
(2) a game whose sowing/geometry is view-ambiguous in prose can be PINNED by brute-forcing a
printed problem against all orientations (Vai lung) — stronger than trusting the CW/CCW label;
(3) figure-derived stone counts can carry false blobs from nearby numeric labels (Ley Lines
64→63) — cross-check the printed count; (4) my pinchtab smoke helper must click QUICK PLAY
before typing in the search box (else it types into the login email field → "no cards" false alarm).

### ▶▶ NEXT (wave 8) — build-ready bench from the wave-7 scout (full report in
### scratchpad/agmag/wave7_scout.md; all sources on disk or one fetch away):
1. **Orbit** (i12 `12*`, Steven Meyers) — 16×16, 8-way groups, half-orbit=no-play zone / orbit=
   capture-enclosed, territory scoring, pie rule. Build the Half-Prohibition variant. Moderate
   (enclosure topology + prohibited-zone state; needs ply cap). Rules issue_12.txt L3184-3222;
   diagrams+puzzle L3229-3339.
2. **Winkel-Advokat** (i23, RESCUED from defer) — French Schmidt rules at scratchpad/winkel_fr.pdf
   /.txt (+ figures winkelfr_pg-2.png). 2p rook-detour drop on a numbered board + orthogonal
   checkers-jump capture. Residual gap: exact 8×8 value grid (concentric rings 2/4/8/16/32 —
   pixel-read a straight-on board photo: eBay 386603904922, spiele-check.de/2839).
3. **Hi-Jack** (i14 `14*`, Barrie Evans) — 8×8 stack-influence placement, piece.stack render,
   two annotated sample games as anchors (issue_14.txt L2039-2117 rules; games L2121-2607).
4. **Sadéqa** (i16 `16*`) + **Ot-tjin** (i14 `14*`) + **Super Halma** (i15 `15*`) + **Layli
   Goobalay** (i13 `13*`) — the remaining bench (2 mancalas, a relay-fish mancala, a long-leap
   Halma). All build-ready; details in wave7_scout.md.
DEFER pool (need a fetch or new render primitive): Mamba (mambagame.com setup diagram), Selus
(build Sadéqa instead), Lightning (needs a NEW arc-mark Board.jsx primitive), MEM (reactive
"blocking announce" breaks move-in-legal_moves), Pagoda (heaviest, no anchor), Gle'x/Phalanx
(new render + weak anchors), Strat (fort geometry diagram-only), Chebache (rules recovered to
scratchpad/chebache_rules.html but proprietary zigzag board).

### (prior handoff) ✅ AG-MAGAZINE WAVE 6 COMPLETE (2026-07-19c) → **358 games**, #355–358
All 4 staged candidates built + adversarially deep-QA'd + browser-verified, one commit each.
NOTE: old-session scratchpads did NOT survive this time (/tmp cleared) — all agmag sources
re-downloaded to this session's scratchpad `agmag/` (issues 17/19/22/24 + sanqi_sdg.pdf +
entrapment_boardspace.html). Re-fetch pattern unchanged (abstractgames.org uploads URL,
browser UA).
- **xyz_chess #355** (`f4cdf3a`) — Hewson 4×4×4 3D chess (AG#24 primary + AG#19 pawn blurb):
  K ortho-only, B 12 planar diagonals, N pure triagonal, level-locked Legan pawns, edge-pawn
  two-step. Gold anchor = 22-move Hewson–Mandoshkin annotated mate replayed exactly (the three
  double-step CAPTURES in the record force the edge-pawn readings). QA MERGE 0 fixes: ~75k-
  position from-scratch differential, 0 mismatches; perft 27/729/22651.
- **sanqi #356** (`b024b00`) — L. Lynn Smith 2003 shared-type hexhex (SDG designer rules
  primary + AG#17 reprint = same ruleset): place/majority-replace (+2 rule), one-turn immunity,
  circle/line/triangle-6 wins with end-of-own-turn timing. QA MERGE 0 fixes: 11,309-pos
  differential; §2.32 worked example discriminates +2 from bare majority; §5.2 Triangle Trap
  replayed. Replacement-churn honest-draw backstops (documented as impl notes). BGG 37001.
- **entrapment #357** (`22977d3`) — Gowell 1999 (Boardspace rules + Java impl mirrored
  method-for-method): roamers/barriers/jump-flip/immediate-capture/mandatory-escape; no
  voluntary flip (absent from play + reference — documented). 7×7|6×7 × 3|4 roamers options.
  QA MERGE 0 code fixes: Java-transcribed oracle, 520 games / 180,453 positions lockstep, 0
  mismatches; honest draws reachable post-exhaustion (cap load-bearing). Doubled-grid polygons
  (grooves = clickable cells; Quoridor walls primitive NOT reusable — single-edge + owner +
  flip state). BGG 12533.
- **jed #358** (`50aeff4`) — Thompson/Handscomb 2021 (AG#22): Jade objectives + J-E-D cycle +
  declare/swap pie. Colouring "JED"[(c−r)%3] pixel-proven; double-completion PROVEN impossible
  (crossing lemma + 195k probes). **QA MERGE-WITH-FIXES — real bug: win gate at ≥18 stones per
  printed "Cross needs 19", which is a magazine ERRATA (6th find): 11-cell short diagonal wins
  via corner double-counting, anchored by the historical Jade pbmserv reference (Browne/van
  Wamelen). Fixed to ≥11 + regressions.** ~110k-pos winner differential, 0 mismatches.
**Wave-6 lessons:** (1) /tmp scratchpads are NOT durable across host restarts — treat re-fetch
as the norm, keep the URL patterns logged here; (2) a reference implementation fetched by the
BUILD agent into the scratchpad (entrapment Java) hands the QA agent its oracle for free —
extend the accasta pre-fetch practice to reference CODE; (3) printed "minimum stones to win"
claims are checkable and can be errata (Jed's Cross-19) — corner/edge double-counting is the
thing to re-derive; (4) games whose rules pages list actions the reference implementation
lacks (entrapment voluntary flip) → implement the PLAY section, document the discrepancy.
**▶▶ NEXT (wave 7) — from the wave-5 scout's remaining slate (sources need re-fetching per
the note above):**
1. **Ley Lines** (i17, Solomon, pp.44-46 full rules) — complete but QA-expensive: no external
   impl, random zone-quota setup (has_randomness), agreement ending needs design care.
2. **Winkel-Advokat** (i23) — WEAKEST: needs the German Schmidt original; French translation
   at regle.escaleajeux.fr/winke_rg.pdf; jump-geometry/turn-structure ambiguities + board
   value layout only on the cover photo. Consider deferring again if ambiguities don't resolve.
3. **Old tier-2 pool** (i2–i16, unscreened): Lightning, Strat, MEM, Phalanx, Gle'x, Orbit,
   Domain, Vai lung thlân, Pagoda, Layli Goobalay, Ot-tjin, Hi-Jack, Sleeping Beauty Draughts,
   Super Halma, Mamba, Selus/Sadéqa, Chebache[Wayback]. Screen with a scout agent first
   (wave-5 lesson: AG index `*`/`†` markers are reliable).

### (prior handoff) ✅ AG-MAGAZINE WAVE 5 COMPLETE (2026-07-19b) → **354 games**, #351–354
Screened all 10 staged wave-5 candidates via a scout agent BEFORE assigning (wave-3 lesson; the
AG game index's `*`=complete-rules / `†`=partial markers are reliable screening signal). Picked
the 4 best-anchored; all deep-QA MERGE **0 fixes across the entire wave**, browser-verified,
one commit each:
- **fenix #351** (`a27425b`) — Horn 2019 HUCH! chess-checkers hybrid (AG#20 designer original
  rules + HUCH rulebook PDF): 9×9 corner triangles, 5 stack-building setup turns (3 Generals +
  King), compulsory max-total-VALUE chain jumps (K3/G2/S1), one-shot General rebuild + mandatory
  King rebuild overriding captures. Option: original (Strike) vs published HUCH — QA confirmed
  EXACTLY two variant differences (setup adjacency, repetition rule). Figure 3 worked max-capture
  example pinned exactly; 3000-position independent-generator differential, 0 mismatches.
- **mattock #352** (`d3c08ef`) — Edwards 2020 hexhex-7/5 mining-collapse territory (AG#21 +
  Mindsports Dagaz JS as semantics reference): mandatory mine w/ collapse rule + optional move +
  automatic simultaneous removal; cannot-mine = loss, structurally always a winner. Magazine
  setup diagram is PRIMARY (Mindsports' own hex-7 setup differs from the magazine — magazine
  wins). p.14 starred legal-mine figure (11 cells exact) + p.20 puzzle/p.25 solution anchored;
  ~13k full move-set differential comparisons over 290 games, 0 mismatches.
- **shape_chess #353** (`52feba0`) — Richu 2022 Xingqi mirror-symmetry scorer (AG#24 Ploog):
  drop/jump/push on 12×12+ points, own 8-connected mirror-symmetric shapes ≥6 score n−5 +
  bonus turn, first to 4. Rotation ≠ symmetry; axes = grid/half-grid orthogonals +
  integer-offset diagonals (half-integer diagonal mirrors provably off-lattice). All 6 article
  puzzles + printed solutions asserted (coordinate frame proven unique); QA ran an EXHAUSTIVE
  all-3832-fixed-6-polyplet symmetry sweep vs an any-angle exact-rational detector, 0
  mismatches (new best-practice: exhaustive small-case enumeration beats sampling).
- **mirador #354** (`f1a936a`) — Perkis 2010 LOS-connection w/ declare/challenge adjudication
  (AG#22): 2×2 miradors, width-1 LOS corridors, declare → unlimited challenger placements →
  broken = challenger wins outright. 18-move fritzd–pim annotated game replayed (printed
  "16. O16" PROVEN a magazine typo for C16 — 5th AG-errata find; annotator = PAUL van Wamelen);
  four-move-win position proven unassailable COMPLETELY (DFS over all 450,799 legal counter-
  placement sets); 15,910-position differential vs an independent AbstractPlay-port oracle, 0
  mismatches. UX note (rule-faithful, shipped as-is): declare window opens after nearly every
  placement early (any lone mirador has LOS to two sides); premature declares must stay legal.
**Wave-5 lessons:** (1) the AG index's `*`/`†` complete/partial-rules markers are reliable and
make screening cheap — check the index FIRST; (2) a dedicated screening scout agent (one agent,
all candidates, ranked recommendation) is token-efficient vs orchestrator-reading every article;
(3) reference implementations keep having their own bugs/deviations (Mindsports hex-7 setup ≠
magazine; AbstractPlay declare model differs) — magazine/designer sources stay primary, engines
are semantics oracles; (4) exhaustive small-case enumeration (all size-6 polyplets vs OEIS
count) is a stronger verifier than any sample; (5) scout metadata still needs build-agent
verification (the "44-move" annotated game was 18 moves; "Marcel" was Paul; SanQi is 2-player
not 3).
**▶▶ NEXT (wave 6) — screened + ranked by the wave-5 scout (full per-game detail in that
report; all sources verified fetchable):**
1. **3D XYZ Chess** (i24 full article + i19 cover; Rick Hewson) — COMPLETE (index 24*): 4×4×4,
   32 standard pieces, K=orthogonal-only, B=12 planar diagonals (no triagonal), N=triagonal
   single-step, Legan-style level-locked pawns that capture as they move (i19 blurb is the
   load-bearing clarification); ANCHOR = full annotated 22-move Hewson–Mandoshkin game ending
   in mate + 10 diagrams. Layered-grid render precedent = qubic/raumschach. issue_24.txt lines
   ~1889-2314, pdf pages 32-34; setup + movement diagrams need pixel-reads.
2. **SanQi** (i17; L. Lynn Smith 2003) — COMPLETE (index 17*): TWO-player (scout corrected the
   3-player brief — "game of three" = 3 shared piece TYPES), hexhex-4+ (10 optimal), placement/
   majority-replacement, one-turn immunity, circle-6 (P1) / line-6 (P2) / triangle-6 (either)
   goals. SDG rules PDF fetchable (superdupergames.org/rules/sanqi.pdf). Termination needs
   design care (replacement churn on a full board → no-progress cap + honest draw).
   issue_17.txt lines ~894-1200.
3. **Entrapment** (i22; Gowell 1999) — COMPLETE-WITH-EXTERNAL: magazine editorial is partial
   (no index `*`) but boardspace.net/entrapment/english/rules.html (fetchable, complete:
   25 barriers/side, roamer 1-2 orthogonal steps, jump-flip barriers, entrapment timing,
   mandatory-escape) + Boardspace Java source as differential oracle + archived games (some by
   Gowell). 7×7 default, 6×7 designer-recommended option. board.walls primitive (Quoridor).
4. **Jed** (i22; Thompson/Handscomb) — COMPLETE (index 22*): Jade (9×11 hex-parallelogram
   shared-stones Cross-vs-Parallel Hex, full rules + drawless proof in-article) + hox protocol
   J→E→D cycling pre-coloured spaces + modified pie. The J/E/D 3-colouring board figure is
   LOAD-BEARING (pixel-read; pdf p.27); weakest anchors of the slate (win-condition examples,
   chilling positions, Parallel-min-18/Cross-min-19 facts). issue_22.txt ~1704-1840 + 2384-2438.
Then: **Ley Lines** (i17, complete but QA-expensive: no external impl, random zone-quota setup
has_randomness, agreement ending) and **Winkel-Advokat** (i23, WEAKEST — needs the German
Schmidt original; French translation regle.escaleajeux.fr/winke_rg.pdf fetched to scratchpad;
jump-geometry/turn-structure ambiguities + board value layout only on the cover photo). Plus the
old tier-2 pool (i2–i16: Lightning, Strat, MEM, Phalanx, Gle'x, Orbit, Domain, Vai lung thlân,
Pagoda, Layli Goobalay, Ot-tjin, Hi-Jack, Sleeping Beauty Draughts, Super Halma, Mamba,
Selus/Sadéqa, Chebache[Wayback]). Magazine PDFs 17–24 + all wave-5/6 source fetches live in
scratchpad `agmag/` (re-extractable: abstractgames.org/uploads/1/1/6/4/116462923/
abstract_games_issue_<N>.pdf, browser UA; scratchpad survives across sessions under
/tmp/claude-1000/-home-erik-abstract-games/<session>/scratchpad — check old session dirs
before re-downloading).

### (prior handoff) ✅ AG-MAGAZINE WAVE 4 COMPLETE (2026-07-19) → **350 games**, #347–350
Erik kicked off "issues 17–24" — scouted + deduped all 8 new-series issues (PDFs re-downloaded to
this session's scratchpad `agmag/`; same URL pattern, browser UA). Most headliners already existed
(keil, tumbleweed, redstone, meridians, murus_gallicus, symple, blooms, agon, toguz_kumalak,
urbino, glinski_chess, stigmergy, hostage_chess, dameo…). Picked 4, all article-verified BEFORE
assigning (wave-3 lesson), all deep-QA'd + browser-verified + committed, one commit each:
- **chigorin_chess #347** (`6b44c86`) — Betza 2002 (AG#24 Vehre): White 4 Knights + Chancellor vs
  Black 4 Bishops + Queen; own-army promotion. FAST-PATH: three sources agree (CVP = FSF built-in
  `chigorin` = AG#24); perft vs pyffish exact (26/416/11408/229973 + promo/castling positions),
  60-game differential 0 mismatches (orchestrator re-ran it independently). Committed on the
  anchor + render probe (standard square board).
- **avalam #348** (`ca714ea`) — Deweys 1996 (AG#18 cover essay = complete rules): 49-cell shaved
  9×9, move any whole stack 1 step onto occupied, cap 5, most tops, tie = honest DRAW. Geometry
  triple-sourced (essay + publisher rulebook photo pixel-count + UCLouvain reference matrix). QA
  MERGE 0-fixes: 400-game lockstep differential vs the actual UCLouvain avalam.py, 0 mismatches;
  **the UCL 5-tower tiebreak is a COURSE convention, not official — 50/400 random games end tied,
  honest-draw is load-bearing** (another entry in the honest-draw ledger).
- **boom_zoom #349** (`34e0071`) — Bomba 2018 Hollandspiele (AG#21 Ploog article = full 2nd-ed
  rules): whole-stack zoom/boom/bear-off, 10-square virtual goal rows incl. corner diagonals, no
  splitting (brief said splits — sources overrode). QA MERGE 0-fixes: from-scratch oracle, 64,599
  positions, 0 mismatches; **the magazine's two endgame-problem captions are SWAPPED** (both agents
  proved it independently via pixel grids + counter accounting; solutions replay exactly under the
  correct pairing — third "errata in the magazine itself" find after Smess/AG#9 and Croda/AG#10).
- **accasta #350** (`bc1579e`) — Stein 1998 (spielstein.com official rules + Stein's own
  never-published-AG17 article PDF, both saved in scratchpad `agmag/accasta_*`): hexhex-4 castles,
  S/H/C up-to-1/2/3, compound split-K turns (realm/blooms sub-move pattern + End-turn), safe-stack
  ≤3 of EACH colour, win = 3 stacks in enemy castle at turn START (2010 update: + no-move win;
  article-only "no release at home" correctly omitted — later-official-supersedes precedent).
  Pari variant option (rule-over-example on the official page's self-contradictory notation). Gold
  anchor: full Stein–Williams 2004 sample-game replay. QA MERGE 0-fixes: independent re-impl,
  61,110 positions / 320 games, 0 mismatches.
**Wave-4 lessons:** (1) pre-fetching the designer's official rules INTO the scratchpad before
launching the build (accasta) removes a whole failure mode; (2) an orchestrator gate run can catch
a selftest mid-write — re-run before diagnosing (accasta "failure" was a half-written file);
(3) magazine-printed problems keep paying as anchors AND keep containing errata (boom_zoom caption
swap); (4) reference academic/course implementations are superb differential oracles but their
CONVENTIONS aren't rules (UCLouvain tiebreak).
**Dedup map i17–24 (everything else in those issues):** i17 zhadu(cover-brief only, no full
rules)/agon/toguz_kumalak(culture article—screen for full rules if wanted)/quadlevel-3d-chess
(archive)/katarenga(Parlett)/universe(Randolph)/SanQi(competition, full rules, 3-player)/ley-lines
(Solomon, full rules pp.44-46); i18 avalam SHIPPED/keil/neue-dame(Gering)/traversi+sudden-death-
grasshopper(Perkis)/marrakesh+wysiwyg(solitaire/cards—skip); i19 3d-xyz-chess(cover + FULL i24
article)/super-chess(retrospective)/qua(3-player 3D connection—hard render)/labyrinth(Horn)/boxoff
(solitaire—skip); i20 nxs(review only + i24 endgame articles—no full rules?)/schada(Horn)/fenix
(Horn, full rules likely)/pagode(cover + i13/i15/i21-precursors—the old tier-2 Pagoda);
i21 accasta+boom_zoom SHIPPED/mattock(Edwards, full article)/jersi(Borboleta, complex)/alfreds-
wyke(Dekker)/rectangle-hex(i23 Back—possible hex option); i22 entrapment(cover, near-complete
rules + Boardspace; 6x7 designer-recommended option)/jed(Thompson, full rules)/mirador(Perkis/van
Wamelen)/chessboard-jetan(jetan option?)/kolcun-dice(screen); i23 winkel-advokat(cover, fairly
complete)/cabale(cover, successor—endgame "broken" per editor)/meridians/domino-runners(draw
randomness—screen); i24 chigorin SHIPPED/shape-chess(Ploog, full rules)/stymie(review)/evl
(screen)/superschaak-fairy(screen)/nibelungenlied(simultaneous—defer w/ Mentalis)/pencil-paper-
part-1(2 games—screen).
**▶▶ NEXT (wave 5) — best-sourced candidates, screen article completeness first as always:**
Entrapment (i22), Ley Lines (i17), 3D XYZ Chess (i19+i24 full article; 4×4×4 — qubic/raumschach
layered-grid render precedent), Winkel-Advokat (i23), Shape Chess (i24), Jed (i22), Mirador
(i22), Mattock (i21), SanQi (i17, 3-player), Fenix (i20). Plus the remaining OLD tier-2 pool
(i2–i16: Lightning, Strat, MEM, Phalanx, Gle'x, Orbit, Domain, Vai lung thlân, Pagoda(+i21
precursors article), Layli Goobalay, Ot-tjin, Hi-Jack, Sleeping Beauty Draughts, Super Halma,
Mamba, Selus/Sadéqa, Chebache(Wayback needed)). Magazine PDFs 17–24 + accasta sources in this
session's scratchpad (re-extractable: abstractgames.org/uploads/1/1/6/4/116462923/
abstract_games_issue_<N>.pdf, browser UA).

### (prior handoff) ✅ AG-MAGAZINE TIER-2 WAVE 3 COMPLETE (2026-07-18c) → **346 games**, #344–346 + a smess bug fix
Picked 4 from the tier-2 list; TWO fell to the screen (the wave's big lesson: **"tier-2 = rules
printed" claims need per-article verification** — read the article BEFORE assigning a build):
- **Take the Brain (i9) = DUPLICATE**: it IS Smess #330 under its UK title (alt-title dedup — grep
  by title missed it; the build agent caught it). The pivot paid off double: QA of the existing
  package vs AG#9 Diagram 1 (600/1200dpi) + chessvariants smess73.png found a **REAL arrow-table
  bug** (b2={N,E}, f7={W,S} — misread as diagonals; the two errors were 180°-symmetric partners =
  invisible to the symmetry selftest). Fixed (`a8968a1`) + pinned: full 89-ply AG#9 sample-game
  replay + a 3,080-state Brain-vs-Brain retrograde solve asserting the EXACT 48-class win list —
  which exposed errata in AG#9's own printed page-29 solution (misses b1b2/b1d2, wrongly includes
  f4e3; count-only would have been fooled, the old wrong table also yields ~47/48). Tags += "take
  the brain"/"all the king's men". Two independent agents agreed square-by-square.
- **Pentagonia (i2) = clone-skip** (Nine Men's Morris on nested pentagons). **Chebache (i3) =
  review-only, NOT full rules** (would need Wayback chebache.com — left on the list, flagged).
- **hijara #344** (`fa5ec46`) — Samuel 1995 fill-in-order alignment scoring (AG#5 review = complete
  rules); ≡ 4×4×4 gravity Qubic w/ scoring, selftest PROVES the 76-line mapping; designer's corner
  line = manifest option `corners` off-by-default (BGG designer text says "optional"); QA MERGE
  (doc-fix only), 500-game differential clean at every ply; 15-pt sequence counts both directions
  (forced by the Qubic equivalence).
- **realm #345** (`cd779d8`) — Orbanes/Sackson 1973 realm-control wargame; AG#9 Mikulas article IS
  the designer-maintained ruleset (he owns the rights). Compound Dispersal/Concentration/
  Rearrangement turns via sub-moves + End-turn (Blooms pattern) + follow-up pickers (created-
  enforcer cell+facing, immobilization choice). Full sample-game replay anchor (every annotated
  Special Event fires exactly; Figures 3–7 pixel-matched; the worked example ≠ the sample game —
  two different games). QA MERGE-WITH-FIXES: **real bug — pass didn't reset the rearrangement
  3-in-a-row streak**; 88k-state independent differential clean; AbstractPlay corroboration (AP
  itself has a capture-arithmetic bug we don't share). ~60% of RANDOM games hit the 1000-sub-move
  cap = genuinely dead both-blocked positions (random players never double-pass); cap scores
  identically to the agreement end, un-gameable.
- **octagons #346** (`c5afe23`) — Schmittberger 1992 half-octagon connection (AG#7); 177 spaces
  (128 halves checkerboard-cut + 49 tilted squares), turn = 1 half-octagon OR 2 squares; swap =
  PROVEN 90°-rotation automorphism (recolour alone would be wrong — third entry in the
  value-preserving-swap family after rhode/anchor); QA MERGE 0-fixes — its independent
  combinatorial graph (the article's Onyx-dual points model) came out graph-IDENTICAL; 7k+
  colouring oracles = exactly one winner always. Platform-class flag: ~2480-move branching makes
  the 3s bot weak (Blokus class; AGP_BOT_MAX_TIME helps).
**Wave-3 lessons:** (1) verify article completeness BEFORE assigning (2 of 4 picks fell to the
screen); (2) dedup must include ALTERNATE TITLES, not uid/name grep (Take the Brain=Smess);
(3) a "duplicate" pick can still pay: QA the existing package against the new source (found a
real bug + errata in the magazine's own puzzle solution); (4) exact-list solver anchors beat
count-only (the wrong board reproduced the right count).
**▶▶ NEXT (wave 4) — remaining tier-2 candidates (NOT yet article-verified — screen each first!):**
Lightning (i5 — 1890s Selchow tile-draw race, has_randomness, tile shapes need Fig-1 pixel-read),
Chebache (i3 — review only; needs Wayback chebache.com rules recovery), Strat (i4 15×30 Halma),
MEM (i2 — "blocking" announce needs design decision), Phalanx (i11), Gle'x (i11), Orbit (i12),
Domain (i12), Vai lung thlân (i12), Pagoda (i13), Layli Goobalay (i13), Ot-tjin (i14), Hi-Jack
(i14), Sleeping Beauty Draughts (i14 Gering), Super Halma (i15 variant), Mamba (i16),
Selus/Sadéqa (i16). Larry Back Square/Head-Start Hex = possible hex options. Liubo defer
(contested reconstruction). **Issues 17–24 still unscouted — scout them next if the verified
tier-2 pool thins** (likely, given the wave-3 attrition rate). Magazine PDFs issues 2/3/5/7/9 +
article slices in this session's scratchpad (re-extractable:
abstractgames.org/uploads/1/1/6/4/116462923/abstract_games_issue_<N>.pdf, browser UA).

### (prior handoff) ✅ AG-MAGAZINE TIER-2 WAVE 2 COMPLETE (2026-07-18b) → **343 games**, #340–343
Picked 4 from the pre-staged tier-2 list (rules printed in the magazine); all deep-QA'd +
browser-verified + committed + pushed, one commit each:
- **croda #340** (`31c4a26`) — Dedić 1995 orthogonal checkers (AG#9, Freeling's own article +
  mindsports 508-croda); QA MERGE 0-fixes, 11,850-pos independent differential; BOTH magazine
  problems anchored (QA found the official AG#10 p.12 solution to the AG#9 prize problem — added
  to selftest). Designer corrected from brief (Dedić, not Freeling; BGG 19843).
- **chase #341** (`dd11536`) — Kruszewski 1985 TSR dice-army 9×9 hex CYLINDER (AG#9 full rules);
  ricochet/wrap/bump-chains/Chamber-splits/exchange + dist-phase for the owner-choice speed
  redistribution; QA MERGE-WITH-FIXES (selftest diagram cell G3→G2; nestorgames CHASE_EN.pdf
  2018, co-credited Kruszewski, settles bump-into-Chamber=illegal). 936 geometry checks +
  38,598-ply full-reimplementation differential, 0 mismatches. Move encoding origin>step>dest.
- **anchor #342** (`1e2ebd0`) — Meyers 2000 hexhex-8 territorial anchors (AG#5); home/away-corner
  anchor rule, simultaneous dead-stone scoring; QA MERGE 0-fixes, 6,000-board/105,953-group
  differential; **pie swap must recolour + CENTRALLY REFLECT** (home corners break plain-recolour
  symmetry — proven automorphism). Documented: Fig 3's printed count overlooks a 3rd dead white
  singleton (margin unchanged). BGG 23235.
- **akron #343** (`018ffad`) — Browne 2002 3D marble stacking connection (AG#14 + Browne's
  official v3.7 RTF + gamerz PBM via Wayback + igGC); over/under = edge-over-edge crossing
  ownership (cut-of-cut RESTORES) + overhead column cuts; DELAYED win (v3.7 default supersedes
  AG14's immediate); Pylos-style dynamic layered render. QA MERGE-WITH-FIXES (selftest-only):
  2.85M+178k move-set comparisons 0 mismatches, Fig-6 level-2 white ball pixel-confirmed.
  Ludii/Ai Ai do NOT have Akron. BGG 10889.
**Wave-2 lessons:** (1) AG problem/solution pairs (often solved in the NEXT issue — check issue
N+1) are gold anchors; (2) designer's later official rules supersede the magazine article
(Akron v3.7 delayed win — same precedent as Rhode/Emulsion); (3) pie swap on colour-asymmetric
boards needs the value-preserving automorphism, not recolour-in-place (anchor's central
reflection joins rhode's transpose).
**▶▶ NEXT (wave 3) — remaining tier-2 candidates (deduped, rules printed):** Take the Brain
(i9 Klamer classic), Realm (i9 Mikulas — article says "complete rules", Orbanes/Sackson Gamut
of Games), Lightning (i5 — 1890s Selchow tile-draw race, has_randomness, tile shapes need
Fig-1 pixel-read), Hijara (i5), Chebache (i3 Pardee dice race), Octagons (i7), Pentagonia (i2),
Strat (i4 15×30 Halma), MEM (i2 — "blocking" announce needs design decision), Phalanx (i11),
Gle'x (i11), Orbit (i12), Domain (i12), Vai lung thlân (i12), Pagoda (i13), Layli Goobalay
(i13), Ot-tjin (i14), Hi-Jack (i14), Sleeping Beauty Draughts (i14 Gering), Super Halma (i15
variant), Mamba (i16), Selus/Sadéqa (i16). Larry Back Square/Head-Start Hex = possible hex
options. Liubo defer (contested reconstruction). Issues 17–24 still unscouted (scout next if
tier-2 thins). Magazine PDFs + per-issue .txt in the session scratchpad (re-extractable:
abstractgames.org/uploads/1/1/6/4/116462923/abstract_games_issue_<N>.pdf, browser UA).

### (prior handoff) ✅ AG-MAGAZINE WAVE 1 COMPLETE (2026-07-18, Erik pick: "start with issue 1…") → **339 games**, #336–339
Source = Abstract Games magazine PDFs: `https://www.abstractgames.org/uploads/1/1/6/4/116462923/abstract_games_issue_<N>.pdf`
(curl w/ browser UA; pdftotext works; diagrams via `pdftoppm -png -r 300`). Issues 1–16 scouted+deduped.
**SHIPPED (all deep-QA'd + browser-verified, one commit each):**
- **jetan #336** (`2ad565b`) — ERB 1922 Martian chess, AG#6 "suggested standard" (Handscomb+Smith);
  E@ escape via reserve chip; chief_rule option; QA MERGE 0-fixes (~700-position differential, mirror exact).
- **salta #337** (`f115798`) — Büttgenbach 1899, AG#8 Gering; full 214-ply Krone–Grotewold 1901 replay,
  A* re-derives the published "27 points"; QA MERGE doc-fix only (9,600-pos differential).
- **hexdame #338** (`d92597c`) — Freeling 1979, mindsports; QA MERGE-WITH-FIXES — **REAL BUG: king
  capture crossing its vacated origin mis-recorded the victim** (fixed+pinned); 15k-pos differential clean.
- **onyx #339** (`b0312d0`) — Larry Back 1995, AG#4 = designer's own rules; 204-pt snub-square+midpoints
  polygons board; QA MERGE 0-fixes (graph re-derived from diagram PIXELS; 60,501-pos differential).
**Dedup map i1–16 (all others already existed):** i1 bashni/camelot/gipf/trax/lines_of_action/kyoto_shogi;
i2 octi/twixt/congkak(=Congklak cover — clone-skip, 2×5 board = possible size option); i3 cathedral/
phutball/epaminondas/grand_chess; i4 hostage/bao; i5 renju; i6 zertz/gonnect; i7 breakthrough/
ludus_latrunculorum; i8 alice_chess/congo; i9 (none built yet — see tier 2); i10 raumschach/mahjong(4p—skip);
i11 entropy/janggi/lasca/omweso; i12 unlur; i13 surakarta/emergo; i15 snort; i16 arimaa/amazons/tablut.
**▶▶ NEXT WAVE PRE-STAGED — TIER 2 (rules printed in the magazine; pick ~4):** Chase (i9 FULL article —
TSR 1986 cult classic, hex board, dice-value pieces, deterministic), Croda (i9, Freeling draughts variant,
mindsports), MEM (i2, Hopfenberg pattern-matching — random full-board setup fine; "blocking" announce
mechanic needs a design decision), Chebache (i3, Pardee dice race), Strat (i4, 15×30 Halma variant),
Hijara (i5), Lightning (i5, 1890s pre-Hex connection game), Anchor (i5, Meyers hex-Go), Octagons (i7),
Pentagonia (i2, nested-pentagon 15-man morris), Realm (i9 Mikulas), Take the Brain (i9), Phalanx (i11),
Gle'x (i11), Orbit (i12), Domain (i12), Vai lung thlân (i12, Mizo traditional), Pagoda (i13),
Layli Goobalay (i13, Somali), Akron (i14 Browne), Ot-tjin (i14), Hi-Jack (i14), Sleeping Beauty
Draughts (i14 Gering), Super Halma (i15 variant), Mamba (i16), Selus/Sadéqa (i16 African warrior games).
Also: Larry Back's Square Hex/Head Start Hex (i5 — possible options on hex). Liubo (i15) = contested
reconstruction, likely defer. **STRUCTURALLY DEFERRED (hidden info):** Mentalis (i1), Plateau (i3),
Bosworth (i2). Issues 17–24 not yet scouted. Scratchpad artifacts: ag_issue_{1..16}.txt + article_*.txt
(re-extractable from the PDFs).

## (prior handoff below) — updated 2026-07-17b (Recognized-Chess-Variants wave COMPLETE)

### ✅ RECOGNIZED-CHESS-VARIANTS WAVE COMPLETE (2026-07-17, Erik pick) → **335 games**, #320–335 (16 new)
**Second half (#329–335, all deep-QA'd + browser-verified):** magnetic_chess #329 (`3236ee8`,
QA MERGE 0-fixes, perft(2)=437 independently re-derived; king-capture win, rook-sourced
castling field) · smess #330 (`e982b87`, QA MERGE 0-fixes — 56/56 arrow-map pixel re-read,
official Hasbro PDF vindicated opponent-square-only promotion; board.overlay chevrons; 7
Ninnies not 8; BGG 1289 corrected from brief) · cwda #331 (`5042c38`, QA MERGE 0-fixes —
4 Betza armies via white_army/black_army options, per-colour asymmetric Nutty Knights,
compulsory Bede queenside 3-square castle-flip, promotion = union of both armies, per-army
perft 20/28/24/26) · crazy_38s #332 (`802cd17` — **THE WAVE'S BIG CATCH: 3 QA rounds**;
knight on the Celtic-knot board is NOT a lattice leaper — geometry-derived KNIGHT_TABLE
(2 curved steps + 1 crossing, tip-intermediate rejected = distance-filtered geometric
knight), diagram anchors a8→{b5,c6,d7} / f3→{...h1} verbatim; QA also caught a never-true
perft freeze; final perft 16/256) · chaturaji #333 (same commit, QA MERGE 0-fixes —
4-seat dice chess, al-Biruni scoring, 4-vector returns, dice state machine browser-
verified) · dragonchess #334 (`a724a8a`, QA MERGE 0-fixes — Gygax 3-board, perft(1)=90
re-derived piece-by-piece, Basilisk freeze/Dragon remote/Paladin 3-D knight all probed,
attack scanner proven vs forward oracle) · flip_chess #335 (`d518a53`, QA MERGE 0-fixes —
7x6-minus-corners (brief wrongly assumed the knot board — sources fixed), flip pairs
P↔Berolina/B↔R/F↔N + flip-in-place (same-cell click, browser-verified), Flip Shogi as
mode option, ZRF dead-code proof for no-double-step/no-ep). **DEFERRED (structural):**
kriegspiel (hidden info — platform shows full state), bughouse (2-board team real-time),
star-trek tri-D (movable attack boards, contested rules), chessapeak (obscure commercial).
The Recognized list is now DRAINED: 27 pre-existing + 16 built + 4 deferred ≈ the full
~50-entry list (dupes/junk rows excluded). **NEXT WAVE = fresh theme (Erik pick).**
LESSONS: same-cell path + =CHOICE = established pocket/flip UI idiom (single choice
auto-plays, no picker); QA re-verify rounds PAY (crazy_38s knight; 2 extra bugs found in
round 2); briefs wrong on boards/BGG ids ~5× this wave — sources-override held.

### (first half of the wave, #320–328, for reference)
Source list = chessvariants.com "Recognized Chess Variants" (~50 distinct; 27 were already in
the library — dedup map in the session log). **Erik also asked for real piece IMAGES over bare
letters** → shipped orchestrator capability `491afce`: pieceImages.js 2→15 recolourable
cburnett-style icons (amazon/centaur/mann/ferz/wazir/alfil/dabbaba/champion/wizard/zebra/
giraffe/unicorn/dragon, Wikimedia CC), ChessLike movement-derived leaper icons + per-game
`ICONS` override (~15 existing variants gained images free; grand_acedrex pins G=giraffe),
SPEC.md "Piece-level icon" section; + `5b433f8` spec.actionNames (generic action-button
labels, mirrors choiceNames). SHIPPED: **chaturanga #320** (`fd43fc3`, crossed kings,
stalemated-player WINS, baring outright, perft+shatranj differential) · **glinski_chess #321**
(`8bc496f`, first hex chess; perft 51/2586/137858 created + @bedard/hexchess differential
19,708 pos 0-mismatch; stalemate ¾–¼ → payoffs [±0.5]; BGG 19432 corrected) ·
**avalanche_chess #322** (`160ec6a`, QA MERGE 0-fixes on independent python-chess oracle;
4-cell compound move + owner's standalone push-promotion =Q; self-check push = instant loss) ·
**mccooey_chess #323** (`6f20c2b`, 7 of McCooey's own games strict-replayed; centre pawn no
double-step; stalemate draw) · **hostage_chess #324** (`c693f3e`, QA MERGE 0 bugs; two-ply
exchange 'exchange:H-L' action + forced tray drop, actionNames labels; browser-verified full
cycle) · **rococo #325** (`0b216b6`, QA MERGE doc-fix only; ZRF-anchored; edge ring, 25-move
opening, uniqueness probe 5,689 pos clean) · **raumschach #326** (`7cb2a54`, 5×5×5 alice-style
5-board polygons; Q+K triagonal verdicts sourced; unicorn icon; perft 61/3608/236510) ·
**circular_chess #327** + **pocket_mutation_chess #328** (`ba21824`, annulus polygons w/
double_step option + QA-MERGE 18-piece mutation table). IN FLIGHT (opus agents): smess,
magnetic_chess, crazy_38s builds. REMAINING BUILDABLE: chess_different_armies (CwDA, big),
flip_chess, dragonchess (3×8×12), chaturanga_4 (4-player+dice). DEFERRED: kriegspiel (hidden
info), bughouse (2-board team), star-trek 3D (movable boards), chessapeak (obscure).
OPS: Fable session cap killed 5 agents mid-flight at ~4:45pm → ALL relaunched clean on
model:opus (no partials survived — killed builds had written nothing). Backend gotcha
confirmed again: registry tolerates partial packages (server catches per-package).
QA pattern this wave: ChessLike fast-path for perft-anchored simple variants; adversarial
deep-QA agent (independent source fetch incl. ZRFs/engines) for every custom-logic game —
verdicts so far 3× MERGE-0-fixes, 1× doc-only fix.

## (prior handoff below) — updated 2026-07-17 (wave tail shipped)

### ✅ TRADITIONAL/REGIONAL WAVE COMPLETE (2026-07-17) → **319 games**, #309–319 + kolowis option
**WAVE TAIL SHIPPED (batches 3+4, same day): 6 items → 319 games, all deep-QA'd +
browser-verified + committed.** kolowis option on awithlaknannai (`8d6e468` — size
[25,49]; Culin 49-pt serpent, 23 men/side, centre + BOTH middle-row end points empty
[3 empties, not 1 — the brief undercounted]; geometry parameterized, default game
trace-identical to HEAD over 10 seeded games) + **puluc #315** (`9f160bd`, QA MERGE
0-fixes — Verbeeck/Wikipedia mapping [4 corn dice, blanks=5, ONE throw/turn],
REVERSE-and-carry piles [brief's "continue forward" was wrong], free-run returns to
hand, track 9/14/21; Sapper/Ludii divergences documented; BGG 13745) + **tab #316**
(`8a99600`, QA MERGE 0-fixes — Lane 1836 pp.346-349 read VERBATIM as primary; banked
throw chains spent any order, tâb-only conversion foremost-first, shared middle loop +
once-only enemy-row detour w/ entry-requires-enemies + freeze/'eggeh exception, whole-
pile capture, unite/tâb-split =ALL/=ONE via existing choiceNames, row-reduction; QA
re-derived successor tables from Lane's letters for ALL 5 sizes both seats 0-mismatch;
BGG 119436) + **hobak_gonu #317** (`1b548c1`, QA MERGE 0-fixes — 11-pt/14-edge pumpkin
graph from Ludii .lud + nol2i figures; one-way home-row FUNNEL [nol2i's win diagram
REFUTES Ludii's own free-slide encoding]; invasion option closed(default)/trap; FULL
SOLVE both variants root=DRAW [2,278 / 15,972 states, max win 20/22] matching namu.wiki;
QA reproduced the solve EXACTLY + 18,250-state full-graph differential 0-mismatch) +
**dablot_prejjesne #318** (`bdcfbb3`, QA MERGE 0-fixes — Keyland-1921/Ludii 72-pt
triangulated 6×7 lattice [42 vertices+30 centres, 191 segments, 316 jump triples] ALL
independently re-derived 0-mismatch; equal-or-lower rank captures; captures option
optional(Keyland default)/compulsory(modern); two-lone-kings draw + trapped-loses +
forced single-combat; 96.8% optional-mode random draw rate PROVEN a random-agent
artifact [71% decisive compulsory, 2/3 MCTS]; BGG 13777) + **bao_la_kiswahili #319**
(`d2547a6`, flagship, QA MERGE-WITH-FIXES notation/doc-only — de Voogt master rules:
namua/mtaji, kichwa/kimbi capture re-entry, first-lap-decides + 16-seed rule, takasa
restrictions, nyumba tax/stop/safari, takasia w/ exceptions, never-ending-sowing CYCLE
DETECTOR; anchors = ~12 Game Cabinet diagrams pit-for-pit [2 published typos found] +
MW Puzzles 1-3 incl. de Voogt's 22-ply never-ending move — measured minimal period 228,
MW's "218" caption PROVEN impossible under every state projection; QA fixed
describe_move's classical notation against all 10 published notated moves + added
Puzzle-1/2 anchors; 640-game sweep, rules engine 0 fixes; kujifunza option; BGG 14186).
**Wave-tail lessons:** (1) browser check caught what QA can't — bao's =L/=R picker leaked
Board.jsx's default chess CHOICE_NAMES ("Rook") until render() supplied choiceNames;
option/=CHOICE games must ship choiceNames when letters collide with promo letters.
(2) The kill-by-port one-liner can silently fail mid-chain — verify "port free" before
trusting a restart, else the browser exercises STALE code. (3) A flagship's pre-written
numeric claims (bao's "period 218" prose) can contradict its own selftest — QA's
independent measurement, not the source's caption, is the authority. (4) 5 of 6 QA
verdicts were 0-fix MERGEs — the build-brief + sources-override + adversarial-QA
pipeline is mature. **CLONE-SKIP CORRECTION: "pat-gonu (=kono)" was a misID — BGG
411418 "Pat Gonu" IS Hobak Gonu (now shipped #317).** Remaining tail: only **gala**
(C+ hard — CVP Bodlaender bent moves + deflection lines; naming hazard: Ludii "Gala" is
a different Sulawesi game) stays deferred. **NEXT WAVE NEEDS A FRESH THEME (Erik pick).**

### ▸ Wave log: TRADITIONAL/REGIONAL WAVE batches 1–2 (2026-07-17) — Ming Mang + kin (Erik pick)
Three scouts complete (Ming Mang / Latrunculi+Gonu / broad regional sweep). **BATCH 1
SHIPPED → 311 games: ming_mang #309 (`e9ac8b7`, deep-QA MERGE 0-fixes, 5.83M-comparison
differential 0-mismatch) + ludus_latrunculorum #310 (`4beff3c`, MERGE-WITH-FIXES doc-only,
103k-ply differential 0-mismatch, leaflet figures transcribed twice independently) + shax
#311 (`0ff34c6`, MERGE-WITH-FIXES doc-only, 400-game geometric-oracle differential
0-mismatch; QA UPGRADED the no-jare interpolation to source-supported via Davies'
"Varieties of shax" passage). All three browser-verified (boards render, moves play).
Batch-1 lessons: Shax's PDF author is Rick DAVIES 1988, not Jama (build corrected the
brief); Locus Ludi leaflet ≠ Ludii encoding in 4 places (leaflet wins, divergences
documented in rules.md).** **BATCH 2 SHIPPED → 314 games: jul_gonu #312 (`126883a`,
QA MERGE-WITH-FIXES doc-qualifier-only — FULL SOLVE anchor: 3,412,738 states/21.0M edges,
ban-free ROOT = cycle-bound DRAW [the pre-solve draft claimed a 1st-player win — the
orchestrator caught the contradiction when the solver finished after the agent stopped;
honest scoping enforced: superko value path-dependent/open]; QA independently REPRODUCED
every solver count + 3.4M-state fixpoint audit 0 violations + 700-game differential
0-mismatch) + choko #313 (`b68cd01`, QA MERGE 0-fixes, 640-game differential
byte-identical; DISTINCT from yote via the drop-initiative rule [voluntary drop forces
opponent's next turn = drop], Parker∪Murray union documented, BGG 380039) + sahkku #314
(`4849e8d`, QA MERGE-WITH-FIXES — QA caught a REAL bug: the king may JUMP own soldiers
[Wikipedia Vuovdaguoika verbatim], build had blocked it; 300-game/69k-state differential
0-errors; Vuovdaguoika attribution triple-checked — Ludii encodes a DIFFERENT Friis-style
ruleset, not an oracle here; no-stacking correctly Vuovdaguoika). All browser-verified
(sahkku sleepers = daldos dot-glyph convention, activation renders a disc).
Batch-2 lessons: (1) a build agent's background solver can finish AFTER the agent stops —
check disk + solve.log, SendMessage-resume the agent to reconcile pre-written claims vs
actual results (rules.md had optimistic placeholders); (2) Wikipedia section placement
(which regional ruleset a sentence sits in) is load-bearing — QA verified rule-by-rule
against raw wikitext.** WAVE TAIL OPTIONS (Erik or next session): puluc + tab (both
running-fights, would reuse daldos/sahkku dice patterns + piece.stack), dablot_prejjesne
(board lattice needs pinning), hobak_gonu (nearly-free full solve), kolowis option on
awithlaknannai (cheap), bao_la_kiswahili (flagship solo slot w/ BGA differential), gala
(C+ hard render). Or call the wave complete at 6 games.

**Batch-1 condensed briefs (full detail in scout reports; sources override):**
- **ming_mang** (confidence B — consensus reconstruction; Shotwell shows only 2 period
  sources, interpretations documented): n×n square, setup = full near file + interior of
  adjacent rank per seat (2n−2 stones on board + 2n−2 reserve; 8×8→14, 9×9→16, 17×17→32);
  rook moves; ACTIVE custodial capture, all 4 directions at once, runs of ≥1; captured
  stones **CONVERTED to capturer's colour** (board population constant — the game's
  identity); moving into a sandwich safe; corner immunity EMERGENT (not a rule);
  positional-superko move ban (Wikipedia); cannot-move loses (covers annihilation-by-
  conversion + blockade); no-progress N-ply + hard cap → honest DRAW (jpn fortress flaw is
  real — do NOT invent a material tiebreak). Options: size [8,9,17] (9="Gundru"),
  last_stone_leap [off,on] (Lha-mo 1926, Ludii Gundru HopCapture; removal not conversion,
  non-compulsory). Do NOT implement corner-turning capture (contested; document). BGG
  40573. Ludii = "Gundru" DLP.Games.358 (their "Mig Mang" is our tibetan_go!). Anchors:
  frozen rule positions (Wikipedia 3 multi-capture cases, conversion invariant, corner
  immunity, superko probe, reached cannot-move loss), opening mobility counts, 180°-sym
  probe. Distinct from mak_yek (no intervention capture, conversion, L setup)/seega/hasami.
- **ludus_latrunculorum** (confidence A): ship Schädler's reconstruction as the Locus Ludi
  "Seneca" playable form; option variant [seneca,piso]. 8×8, 20 pcs/side (16–24 agreed);
  placement phase (anywhere, no captures) then: 1-step orth + multi-leap over OWN-colour
  counters (leaflet; Piso = no leaps, immediate custodial); custodial trap → *incitus*
  (flipped, passive), NEXT turn mover MUST remove a still-guarded trapped piece before
  moving; corner trap; trapped attacker frees its victim; restricted no-suicide; no
  back-and-forth shuttle of one counter. End: reduced-to-1 or blockade; winner = most
  captures ⇒ honest DRAW on tie. NO dux (Kowalski/Bell dux = thin evidence — skip those
  rulesets). Authoritative: locusludi.ch/wp-content/uploads/2022/08/LUDUS-LATRUNCULORUM_rules_GB.pdf
  (+ Ludii `war/custodial/Ludus Latrunculorum.lud` 30+ rulesets; leaflet wins conflicts,
  e.g. leap-over-own-only vs Ludii's any-piece). Render: incitus = piece fill/stroke
  override (redstone/blooms precedent). BGG 21488 (merged Petteia entry). Anchors: leaflet
  worked figures as selftest positions; optional one-time Ludii-jar differential.
- **shax** (confidence A−): Somali morris, 24-point NO-diagonal morris board, 12 pcs each
  → board FULL after placement; NO removals during placement — after placement, FIRST
  player to have formed a mill removes one, then opponent removes one regardless; jare/
  oodan rule: blocked player ⇒ opponent MUST open an intersection, freeing move forming a
  mill removes NOTHING; NO flying; win = reduce to 2. Open point: no mill formed by anyone
  in placement (some accounts restart) — resolve from sources + document. Authoritative:
  Jama Musse Jama "An Introduction to Shax" PDF (mogadishuimages.wordpress.com) +
  Wikipedia. BGG 63875. Template: nine_mens_morris infra.

**Batch 2 queued (after batch 1 lands):** jul_gonu (A− — 4×4 Korean custodial, active-only,
flank 1-or-2 run, win = reduce-to-1 or stalemate, no-repetition rule; ~3M states ⇒ FULL
SOLVE anchor; BGG 96254; distinct from four_field_kono [same board, jump-capture]);
choko (B+ — 5×5 empty start, drop-or-move, jump capture + FREE second removal from
anywhere; Murray/Ludii over Wikipedia's phased version; morris two-stage removal encoding);
sahkku (B+ — Sámi 3×15, shared convertible neutral king "gonagas", 3 stick dice X/II/III/
blank, stacking + stack capture, mirrored tracks; ship Vuovdaguoika ruleset; Ludii
DLP.Games.646 + Borvo BGS 4 (2001); daldos pattern for dice-in-state; DRAW at cap, don't
copy daldos's ties→player-0). **Tail candidates:** puluc (B+ — Ludii/Bell track, prisoner-
carrying via piece.stack), tab (B — 4×N boustrophedon, conversion via tâb throw, banked
throws), dablot_prejjesne (B — rank-restricted jump capture, BGG 13777, board lattice needs
pinning), bao_la_kiswahili (B flagship — de Voogt codification, Ludii "Bao Ki Arabu" + BGA
live implementation as oracles; own solo slot), hobak_gonu (B small — Ludii .lud + trivial
full solve), gala German farmers' chess (C+ — CVP Bodlaender; NOT ChessLike, bent moves +
deflection lines; naming hazard: Ludii "Gala" is a DIFFERENT Sulawesi game), kolowis
size-option on awithlaknannai (cheap, Culin 1907: 49 pts, 23 pcs, centre empty).
**CLONE-SKIP/DEFER (recorded so they aren't re-scouted):** petteia (every reconstruction ⊂
latrunculi/hasami space), umul-gonu (=pong_hau_ki), gonjil-gonu (=12-morris), ~~pat-gonu
(=kono)~~ [WRONG — Pat Gonu BGG 411418 = Hobak Gonu, shipped #317], boseog-gonu + ja-jeon-geo-gonu (Ludii "uncertain history", thin), terhüchü +
sholo-guti (alquerque cluster), buga-shadara (bagh_chal family), zamma/kharbaga (draughts
mechanics, lattice-only novelty), patolli (gambling economy, below faithfulness bar),
main_chator (thin vs makruk/sittuyin). Note: cyningstan + mlwi.magix.net were DOWN during
scouting — don't rely on them; Wayback works.

### ✅ GO-VARIANTS WAVE COMPLETE (2026-07-16) → **308 games**, #304–308 + go option pack
Erik picked the theme ("Go variants — OGS forum / govariants.com / Wikipedia"). Scouted
by 3 parallel agents, built in 2 batches of 3, every package adversarially deep-QA'd
(MERGE ×5), all browser-verified, `go` options probe-verified. Commits `7aae4ec` (batch 1),
`44bb17d` (go options), `466688b` (redstone), `621d01a` (keil).
- **kropki #304** — Russian/Polish Dots (Точки), СКСТ/zagram "no-territory" rules (three
  sources CONVERGE: playdots.ru СКСТ + zagram + pointsgame/oppai-rs — no dialect risk).
  8-conn chain / 4-conn interior, empty-base ("домик") mover-precedence exception,
  liberation w/ score rollback, edge never encloses, ties = honest draw (СКСТ explicit).
  Sizes 13/20(default)/25/39×32, cross/empty start. **ORACLE: pointsgame/oppai-rs** (Rust;
  `~/.cargo/bin/cargo` — rustup installed this session, minimal profile). `_diff_oppai.py`
  env-gated, emits its own Rust harness (`--write-harness`): build 80 games/10,731 moves
  full-state 0-mismatch; QA fresh-seed 30 games incl. 39×32 + mid-game passes, 0-mismatch.
  AGPL = oracle only, no code copied.
- **sunjang_baduk #305** — historical Korean Go: 16-stone pinwheel setup + prescribed Black
  tengen (17 pre-placed), WHITE moves first, ordinary Go in play ("ko and seki as in Japan"),
  **Korean REMOVAL counting** (genuinely a third scoring family: classify regions TT-style →
  remove non-wall stones, no removal may leave a friendly group in atari, cutting points OK →
  count TERRITORY ONLY, prisoners ignored). Anchor: Bill Spight's SL 9×9 worked example —
  post-removal board reproduced EXACTLY, B29/W31=W+2 (Chinese gives W+1 on the same position —
  pinned as the not-area-scoring proof) + both ko variations. Komi option 0(default)/4.5.
  Play-inside-own-territory is FREE under this scoring ⇒ play-it-out sound, bots fine.
- **tibetan_go #306** — Fairbairn/GoGoD 2005 "New In Go" ruleset (the Shotwell conflicts
  DISSOLVE: proximity rule rejected by the primary source; Wikipedia's 40+10 pts = NIG's
  20+5 zi, unit conversion). 17×17, 12 "Bo" stones on the 3rd line, White first, Chinese
  scoring + bonuses (all four 1-1s in one area → +40 pts; +10 more if same player has tengen),
  **vacated-point ban**: after ANY capture the opponent may not play on the vacated points for
  one move (subsumes simple ko; kills instant snapbacks); positional superko kept as documented
  backstop. Anchor: 2005 Jiang Zhujiu–Yue Liang pro SGF embedded — 217-move full replay legal,
  14 ban-active plies. Disambiguated from the unrelated custodial "Ming Mang".
- **go option pack** (no count bump) — `handicap [0,2–9]` (fixed Japanese hoshi placement,
  SL diagrams cross-checked vs OGS GobanEngine.ts EXACT; White moves first; komi choices
  gain 0.5), `topology [normal,torus]` (all adjacency through the `_neighbors` choke point
  wraps; caption flags it), `mode [normal,killall]` — **my brief had kill-all INVERTED;
  build agent corrected per Sensei's/Dinerchtein**: White wins iff any White stone survives.
  Backward-compat: new state keys serialized only when non-default; old live-DB payloads
  deserialize to normal; default-game trace pinned by sha256 from pre-change HEAD.
- **redstone #307** — Mark Steere 2012 annihilation Go: own placements NEVER capture; red
  (shared, permanent) stones legal ONLY where they bound ≥1 group; ALL boundless groups
  removed simultaneously INCL. the mover's own (unlike Go); annihilate enemy = win,
  both-annihilated = MOVER wins (sheet text), no draws; pie rule = ply-2 swap. Sizes 7/9/13.
  Move encoding `"c,r=black|white|red"` (Yodd-style always-suffixed choice ⇒ one-click UX +
  picker only where both colours legal); red = ZÈRTZ piece fill/stroke override. Anchors:
  all 5 rulesheet figures coordinate-exact (build + QA independent re-transcription, 0
  discrepancies); QA from-scratch legality oracle 300 games/53.5k plies 0 diffs; no-move
  backstop PROVEN unreachable. NOTE: Steere PDF **does** have a text layer (unlike his older
  vector sheets). BGG 120533.
- **keil #308** — Luis Bolaños Mures 2019, Go on hexhex cells via the LINKING rule ("two
  adjacent points link iff a common neighbour matches one of them in type") — restores
  crosscuts/ko on 6-connectivity; liberties/territory over LINKS; restricted positional
  superko over ONE'S OWN end-of-turn positions (button state distinguishes); komi-pie as
  in-game moves (`komi=0..12` buttons → `black`/`white` side choice) + half-point button ⇒
  no ties once taken. Sizes hexhex 4–7 (default 5). **SOURCE ARBITRATION: SL = BGG = MindSports
  (designer-current) supersede the 2019 L19 thread, whose wording is a DIFFERENT predicate.**
  Anchors: QA differential vs independent implementation of the SL sentence (115,200 link
  checks, 0 mismatches); scoped-vs-full capture equivalence proven + fuzzed. BGG 295889.

**Wave lessons:** (1) Traditional/regional variants (Sunjang, Tibetan) pinned down cleanly
once the PRIMARY source chain was chased — the "contested reconstruction" fear pattern
(maka_dai_dai) did NOT recur; a played-out pro game SGF is a superb full-ruleset anchor.
(2) My briefs were wrong twice (kill-all winner inverted; kropki liberation overstated) —
the sources-override-brief standing order caught both. (3) A komi-pie protocol models
cleanly as discrete non-cell action moves (13 buttons render fine).

**GO SEAM NOW DRAINED at the quality bar.** Shipped go-family total: go(+handicap/torus/
killall), atari_go, nogo, gonnect, sygo, tanbo, rosette, lotus, irensei, renju, slither,
blooms, kropki, sunjang_baduk, tibetan_go, redstone, keil. Scouted + REJECTED/DEFERRED:
Phantom/One-Colour/Batoo/Lighthouse (hidden info — platform disqualified), Parallel/
Fractional (simultaneous), Rengo/Pair (team), Environmental (auction), Medusa (Freeling —
BUILDABLE w/ Dagaz oracle but compound place-and-move-all-groups turns + end-of-game
dead-stone adjudication = both platform pain points, designer files it under "miscellany";
LOW priority, brief exists in this session's scout report), Margo/Spargo (Cameron Browne,
nestorgames PDF confirmed — needs a NEW square-pyramidal 3D-stacking render primitive,
orchestrator-owned Board.jsx work), Tibetan bonus variants (Shotwell's rejected rules),
Keima Go / TriGo / Alak / Stoical Go (thin; Stoical would be a `ko_rule` option on go if
ever wanted), govariants.com experimentals (Drift/Freeze/Pyramid/Tetris/Thue-Morse/Rizoma —
no pedigree). **NEXT WAVE NEEDS A FRESH THEME (Erik pick).** Possible directions surfaced
in scouting: a "traditional/regional games" wave (Ming Mang custodial, more historical
regionals), or the deferred render-primitive investments (Margo/Spargo 3D stacking; solo
puzzle support for num_players=1, previously offered and declined).

### ✅ BLOKUS FAMILY COMPLETE (2026-07-15, `df96acc`) → **303 games**, #302–303
Erik: "continue with 4-player Blokus or others you pick". Shipped **blokus #302** (4p,
20×20) + **blokus_trigon #303**, both Pentobi-anchored, + 2 Board.jsx additions. Suite
green @303, browser-verified, pushed.

- **blokus** — corners are **colour-assigned CLOCKWISE**: seat0 (0,19) top-left, seat1
  (19,19), seat2 (19,0), seat3 (0,0) [our bottom-origin]. All 4 seats: **58** opening
  moves, split `{1:1,2:2,3:5,4:13,5:37}`. Differential: identical to Pentobi over **367
  positions / 6 complete games to terminal**, 6/6 final scores. R1983 never *states* the
  corner assignment (it follows from the blue→yellow→red→green seating) → documented as
  an interpretation.
- **blokus_trigon** — **sources corrected my brief TWICE**: BGG **21550** (21942 is Sid
  Sackson's *Camp* — the agent verified with control lookups), year **2006** not 2007.
  Hexagonal board of **486 triangles** (Pentobi `TrigonGeometry`: `init(sz*4-1, sz*2)`,
  sz=9 → 35×18, `dy=min(y,H-y-1); min_x=sz-dy-1; max_x=W-min_x-1`; row profile
  19,21..35,35..21,19). 22 free polyiamonds (1/1/1/3/4/12 by size). **6 start points are
  SHARED — any colour may open on any** (unlike classic's assigned corners): (9,6),
  (9,11), (17,3), (17,14), (25,6), (25,11). Anchor **2478 = 6×413**, split
  `{1:6,2:18,3:54,4:168,5:540,6:1692}`. Differential: identical over **405 positions / 6
  full games**, final_score 6/6 (Pentobi counts PLACED cells; `ours = pentobi − 110`).
  **KEY TECHNIQUE: a 60° rotation is NOT an integer map on (c,r) — do it on the VERTEX
  lattice, where D6 is integer matrices**, then read back. Engine uses **UP ⟺ (c+r) ODD**.

**Board.jsx additions (both generic + opt-in):**
- **`grid: "tri"` + `parity[]`** (parallel to `orients`; `p_i`=0 ⇒ orientation i's ANCHOR
  points UP) ⇒ polyiamond chips draw as triangles. **Purely RELATIVE to the anchor**, so
  the engine indexes its board however it likes and need only stay self-consistent — I
  first wrote a global "UP ⟺ c+r EVEN" rule into SPEC and it was WRONG for our
  coords; caught before it propagated. Verified live: the 1-triangle piece's 2
  orientations partition the 6 start points exactly 3 odd / 3 even.
- **`piece.shape: "fill"`** floods the whole CELL in the seat colour so a tile reads as
  ONE solid block, not a disc per cell. **Adopted by all 5 tiling games** — it makes the
  corner-touch rule (the entire point of Blokus) visible at a glance. Big readability win.

**REAL BUG FIXED (found by the blokus agent, in the game I'd shipped hours earlier):**
`blokus_duo.heuristic` returned a **bare float**, but `MCTSBot._rollout` hands the value
straight to back-prop which indexes `payoffs[p]` ⇒ `TypeError: 'float' object is not
subscriptable`. **`heuristic` MUST return one payoff PER SEAT, like `returns`** (
`ChessLike.heuristic` does). Invisible in Duo (~42 plies < default `max_rollout=50`, so
the cutoff never fires) but fatal at Blokus's 84 plies. **LOWERING max_rollout triggers
it, not raising.** Swept all 303 games: **102/103 heuristics were already well-formed** —
blokus_duo was the only one. Fixed to `[v,-v]` + mutation-pinned by a selftest that forces
the cutoff.

**Pentobi family surveyed (what's left):** `blokus two-player`/`three-player` +
`blokus trigon two-player`/`three-player` are official variants we DON'T ship (`num_players`
is a fixed property read before any state exists ⇒ can't be a manifest option; each would
need its own package — probably bloat). **callisto** (diamond of squares), **gembloq**
(quarter-square gems), **nexos** (pieces on grid EDGES) each need NEW geometry; **blokus
junior** is a kids' cut-down. ⇒ **The Blokus seam is DRAINED** unless we want one of those.

### ✅ TILING / POLYOMINO PHASE — SHIPPED (2026-07-15, `12633b9`) → **301 games**, #299–301
Erik asked to look at Zillions' "Tiling games" theme (66 submissions, theme=30).
**Scouting verdict: that theme is a DEAD END — but it pointed at a real gap.** All 66
enumerated (the `offset` param silently drops the theme filter; you must POST the form
with `zilligames_gam_criteria=props&1,30&offset&N&…`). Breakdown: **55 are SOLITAIRE
puzzles**, ~60 of 66 are by ONE author (Karl Scherer — already in this file's REJECTS
list from an earlier pass); of the 11 tagged 2-player, Crosscram = Domineering (have),
"Square The Rectangle Large Board" is mis-tagged, Sticks-3D needs a 3D board. Residue =
8 thin 2003-era singles (Dipole + Africa University by Ingo Althöfer are the best; both
need ZERO new primitives — see "leftovers" below).

**Two structural findings worth keeping:**
1. **Stick/rectangle games need NO new primitive** — a 1×n stick or a rectangle is
   determined by TWO cells, so `"first>last"` is the existing domineering/cram path
   model. Only free-form polyominoes needed a palette.
2. **55/66 need `num_players=1`, which the platform has NEVER had** (0 games use it).
   Lobby/bot/ratings/async all assume ≥2 seats. Erik was offered this and DECLINED in
   favour of the polyomino palette. Solo-puzzle support remains an open platform
   question, not a rejected one.

**Erik picked: build the polyomino palette** → unlocked the real tiling classics.

**NEW PRIMITIVE — `palette`** (SPEC.md has the full contract). Move `"KEY:o@c,r"`
(= drop syntax + orientation index; `DROP_RE` untouched ⇒ Crazyhouse/Gobblet/Shogi
byte-identical). UI derives orientations/anchors from `legal_moves` ALONE ⇒ **no server
change** (enforced path is still `move in legal_moves`), same as drops. Per-seat trays
below the board (2- and 4-seat alike), shape thumbnails, orientation strip, legal-anchor
highlight, hovered ghost footprint.
- **`palette.shared`** = ONE "Pool" tray in the mover's colour (Golomb). **Must be
  explicit**: Blokus Duo's two SEPARATE 21-piece hands are byte-identical at move 1, so
  auto-merging identical lists would silently wreck it.
- **ANCHOR CONTRACT (hard requirement): every orientation contains `[0,0]`** — anchor =
  bottom-most then left-most COVERED cell. **Do NOT normalise to the bbox corner** (a
  plus-pentomino's corner is empty ⇒ you click a cell the tile doesn't occupy; observed
  live: anchor (7,2) with the tile landing on 9,4–11,6). This bug came from the throwaway
  reference probe and propagated to 2 of 3 games — a build agent caught it. Pinned by a
  "REVERT anchor to bbox corner" mutation test. **Gotcha:** the covered anchor makes `dc`
  NEGATIVE, so placement loops must bound BOTH sides (`range(-lo_c, W-hi_c)`); the naive
  `range(W-max)` silently DROPS placements. Bit both blokus_duo and cathedral.

**Shipped:** blokus_duo #299 (Tavitian 2005, 14×14, BGG 16395) · golomb_pentominoes #300
(Golomb mid-1950s, 8×8, 12 free pentominoes SHARED pool) · cathedral #301 (Robert P.
Moore **1979** not 1978, BGG 7, 10×10). Full suite green @301; all browser-verified.

**ORACLES (reusable — this is the valuable residue):**
- **Pentobi** = the reference Blokus engine (Enzenberger, GPL) and a *general* Blokus-family
  oracle: `cmake -B build -DPENTOBI_BUILD_GTP=ON -DPENTOBI_BUILD_GUI=OFF` (**`pip install
  cmake` into .venv — cmake is NOT installed and apt needs sudo**; GTP target needs no Qt).
  CECP-ish GTP: `set_game blokus duo` (the FULL name — `duo` alone is rejected), `all_legal
  b`, `play b e10,e11,…`, `final_score`. Colours: duo=`b`/`w`; classic=`1`/`blue`. Ground
  truth captured: **Duo opening 414** `{1:1,2:4,3:18,4:76,5:315}`; **classic Blokus opening
  58** `{1:1,2:2,3:5,4:13,5:37}` (for a future 4p blokus). Differential lives at
  `games/blokus_duo/_diff_pentobi.py` (env `PENTOBI_GTP=…`; compares covered-CELL-SETS so
  it's anchor-agnostic). Result: identical on 272+ positions over full games; `final_score`
  25/25 **including the margin**; Pentobi's source confirms bonus 15/5 for the classic set.
- **Orman 1996** (`library.slmath.org/books/Book29/files/orman.pdf`) gives Golomb anchors
  **2308 / 296 / 1181 / 1197**, all independently re-derived. ⚠️ **1181 belongs to a LOSING
  opening**; 1197 is the N-class minimum (the drawn Fig-3 placement is 1216 — a figure-vs-text
  imprecision in the paper). "min 5 / max 12 game length" is **NOT in Orman** — folklore.
- **Cathedral has NO oracle.** Its anchor is arithmetic (`2×47+6=100` tiles the board
  exactly) + the rulesheet's SIX worked examples (page 3 figure, no text layer → `pdftoppm`
  and READ the figures). The only public Python impl (elliottower/cathedral-rl) is **BROKEN**
  on chirality (Abbey==AbbeyFlipped) — do not copy it.

**Rule traps banked:** Blokus and Cathedral have **OPPOSITE reflection rules** — Blokus
allows flips (21 = exactly the FREE polyomino count; one-sided would be 29), Cathedral is
**rotation-only**, which is *why* its Abbey/Academy are chiral. Cathedral rule 4's "corner to
corner contact is not acceptable" ⇒ **buildings bound 4-connected, space floods 8-connected**
(note 4) — *this*, not the chirality, is the real trap. Cathedral **rule 7 publishes an
explicit DRAW**; **Wikipedia drops that clause and is wrong**. Blokus rulebooks are silent on
ties ⇒ honest draw (Pentobi itself reports `"0"`; 5.7% of random games tie).

**LEFTOVERS / next candidates (deduped):**
- **blokus (4p, 20×20)** — the obvious next one: template off `blokus_duo` (we have >2-seat
  seating + 4 colours), corners are colour-assigned, anchor = **58** opening moves from
  Pentobi (`set_game blokus`, `all_legal 1`). Scoring identical (15/5). ~1 agent.
- **Blokus Trigon** (polyiamonds) — Pentobi supports it (`set_game blokus trigon`) but needs a
  triangular board primitive; scope before building.
- From the Zillions theme, if ever wanted: **Dipole** + **Africa University** (Althöfer 2003;
  both need ZERO new primitives — `board.tints` + 2-cell path + random setup, all shipped),
  then Area / Square Down / Sticks For Two / Sticks-Dia / Sticks Ortho (Scherer, thin).
  Match for Two would need the palette. **Quality bar caveat:** these are 2003 Zillions
  experiments, well below the Freeling/Duncan/Silverman/Muller bar we've been holding.
- **Cathedral open interpretations** (documented in its rules.md, worth revisiting if a
  source surfaces): whether "your first move" means the first *building*; whether your OWN
  buildings count toward "two or more"; mandatory-capture.

### ✅ SHOGI PHASE — wave 1 SHIPPED (2026-07-14) → **294 games**, #293–294 + 1 option
Erik picked the SHOGI PHASE (model note: orchestrator on Opus 4.8 1M; build/QA agents
Fable-or-Opus interchangeable — the real backbone is oracles/perft, not the model). The
"easy tier" turned out front-loaded harder than the queue implied (only goro_goro_plus was
trivial). All three shipped + independent adversarial deep-QA MERGE (0 fixes each) +
browser-verified + pushed (`c2f35aa`, auto-deploy fired). Full suite green.
- **Sho Shogi #293** (`4d638c4`) — 9×9 historical predecessor of modern shogi: standard army
  + a **Drunk Elephant** (7 king-steps minus straight-back) that promotes to a **Crown Prince**
  (royal), and **NO drops**. Dual royalty: "in check" iff EVERY royal is attacked → must capture
  BOTH. Bare-king win + mutual-bare draw (CVP/Steve-Evans reconstruction, orchestrator-confirmed
  vs source). Drunk Elephant/Crown Prince added via SHADOWED BASE_MOVE/PROMO_MOVE + rebuilt
  reverse-attack maps IN-SUBCLASS (shogilike.py untouched). deep-QA: perft d1=26/d2=676/d3=17368
  (2 independent gens agree), 601,801 attack-map checks 0 mismatch, 10k-pos legal-move diff 0
  mismatch, all royalty/bare-king scenarios correct.
- **Goro Goro Plus** (`656f0e3`) — delivered as a NON-breaking `variant [classic, plus]` OPTION on
  the existing goro_goro_shogi (not a new package — Erik's option convention). `plus` = seed a
  Lance + Knight into each starting hand (FSF/PyChess `gorogoroplus`); all L/N move/promote/drop
  logic already in ShogiLike. `classic` byte-identical. Does not bump the game count.
- **Shinjuu Shogi #294** (`c2f35aa`) — Silverman's own 11×11 four-Divine-Beasts drop shogi, 29
  pieces/side of 16 types (14 novel), drops, checkmate. Deliberately CHIRAL (Divine Beasts have
  no rotational partner → fairness from point-symmetric setup, not per-piece rotation). ShogiLike
  subclass; **attacked() computed FORWARD from _piece_targets** (not reverse maps) for the
  ranging/jumping/leap-over exotics. All 30 move-forms read square-by-square from Silverman's guide
  PDF (400 DPI colour-sampled) by BUILD and independently re-read by deep-QA (0 discrepancies).
  Multi-jump pieces (Golden Bird leap-over-3, Wooden Dove jump-to-3rd-then-slide, Great Dragon
  sideways slide-or-jump-2/3) custom. **NO machine oracle** (Ai Ai desktop-only) → geometry anchored
  to the PDF; 5 interpretations documented in rules.md. Labels switched kanji→romaji (chu/dai/sho
  convention; kanji kept in rules.md). perf: legal_moves 3.7ms / in_check 0.056ms (fine for UI,
  weak-but-functional bot). LESSON: for a novel non-standard piece, prefer FORWARD-computed
  attacked() over the fragile reverse-attack maps (shinjuu) — but the shadowed-tables + rebuilt
  reverse-map route also works and is verifiable (sho_shogi, 601k-check clean).

### ▶▶ SHOGI PHASE — wave 2 (THE HARD GIANTS) — PRE-STAGED, next up
The easy/moderate tier is DONE. Everything remaining is large-shogi needing Fire-Demon / jumping-
general / Lion / area-move mechanics that exceed ShogiLike's (slides, leaps) model. Template =
**chu_shogi/game.py** (557 lines: full Lion engine — igui/double-move/distance-2/Lion-trading —
+ Falcon/Eagle custom pieces + POWER_ATT reach; it subclasses ShogiLike but layers heavy custom
movement). dai_shogi = the many-piece-types movement-table template. Build order (verifiability-
first, NOT the old easiest-first):
- **nutty_shogi (13×13) — ✅ SHIPPED #295 (`54b6362`).** Muller's demagnified Tenjiku; 50 pcs/25
  types, drop-less, king-capture/BURN win ("win as event"). Fire Demon (BsR slide + 3-step area move;
  active burn + passive-PRIORITY burn + win-on-burn + safe-capture), jumping generals (rank order
  K>JQ>Regent>JR/JB>others), Lion/Griffon/Harpy (reused chu), Tetrarchs/Eagle/Unicorn. Built from
  the CVP nutty-shogi Betza; chariot d2/buffalo k2 per the EXECUTABLE diagram config (prose disagrees).
  deep-QA MERGE 0-fix (all 5 FD behaviours confirmed, perft 43/1845/85710 root checked piece-by-piece,
  legal_moves 0.52ms), browser-verified (FD centered at g2). **THIS is now the Tenjiku template.**
- **tenjiku_shogi (16×16) — NEXT, template off the COMMITTED nutty_shogi.** The classic; reuses
  nutty's Fire-Demon/jumping/Lion machinery on a 16×16 board with MORE pieces/types (nutty is the
  *demagnified* subset — tenjiku adds e.g. the Vice General / Great General / Heavenly-Tetrarch-class
  pieces and a fuller army, ~78 pcs/side). Weak oracle (no HaChu/pyffish builtin for tenjiku) → lean
  on nutty's proven code + Wikipedia "Tenjiku shogi" + CVP; perft self-anchor. Source the extra
  pieces + the exact 16×16 setup carefully; the "Generals" hierarchy (jumping-rank) extends nutty's.
- **maka_dai_dai_shogi (19×19) — DEFERRED (decision 2026-07-14, orchestrator diligence).** Contested
  Edo-era sources (promote-by-CAPTURE-value etc.) AND **no oracle**: HaChu 0.21's runtime variant list
  is `chu,nocastle,shogi,sho,dai,tenjiku,shatranj,makruk,lion,wa-shogi,werewolf,cashew-shogi,
  macadamia-shogi` — **`maka` is NOT supported** (the "maka" string in the binary is a disabled/partial
  feature). Shipping it = an unverifiable reconstruction of a FAMOUS game → below the faithfulness bar.
  Matches the earlier project decision (skip Dai Dai / Maka Dai Dai in favor of Muller's proxies). Build
  only if Erik explicitly wants a documented-reconstruction; otherwise use the proxies below.
- **tai_shogi (25×25, ~177 pcs) + "mini_tai" — DROP-RECOMMENDED.** No oracle, ~90 piece types, 625-cell
  board ≈ unplayable in the generic UI + very weak bot. Out-of-scope unless Erik wants a display/curio.
  ("mini_tai_shogi" is not a well-defined historical variant.)
- **✅ cashew_shogi #297 (`487c26b`) + macadamia_shogi #298 (`c013262`) SHIPPED — VERIFIABLE finale, SHOGI PHASE COMPLETE.**
  Both deep-QA MERGE-WITH-FIXES (adversarial QA caught a REAL bug in each: cashew a c1/d1+j1/k1 setup
  promoted-flag error via the HaChu-FEN differential; macadamia White's chiral pieces moving mirror-imaged
  vs the 180°-rotation setup). HaChu caveat: search/usermove SIGSEGV on the nut variants → the differential
  is Betza-definition + setup-FEN level (still authoritative; Muller wrote HaChu) + Muller's CVP pages are
  complete. Nut-proxy TRIO now complete: Nutty=Tenjiku, Cashew=Dai Dai, Macadamia=Maka Dai Dai. Original
  build notes below (historical):
- **▶ cashew_shogi + macadamia_shogi (13×13) — the VERIFIABLE large-shogi finale (HaChu-anchored).**
  H.G. Muller's own 13×13 "nut" proxies: **Cashew ≈ demagnified Dai Dai, Macadamia ≈ demagnified Maka
  Dai Dai** (Nutty, already shipped #295, is his Tenjiku proxy). **Both ARE in HaChu 0.21's variant
  list** → a real CECP differential oracle, exactly how Chu #248 + Nutty #295 were anchored. Genuinely
  missing (deduped 2026-07-14). Template off the committed nutty_shogi (same 13×13 Fire-Demon/jumping/
  Lion family). Get each variant's setup + piece set from HaChu's `setup (...)` strings + Muller's
  chessvariants pages (curl -A Mozilla). HaChu ops: `apt-get download hachu` (0.21 .deb, no sudo) →
  `dpkg-deb -x` → `usr/games/hachu`; it speaks CECP/xboard — feed `protover 2` to dump `feature
  variants=`; `variant cashew-shogi` / `variant macadamia-shogi` to select; the invalid-usermove trick
  dumps its root move list; `@@@@` = Lion-pass null. (Chu #248's build used HaChu as a threaded CECP
  differential oracle — reuse that harness.) THIS is the recommended wave-2 continuation over maka/tai.

Op notes carried into wave 2: `.venv/bin/uvicorn` (not on PATH); pyffish 0.0.89 in .venv (general
FSF oracle, load custom variants.ini first or SEGFAULT); HaChu not installed (apt-get download the
0.21 .deb when a Chu/Dai differential is needed — NOT needed for nutty/tenjiku, which have no HaChu
support). pinchtab under WSL: `pinchtab server` foreground via run_in_background; eval works
(allowEvaluate on) but IDPI intermittently blanks eval results → screenshot (pixels) is reliable;
QuickPlay flow = click QUICK PLAY → React-native-setter inject search → click .game-card-main by
exact title → hotseat → START → screenshot.

### (prior handoff below) — updated 2026-07-13

### ✅ OPTION-ADDITIONS wave SHIPPED (2026-07-13) → **289 games**, #289 + 3 option edits
All four done, full suite green ("all tests passed"), committed + pushed (auto-deploy fired for
commit `11031e4`). Per-game selftests + render-shape probes + browser-verify where it mattered.
- **No-Castling Chess #289** (`58821dd`) — Kramnik 2019; ChessLike subclass, `CASTLING=NoCastling`.
  Anchor perft 20/400/8902 + selftest diffs vs `Chess` to prove BOTH castles removed while the
  king still steps. Browser-verified: real chess glyphs, 64 cells, no white-screen.
- **three_check five-check** (`33a7151`) — option `checks_to_win [3,5]` (default 3). Threshold on
  `TCState`, read in `initial_state`, carried through `apply_move`, used in win check + serialized.
  Selftest: same tally terminal at 3 but not 5; the classic forcing line's 3rd check no longer wins
  under 5. Render caption shows "(to win: 5)".
- **reversi size+goal** (`e4b1edf`) — `size [8,10]` (10 = Grand Othello) + `goal [most,fewest]`
  (fewest = Anti-/misère, equal = honest draw). Parameterized helpers by `n`, extended notation
  alphabet to 10 cols, both on state + serialized. Default 8×8/most byte-identical. Browser-verified
  END-TO-END: 10×10 renders (100 cells), move+flip works, notation "B:e4", caption "(fewest wins)".
- **backgammon setup** (`11031e4`, + GAME_STATUS regen) — `setup [standard,nackgammon,hypergammon]`
  (default standard). Named start maps + mirror; win check now compares off[pl] vs the player's
  actual checker total (`_total`) so Hypergammon's 3-checker race terminates (was hardcoded 15).
  Selftest: each setup's exact counts, unknown→standard fallback, a hypergammon race bears off all 3.

**Lessons this wave:** integer option choices (`[8,10]`, `[3,5]`) are fully handled by the frontend
`GameOptions.jsx` (stringify-and-find-back) — used by ~70 games, nil risk. The option infra
(dropdowns → options → `initial_state`) is generic and proven; a standard-render option toggle on an
already-verified game carries nil render risk, so browser-verify only the genuinely-new visual (here:
reversi 10×10). `uvicorn` is at `.venv/bin/uvicorn` (not on PATH). The full suite runs each package's
selftest.py as a SUBPROCESS serially — parent shows low CPU while children work; ~7 min at 289 games,
Python block-buffers the redirected log so it looks empty until the end (not hung — check child procs).

### ✅ BESPOKE-POLYGONS-BOARD grade-B singles — TIER COMPLETE (2026-07-14), ALL 3 SHIPPED (#290-292)
Erik chose this tier + supplied source images (Akimbo/Okimba MHTML pattern). All three shipped +
browser-verified + independently QA'd by the orchestrator. Status:
- **Snodd #290 SHIPPED** (`46d25fc`) — Silverman 2021; Yodd/Xodd's exact parity rules (place 1-2 stones
  either colour, total groups must stay ODD, fewer own groups wins, no draws) on a snub-square tiling
  (degree-5 interior). game.py = faithful line-for-line yodd port with hex adjacency → a GENERATED
  `board.json` graph (pex pattern, pure-stdlib). Board = 84 snub-square points (56 interior degree-5)
  rendered as the dual **Cairo pentagonal tiling** via the existing polygons primitive (NO Board.jsx
  change). Geometry generated programmatically (snub square → Cairo dual) — orchestrator independently
  verified: all 84 cells pentagons, adjacency symmetric/connected, every adjacent pentagon pair shares
  exactly 1 edge + no non-adjacent pair shares any (exact dual), interior degree 5. validate+selftest+
  browser (colour-pick placement, odd-invariant caption). **Generatable geometry = no image needed.**
- **Side Stitch #291 SHIPPED** (`439c54d`) — Duncan 2017 (BGG 223388), the award-winning ORIGINAL that
  our existing exo_hex is the "distilled" sibling of. hexhex-8 (169 cells), 7 colour-sides; group score
  = # distinct colour-sides touched (boundary cell counts for both); recursive lexicographic tiebreak;
  honest draw only on symmetric double-pass. **The 7-arc perimeter map was extracted PROGRAMMATICALLY
  from Duncan's reference board image** (Silverman blog MHTML): detect 169 grey cells → lattice-fit to
  axial → sample each of 42 perimeter cells' border colour(s) → 7 sides each touched by exactly 7 cells,
  7 boundary cells touch two (perfectly symmetric). Orchestrator re-verified embedded PERIM_COLORS = the
  extraction (0 mismatch). Mirrors exo_hex; native hexhex + board.tints render. Confirmed distinct from
  exo_hex (touch-colour-sides vs contain-exo-stones). validate+selftest(8)+browser (7 arcs render).
- **YvY #292 SHIPPED** (`4771599`) — Freeling+Bush; the hard one (loop + territory). base-7 board =
  a **serrated hexagonal board of 147 cells with 21 degree-2 sprout spikes** (21 = "7 sprouts per two
  adjacent sides"). Board extracted from the mindsports image (Erik's `~/Downloads/YvY.mhtml`): detect
  the playable light-grey hexagon (147 cells) vs off-board dark cells, confirm via zoom the sprouts are
  genuine degree-2 spikes separated by off-board gaps, generate+render board.json (polygons). Rules:
  place 1 stone/turn or pass, swap/pie; **LOOP (a group enclosing ≥1 cell) = SUDDEN-DEATH WIN**; else
  double-pass → dead groups (no sprout) removed, score = (sprouts controlled) − 2×(groups), higher
  wins, honest draw on tie. **KEY FINDING (verified by orchestrator):** on YvY *any* enclosure is a
  loop = instant win, so at a pass-pass end NO enclosure survives → the "fenced-in / territory /
  group-merging" machinery is provably INERT and sprout control reduces to occupation; game.py keeps
  the full general enclosure flood-fill (faithful, future-proof) but it computes 0 territory here.
  Independent QA: 6-stone ring → sudden-death loop win + center enclosed; line ≠ loop; scoring &
  dead-group removal correct; no sprout enclosable even walling the whole board. validate+selftest+
  browser (147 cells + green sprouts render, placement + turn advance).
- `medusa` stays DEFERRED (compound multi-move + non-terminating + weak MCTS).

**Tier lessons:** image-sourced bespoke boards → extract the board IMAGE from Erik's saved MHTML
(`email.message_from_binary_file` → walk `image/*` parts) then read it PROGRAMMATICALLY (grey-cell
connected-components → lattice-fit to axial → sample border colours / classify light-vs-dark cells)
— beats eyeballing every time (nailed side_stitch's 7-arc map + yvy's 147-cell serrated board). A game
whose geometry is a DEFINED tiling (snub-square/Cairo) needs no image — generate it. The orchestrator
owns board.json + independent verification (dual-exactness, degree histograms, arc-map re-derivation,
loop/scoring probes); build agents do rules on the given board.

### ▶▶ NEXT WAVE — PRE-STAGED (Erik will pick: SHOGI phase, or a Silverman /games/ wave)
Erik (2026-07-14, pausing) named two directions; a scout of **https://drericsilverman.com/games/**
shows they largely CONVERGE on the shogi family. Full list deduped against the 292-game library
(2026-07-14) — everything below is genuinely MISSING:

**A) SHOGI FAMILY (large/historical/variant) — the "shogi phase".** Anchor with **HaChu** (Chu/Dai
differential, apt-get download hachu 0.21) and **pyffish** (Fairy-Stockfish, any FSF variant, perft +
legal-move differential; load the variant config first or it SEGFAULTs) — both proven this project;
add perft anchors. Candidates, roughly easiest→hardest:
- **sho_shogi** — historical 9×9 precursor to modern shogi (has the drunk-elephant, NO drops). Easiest;
  ShogiLike-adjacent.
- **goro_goro_plus** — extended Goro Goro Shogi (we have goro_goro_shogi #204) — verify what "Plus" adds.
- **shinjuu_shogi** — **Silverman's OWN 11×11 shogi** (designer-original — nice to have his game). Rules on
  his blog/page; verify piece set.
- **wa_shogi** variants aside (we HAVE wa_shogi). **nutty_shogi** — H.G. Muller's "Nutty Shogi" (the
  nut-trio the older queue flagged); needs Muller's page for the piece set.
- **tenjiku_shogi** — 16×16 large shogi with the fearsome "jumping generals" (fire-demon burning, etc.) —
  long-flagged; HaChu can't differential it fully, so perft + careful source (Wikipedia + CVP). HARD.
- **maka_dai_dai_shogi** (19×19) — was blog group-A; huge piece set, promote-by-capture-value rules. HARD.
- **tai_shogi** (25×25, ~354 pieces) + **mini_tai_shogi** — the giants; likely too big for the generic
  UI/bot to be playable — SCOPE before building (may be render/perf-prohibitive; document if dropped).

**B) SILVERMAN /games/ NON-SHOGI (genuinely distinct from what we have):**
- **onyx** — Onyx (2000), connection game on a mixed square+diagonal grid with a CAPTURE mechanic
  (surrounded stone removed). Distinct from our connection games; needs the rules (BGG/designer).
- **hexsymple** — HexSymple, Freeling's Hex+Symple hybrid (we have both hex & symple). Verify it's a
  distinct ruleset, not just a UI mash-up.
- **desdemona** — an Othello/Reversi variant (rotate-the-board twist). VERIFY distinct from our reversi
  (now with size/goal options) before building — may be a near-clone.
- **courier variants** — modern_courier / reformed_courier / courier_spiel (we have base courier_chess).
  Likely thin variants of courier_chess — probably OPTIONS or skip; low priority, verify distinctness.

**Recommendation:** if "shogi phase" → start sho_shogi (easy) → goro_goro_plus → shinjuu_shogi →
nutty_shogi, then the hard giants (tenjiku/maka_dai_dai) with perft+pyffish, and SCOPE tai/mini_tai
before committing. If "Silverman wave" → onyx + hexsymple + shinjuu_shogi are the freshest; check
desdemona/courier-variants for dedup first. `medusa` stays deferred.
- **Large-shogi group A tail** (still partially open — see the group-A notes below; Tenjiku + the
  Muller nut-trio, HaChu/pyffish oracles).
- **A fresh scouted theme** (the library is 289 games — most famous distinct abstracts already exist,
  so new picks are Zillions/CVP/traditional deep cuts; dedup HARD).
Recommend: **ask Erik to pick a direction** (bespoke-board singles vs. group-A shogi vs. a new scout)
rather than auto-starting — none is a clean one-line kickoff anymore.

**Coverage note (kept):** wave-7 leftovers were triaged out — quarto-2×2 DONE (existing option),
bestemshe = a mancala (future), mini_xiangqi clone-rejected, antidraughts/frysk/breakthrough-draughts
= lower-value option/near-clone material.

---

**Current state: 292 games** on `origin/main`, auto-deployed live at
https://abstract-games.onrender.com. Latest = **BESPOKE-POLYGONS grade-B singles TIER COMPLETE
(all 3 shipped 2026-07-14):** Snodd #290 (Cairo/snub-square, generated geometry) + Side Stitch #291
(Duncan, 7-arc perimeter extracted from the reference image) + YvY #292 (Freeling loop+territory,
147-cell serrated board extracted from the mindsports image) — see the ✅ block at the very top.
Prior = **OPTION-ADDITIONS wave (SHIPPED 2026-07-13):**
No-Castling Chess #289 + three_check five-check + reversi size/goal + backgammon setup. Prior =
**wave 7 draughts medley #286–288 (SHIPPED 2026-07-13):** Russian Draughts (any-capture + promote-mid-capture-continues), Spanish
Draughts (forward-only men that CAN take kings + flying kings + max-priority — Italian
inverted), Pool Checkers (Russian but promotion DEFERRED to end of chain). All 3 perft
7/49/302/1469, deep-QA MERGE with the clone gate explicitly passed (Russian vs Pool produce
different legal moves on a mid-capture-promotion position). Committed on the fast-path
(perft anchor + render-shape probe identical to the browser-verified italian/brazilian
draughts). The rest of the variant batch was triaged as options/already-covered — see wave 7
below. **NEXT WAVE = the OPTION-ADDITIONS (Erik chose these 2026-07-13) — PRE-STAGED &
LAUNCH-READY, see the block immediately below.** Prior =
**PerGioco wave 6 #283–285 (SHIPPED 2026-07-13):** Yoxii (Partinico/Cosmoludo totem surround on a 37-cell OCTAGON — brief's
"cross" corrected to octagon from the rulebook; polygons render + valued =CHOICE pieces),
Donuts/INSERT (Cathala; 6×6 random-tile line board, has_randomness, forced-direction +
insertion flips; per-cell lines via board.overlay — no Board.jsx change), Complica (Knizia
1991 Connect-4 with column-push, differential-tested vs AbstractPlay). All 3 deep-QA MERGE
0-fixes (0 mismatches: yoxii 30k totem moves, donuts 6,462 steps, complica 2,000 playouts),
browser-verified. **Next: wave 7 (VARIANT BATCH on existing engines), grade-B singles — see
below.** Prior = **PerGioco wave 5 #280–282 (SHIPPED 2026-07-13):** Strands (Bentley largest-group placement on a numbered hexhex — numbers
render as neutral labelled discs, no Board.jsx change; incremental single-cell placement
avoids a move blowup), Italian Draughts (traditional 8×8 per the FID rulebook — short
non-flying kings, men can't take kings, full mandatory-capture priority chain; a build-agent
correction fixed my wrong "flying kings" brief), Alvéole (hex Lines of Action, differential-
tested vs the author's open-source BGA implementation). All 3 deep-QA MERGE (0 mismatches:
strands scoring/120 games, italian 400 games, alveole 76,000 positions), browser-verified.
**Next: wave 6 (yoxii/donuts/complica), wave 7 (variant batch), grade-B singles — ranked
queue below.** Prior = **PerGioco wave 4, the Mark Steere trio #277–279 (SHIPPED 2026-07-13):** Icebreaker (hexhex gradient-capture, BFS-around-ships
distance, capture the majority of icebergs), Silo (1×6 stacking consolidation, `piece.stack`
towers, opposite-side "your right", pie rule), Rive (hexhex group-minimisation capture with
multi-placement turns — the intricate one; QA reproduced Figs 3b/3d exactly + dropped the
size 5/7 options to avoid a legal_moves explosion). All three built from Steere's official
PDFs (vector figures rendered to images), independent adversarial deep-QA (0 differential
mismatches: icebreaker 2,966 positions, silo 20,339 moves, rive 7,900 positions), browser-
verified, one commit each. **Next: wave 5 (strands/italian_draughts/alveole), waves 6–7, the
variant batch — see the ranked queue below.** Prior = **#275 Akimbo + #276 Okimba** (Bolaños
Mures 2026, Rhode's successors — Erik saved their BGG pages as MHTML + pointed at the
designer's reference JS at github.com/luigio/games; both deep-QA MERGE + browser-verified,
see the 2026-07-13 SHIPPED block below). Prior: #266–274 PerGioco gap-fill, #248–265
Group A large shogi + mixed wave. **Both long-standing Erik flags now RESOLVED (2026-07-13):
Emulsion tie-rule + pie (`368f86b`), Crossway transpose-mirror swap (`8f68c1b`) — see the
"✅ Flags" block below.** No open flags.

### SHIPPED (2026-07-13) → **276 games**, #275–276
- **akimbo #275** — Bolaños Mures 2026 (BGG 466041), Rhode's *capturing* successor. Default
  13×13; legal iff ≤1 naked diagonal PER COLOUR on the raw board BEFORE removal ("not even
  momentarily"); completing a crosscut removes your OTHER stone. Pie rule, drawless.
- **okimba #276** — Bolaños Mures 2026 (BGG 468749), the *no-captures* successor. Default
  11×11 (per BGG "11×11 Grids"); legal iff ≤1 naked diagonal TOTAL across both colours →
  crosscuts can never form → no removals. Pie rule, drawless.
- Both: template = games/rhode; built from the designer's own reference JS (Akimbo.html/
  Okimba.html) + Erik's saved BGG MHTML. Independent adversarial deep-QA reimplemented the
  ref naked-diagonal counter from scratch and found **0 mismatches** (akimbo: 28,591 legality
  + 783,642 removal; okimba: 16,870 legality + 20,000 naked-count), 0 draws in playouts,
  honest [0,0] double-pass + ply-cap backstops. pinchtab browser-verified both (render, edge
  colours, place + pie-swap button). One commit each.

---

Previous handoff (2026-07-03): tree clean, HEAD `4db62cf`, **227 games**.

### Blog run, group B COMPLETE (2026-07-01 → 07-03) — all 9 chess variants, #219–227
Erik picked group B of the Silverman-blog queue. Per game: build agent (source-verified) →
orchestrator gate (validate+selftest+render probe) → **independent adversarial deep-QA agent**
(fetches sources itself, own probe scripts, fixes or verdicts) → browser-verify → commit → push.
All 9 = MERGE (2 with trivial fixes: a bot piece-value tweak, a docstring).
- **#219 Opulent Chess** (Strong 10×10): Lion=HFD, Wizard=CF, N+wazir; Grand promotion. perft d1=52 hand-verified.
- **#220 Grand Shatranj** (Joyce 10×10, D preset): KAD/WDN/FAN leapers, Oliphant/War-Machine 2-leg riders,
  baring win; QA ran an exhaustive 8-ray×27-occupancy rider oracle (0 mismatches).
- **#221 Gross Chess** (Duniho 12×12): Cannon/Vao, flexible castling, 1/2/3-step pawns + multi-square e.p.,
  tiered pool promotion. perft d1=72 hand-verified, d2=72² structurally proven.
- **#222 Elven Chess** (Muller 10×10): Warlock = full Chu-Shogi Lion (double moves `f>m>t`, igui `f>m>f`, pass)
  + iron/royal-for-one-turn anti-trade rules (stateful iron flag in poskey); 3-square castling.
- **#223 Caissa Britannia** (Duniho 10×10): ROYAL QUEEN (through-check ban, facing ban), Dragon DDAA,
  Unicorn B+Nightrider, Lion=Leo, liberation promotion.
- **#224 Metamachy** (Cazaux 12×12): double-step from ANY square + e.p. anywhere, 16-direction one-time
  King jump, Eagle gryphon; placement variant fixed to default array (future manifest option).
- **#225 Omega Chess** (MacDonald): **first non-rectangular ChessLike** — 12×12 embed, `on()` override
  (104 cells), polygons render w/ detached purple wizard squares (NO Board.jsx change); official 0–9/w1–w4
  notation; both published Wikipedia mate lines replayed as anchors.
- **#226 Decimaka** (Muller 10×10): promote-on-CAPTURE (F→Q, N→NN, T→Trident, others→Omni; Q-capture
  override); pawns go dead on last rank. Builder died at session limit post-gates → the QA agent's
  independent source extraction doubled as the build report (pattern worth reusing).
- **#227 Zanzibar-XL** (Cazaux 12×12, 80 pieces/19 types): setup phase as **reserve-tray drops** (`L@c,r`,
  reuses the Crazyhouse primitive — no UI change); Eagle/Rhino bent riders w/ reverse ray-traced attacked()
  (differential 800 pos × 144 sq, 0 mismatches); validate 87s after perf work.
**Ops lessons this run:** 5-hour session limits killed whole agent waves repeatedly (13 agent deaths) —
partial packages must be deleted + relaunched fresh (or gate-checked if complete); when the **Fable model
cap** hit, relaunching agents with `model: "opus"` worked fine for build/QA. Stagger launches (≤3) so a
limit kills less in flight. pinchtab agent sessions expire between waves — recreate per batch.

### ▶ NEXT: blog groups A & C still queued (see below)
Group A = large shogi (Chu 12×12 … Maka Dai Dai 19×19; verify the joke "nut-named" ones), group C =
connection/Y/hex family (Iris/Lotus/Medusa/…/Y-variants; hex/polygons primitives exist, verify render needs).
Plus long-flagged Tamerlane & Bao.

### Group C SCOPED (2026-07-04) — two research agents, all 19 titles resolved; builds started
**Y-family (7 names → 4 buildable):** `odd_y` [A; Bill Taylor 2015, BGG 223551; one package w/ `sides` option
5(default)/7 ABSORBS "5-Y" and Ea Ea's "Star-Y" (same win rule: 3 sides whose midpoint-triangle contains center;
pentagon = any 3 non-consecutive sides); reuse poly_y mudcrack board] · `xodd` [A; Bolaños Mures 2011, BGG 112111,
mindsports /624-xodd; = yodd parity rules on square grid w/ orthogonal adjacency, size 9-13] · `superstar` [B;
Freeling mid-1980s, mindsports /552-superstar; 12-sided star hex board, scores stars(edge-touch) + superstars
(5×(S−2) sides connected) + loops(empties + 5/trapped enemy); board must be reconstructed from diagram; komi
unestablished → document tie rule like starweb] · `snodd` [B+; Silverman 2021, blog-only, designer-playtested only;
= yodd on snub-square tiling VERTICES (degree 5); optional] · **Double Star = only as a `star_star` (*Star) build
w/ stones-per-turn 1/2 option** [B; Ea Ea; gamepuzzles.com/starbook-final.pdf pp.14-22; *Star itself is a real
library gap — our `star` is Schensted's earlier different game; scoring invariant: combined = edge cells + 1, odd].
**Designer dozen (all complete rules, ranked):** 1 `permute` [A; Silverman 2020; 2×2 twist+bandage, full chequerboard,
catchup-cascade scoring, provably terminates] · 2 `tintas` [A; Dieter Stein 2016, spielstein.com; 49-cell hexhex-4+
6 pinwheel bumps (axial coords in scout report), 7×7 colors random spread, shared pawn collects, ≤49 turns,
has_randomness] · 3 `ayu` [A; Bolaños Mures 2011, mindsports /724; 11×11 interleaved-singleton setup, amoeba
moves w/ approach-closest rule, CAN'T-MOVE=WIN, repetition=draw] · 4 `exo_hex` [A; Duncan 2019, BGG 291638; hexhex-7
odd + exterior exo-stone strings, best-group-by-exo-stones + recursive tiebreak, pie] · 5 `iris` [A; Duncan 2019,
BGG 286792; hexhex-5, 1-then-2-stones protocol, colored-rim forced 180° pair placement, atomic pair move `c1>c2`] ·
6 `side_stitch` [A; Duncan 2017, BGG 223388; hexhex-8, 7 six-cell perimeter arcs (hard-code from image), best-group
sides-touched + recursive tiebreak; SIBLING of exo_hex — ship both or prefer exo_hex] · 7 `rosette` [A; Mark Berger
1975 (NOT Freeling), mindsports /1098; Go on honeycomb VERTICES (6n², base-5=150 default) + rosette immunity,
superko, area scoring] · 8 `lotus` [A−; Freeling pre-1992, mindsports /538; REUSES kensington 72-point board;
Go liberties + Othello-FLIP capture (cascading re-reversal), lotus immunity, pass-marker track, provably ends] ·
9 `pex` [B; Bush + Marjorie Rice 2008, iggamecenter rules; Hex verbatim on Rice type-11 pentagon tiling (5/7-degree
cells) — all effort = polygons board construction, 8×8=128 cells] · 10 `yvy` [B; Freeling+Bush 2009, mindsports
/555; board+sprout map must be transcribed from diagram; loop=instant win, sprouts−2×groups scoring, "fenced in"
needs formal def] · 11 `volo` [B; Dieter Stein 2010; hexhex-7 points −corners−center=120, bird placement/flock
line-flight, region-removal w/ mover's survival CHOICE inside move, needs loop guard] · 12 `medusa` [B-DEFER;
Freeling; compound turns (place + per-group slides w/ lost-move state), non-terminating → cap, weak MCTS — cost].
Full quoted rules + URLs in the two scout reports (session transcript); sources re-fetchable
(mindsports/spielstein/iggamecenter/drericsilverman fetch fine; BGG via
api.geekdo.com/api/geekitems?objectid=<id>&objecttype=thing or Wayback).

### Group C SHIPPED so far (2026-07-06) — #228–232 committed+pushed, all deep-QA'd + browser-verified
- **#228 Xodd** `85fe1ee` — QA MERGE (legal-move exactness vs brute force ~3600 pos; 330-game fuzz).
- **#229 Odd-Y** `c851854` — QA MERGE-WITH-FIXES (dead import); triple tables derived 3 ways; pentagon
  graph-identical to poly_y; 550 full boards single-winner. Pentagon+heptagon both browser-rendered.
- **#230 Permute** `50abe26` — QA MERGE; swap-semantics proven; 2-click twist + CW/CCW picker + ✕ bandage
  all work in browser.
- **#231 Ayu** `436277b` — QA MERGE; setup + distance rule verified against the official Dagaz JS engine;
  3440-position adversarial exactness. LESSON: distance-rule readings proven equivalent.
- **#232 Exo-Hex** `9df0c31` — QA MERGE-WITH-FIXES: **genuine tie → DRAW (never invent a winner —
  build had an unsourced 'White wins ties' fallback; random early-double-pass games tie ~12%)**.
### Group C batch 2 SHIPPED (2026-07-06) — #234–236 committed+pushed+deployed, all deep-QA MERGE + browser-verified
- **#234 Iris** `e6be652` — QA MERGE, 0 fixes; antipodal-pair protocol exact vs reference over 2132 pos.
- **#235 Rosette** `3f983cf` — QA MERGE, 0 fixes; honeycomb graph rebuilt (Euler verified), rosette immunity
  both directions, situational superko. Go-on-honeycomb-vertices, 150-pt board renders clean.
- **#236 Lotus** `89e11db` — QA MERGE, 0 fixes; flip-capture cascade verified on a real 13-stone case,
  27,615-placement fuzz vs independent _resolve. Reuses kensington 72-vertex board.

### Group C batch 3 SHIPPED (2026-07-06) — #237–238 committed+pushed+deployed, both deep-QA MERGE + browser-verified
- **#237 Superstar** `ee3cda8` — QA MERGE, 0 fixes; Freeling 12-sided star board (Starweb 217 cells + 60-cell
  edge ring, verified byte-identical to starweb + edge recomputed), 12-side partition confirmed, star/superstar/
  loop scoring fuzzed vs referees over 3000 chains + 1000 boards. Star board + gold edge ring renders clean.
- **#238 Volo** `8186489` — QA MERGE, 0 fixes; Stein bird-flocking unification, 120/84-pt hexhex; 648 fly moves
  audited; 'mover never self-fragments' PROVEN (validates single-suffix region encoding); win-priority confirmed.
  `hex`-render (corners/center show empty-unplayable, cosmetic-safe, no crash).

### ▶ REMAINING group C (2026-07-06): **11 games shipped this session (#228–238)** = xodd, odd_y, permute, ayu,
exo_hex, tintas, iris, rosette, lotus, superstar, volo. Left in group C, all HARDER/lower-value long tail:
- **side_stitch** (Duncan 2017, BGG 223388) — grade A but flagged a near-sibling of exo_hex (both best-group
  hexhex scoring); the 7-arc perimeter table must be hard-coded from the image. DEFER-ABLE.
- **pex** (Bush + Marjorie Rice 2008) — grade B; Hex verbatim on the Rice type-11 pentagon tiling; all effort =
  constructing that polygons board (5/7-degree cells).
- **yvy** (Freeling+Bush 2009) — grade B; board+sprout map must be transcribed from the mindsports diagram;
  loop=instant-win, sprouts−2×groups scoring, "fenced in" needs a formal def.
- **snodd** (Silverman 2021) — grade B+; yodd on a snub-square tiling (degree-5 vertices) — near-clone geometry,
  designer-playtested only; needs a snub-square polygons board.
- **star_star** (*Star + Double Star as a stones-per-turn option) — grade B; a REAL library gap (our `star` is
  Schensted's earlier different game) but needs the bespoke *Star tournament board + edge-ownership scoring.
- **medusa** — DEFERRED (compound multi-move turns + non-terminating + weak MCTS = high cost/low payoff).
### ZILLIONS connection-games scout (2026-07-06, Erik-directed) — mined theme=4 (~1800 mostly mis-tagged entries,
775 parsed, top ReadMes read). Best genuinely-distinct picks (mostly Luis Bolaños Mures); geometry all
square/square-intersection/hex-of-hexes = NO new render primitive; rules live in the .zip ReadMe (skill ports fine):
1. **Ordo** (Dieter Stein 2009, id=2345) — grade A, TOP PICK; stay-connected race, men + line-slide "ordo" move,
   all your men must stay one 8-connected group; win = reach back row / split enemy. **BUILDING NOW.**
2. **Stigmergy** (Bolaños Mures & Metzger 2021, id=3126) — grade A/B; hex-of-hexes line-of-sight control + flip +
   area score. Distinct from tumbleweed (no stacks). Ship this, SKIP its sibling Robble(3117) + square-cousin Pletore.
3. **Emulsion** (Bolaños Mures 2020, id=3089) — grade B, VERY clean; full square board, swap-only (swap must raise
   your piece value), largest-group scoring, PROVABLY FINITE (monotone potential, no cap). Totally novel.
4. **Flipway** (Bolaños Mures 2020, id=3051) — grade B; 2×2 multi-drop + crosscut-flip, connect your two edges,
   drawless. Head of a family (Morpheus/Squer/Rhode/Flicker/Cation = near-dups → ship ONE, Flipway is cleanest).
5. **Pletore** (id=3198) — square cousin of Stigmergy; ship only if we want both (prob skip — near-dup of Stigmergy).
6. **Cation** (2016, id=2500) — grade B; row-flip connection; ReadMe lacks rules → needs designer's public rules first.
7. **Konobi** (2012, id=2014) — grade B; square drawless connection w/ weak-diagonal restriction; FLAG dedup vs
   crossway (closest existing) — confirm before building; ReadMe boilerplate → needs designer rules.
REJECTS (already-have/clone/off-theme): crossway(have), Morpheus/Squer/Rhode/Flicker(Flipway near-dups), Robble
(Stigmergy sib), Kopano(Konobi sib), Peon(=Cation), DiaGo(Go variant), HexHive(Hex reskin), Foxxy(fox&geese),
Faction(extermination not connection), Karl-Scherer solitaire puzzles, mis-tagged shogi/chess/dama bulk.
Recommended port order: Ordo → Stigmergy → Emulsion → Flipway → (Cation/Konobi after rule-verification).

**PROGRESS (2026-07-07): Ordo SHIPPED (#240). Next 3 STAGED + BLOCKED ON MODEL LIMITS — Emulsion, Stigmergy,
Flipway build agents were launched (full briefs ready, all 3 ReadMes already fetched/confirmed complete) but ALL
died: Opus session limit (resets 12:30am PT) AND Fable usage-credit limit both hit. Nothing on disk (clean).
TO RESUME: relaunch the 3 builds on opus (after 12:30am PT reset) or fable (after credits refill) — briefs are in
the session transcript; each = download the Zillions .zip ReadMe (authoritative), verify vs designer/BGG, implement,
selftest, then deep-QA + browser + commit. Stigmergy default board = hexhex side-8 (per its .zrf), reuse tumbleweed
geometry; confirm distinct-from-tumbleweed (no stacks). Emulsion = full-board swap-only, provably finite. Flipway
= 2×2-drop + crosscut-flip connection (drop-maximality is the subtle rule). After these: Cation/Konobi need the
designer's public rules first; then remaining known-C (yvy/snodd/side_stitch) or group A (large shogi).**
**NOTE: zillions-to-platform skill last updated 2026-06-18 — still works (procedure doc); could refresh with newer
render primitives if a Zillions game ever needs one, but this batch is all standard square/hex so not needed.**

### SHIPPED (2026-07-10): the whole staged wave + Cation/Konobi/Rhode → **247 games**, #242–247
All six = build agent → orchestrator gate → independent adversarial deep-QA (own source fetch + differential
probes) → browser-verified (batched backend restart, pinchtab QuickPlay, signature move played) → committed →
pushed. Erik supplied saved-MHTML BGG rules for Cation/Rhode (designer thread 1593043) and Konobi (game page),
unblocking the rule-verification gate; Rhode added on Erik's call (same thread as Cation; designer later
superseded it with Akimbo/Okimba — noted in its rules.md; those two are future candidates).
- **#242 Emulsion** `d8f6546` — swap-only largest-group, designer-authored ReadMe anchor; QA MERGE-WITH-FIXES
  (doc-only). Deep-QA diff 0 mismatches / 1,439 positions; 122 genuine even-board full ties matched.
- **#243 Stigmergy** `9fa1716` — LoS-control hexhex territory + komi/button; QA MERGE 0 fixes (9,186 positions,
  132 games, exact match; .zrf flag machinery decoded as cross-check). Distinct from tumbleweed (no stacks).
- **#244 Flipway** `3df00e8` — maximal-2×2-drop + crosscut-flip connection; QA MERGE-WITH-FIXES — **real rules
  bug caught**: checkered-setup opening must be a single white-stone replacement, not a flip (fixed).
- **#245 Cation** `0eb0051` (+ swap fix `2ab169e`) — crosscut-ko connection; builder died post-write at a session
  limit → deep-QA served as the sole independent check (Decimaka pattern): MERGE 0 fixes, 12,272 states diffed,
  both designer-recorded games replayed. "Streamlined Cation" (Apr 2026 designer post) is unpublished — 2016
  rules implemented with a version note; revisit if he publishes it.
- **#246 Konobi** `5957530` — weak-connection-ban connection; build found an argument-transposition TYPO in the
  designer's .zrf (contradicts the rule text embedded in the same file); QA independently CONFIRMED (717/21,271
  positions diverge as-written; corrected reading = prose exactly). Official PDF sample game replayed.
- **#247 Rhode** `7ac73a2` — forced weak-pair completion + crosscut self-removal; QA MERGE-WITH-FIXES (pie swap
  → value-preserving transpose mirror); win-timing-after-removal anchored both ways (540 break cases).

### ✅ Flags for Erik — BOTH RESOLVED (2026-07-13, Erik-directed)
1. **Emulsion even-board tie rule — RESOLVED** (`368f86b`): aligned to the designer's CURRENT BGG description
   (last mover LOSES + added the pie rule), which supersedes the 2020 Zillions ReadMe — same precedent as Rhode
   being superseded by Akimbo/Okimba. Pie = recolour-all + pass-to-Black (colour-inversion symmetry); tie flipped
   in `returns()`. Verified: pie preserves the shared move set (0/400), tie flips both ways, browser-verified
   (Swap button appears + applies + recolours). Default 9×9 (odd) never triggers the tie regardless.
2. **Crossway pie swap — RESOLVED** (`8f68c1b`): now transpose-mirrors (c,r)→(r,c) + recolours (was recolour-in-
   place), matching Rhode/Cation/Konobi. Verified value-preserving over 3,000 boards (0 mismatches both
   directions) + browser-verified (open b4 → swap → single White stone at 3,1).

### ▶ NEXT-WAVE QUEUE scouted 2026-07-11 (Zillions/CVP/designer sites; Erik-directed overnight run)
All deduped vs the 248 uids + prior rejects; sources fetched + verified complete. Build in mix-balanced waves of 3:
1. **cannon_game** [A; Whitcher 2003; 10×10 soldiers form 3-in-line "cannons" that slide/shoot; nestorgames PDF +
   iggamecenter + Zillions id=150; distinct vs mak_yek/xiangqi/epaminondas] · **murus_gallicus** [A; Leduc 2009; 8×7
   tower-distribution walls; Wikipedia + nestorgames PDF + Zillions id=1891; piece.stack ht-2] · **duck_chess**
   [A-; Paulden 2016; chess + shared duck blocker moved after each move (backgammon sub-move pattern, king-capture
   win); Fairy-Stockfish `duck` = perft oracle]
2. **mixtour** [A; Stein 2011; 5×5 stack-climbing, move dist = target height; spielstein rules; CYCLABLE → no-progress
   cap] · **blooms** [A; Bentley 2018; hexhex two-colors-each, fenced-bloom capture, BGA oracle] · **shatar** [A-;
   Mongolian chess; FSF `shatar` oracle; shak/tuk mate-class rules = crux, document FSF's interpretation]
3. **byte** [A; Steere 2005; merge-only stacks, pyramid-of-8 scoring; marksteeregames PDF] · **dodo** [A; Steere 2021;
   hex misère blocking race, first-stuck WINS; PDF] · **shogun_chess** [B+; crazyhouse hybrid w/ rank-6 shogi
   promotion + demote-into-hand; FSF variants.ini oracle; CrazyhouseDrops shipped]
4. **omega_nra** [A-; Romeral Andrés 2010; hex, place one stone of EVERY color, PRODUCT-of-group-sizes scoring,
   2-4p; nestorgames PDF] · **urbino** [A-; Stein 2018; shared architects + building placement, district scoring;
   =CHOICE picker for building type] · **congo** [B+; Freeling 1982; 7×7 animal chess, river drowning + monkey
   chain-jumps; Wikipedia complete]
5. **veletas** [B+; Bolaños Mures 2013; shared queen-shooters claimed by immobilization; nestorgames PDF] ·
   **banqi** [B+; Dark Chess 4×8 flip-reveal, Taiwanese hierarchy; randomness-in-state pattern, has_randomness] ·
   **tamerlane_chess** [B+; c.1400, 11×10+citadels (omega_chess non-rect precedent), CVP complete] or
   **hexagonal_chess** [B+; Gliński 91-cell hexhex; NO oracle, custom engine — biggest single build; stalemate=¾
   point → implement draw + document]
Backups (sources verified): redstone/king_and_courtesan (Steere, capped to avoid flooding), abande/attangle/accasta
(Stein seam), breakthru (Randolph 1965, 2-moves pattern; name-confusion warning vs breakthrough), onyx (connection
fatigue), neutron, isolation, salta, jetan (CVP mainline + document ambiguities), CwDA (armies as options), raumschach
(5×5×5 via qubic layers), chad (mindsports, find page via site search). **✅ Akimbo/Okimba SHIPPED
#275–276 (2026-07-13)** — Erik saved the BGG pages as MHTML + pointed at the designer's reference JS
(github.com/luigio/games); see the 2026-07-13 SHIPPED block at top.
Rejects logged by the scout (clones/render-heavy/contested-rules): hexdame, morabaraba, chaturanga, sho_shogi,
minixiangqi, gothic/embassy, LYNGK, avalam, terrace, rithmomachia, kriegspiel/bughouse (hidden info/two-board),
rococo, avalanche, palago/akron/margo/shibumi, six/kulami/katarenga/barragoon/boku/chase/bizingo/djambi.
Zillions gotcha: theme-listing URLs are dead — the submissions.cgi search is POST-only (`search_term`); name-search works.

### SHIPPED overnight 2026-07-11 (Erik-directed autonomous run) → **253 games**, #248–253
All six: build → orchestrator gate → independent adversarial deep-QA → browser-verified → committed → pushed.
- **#248 Chu Shogi** `c20d77b` — the Group A flagship. Lion-trading + counterstrike rules; HaChu differential
  (551 build + 600 QA self-play moves replayed w/ per-ply board sync; 4,144 root-list moves compared; perft
  36/1,296/48,819 d1-HaChu-confirmed); deep-QA MERGE 0 fixes, independent 28-move-kind audit; QA also proved
  HaChu 0.21 itself deviates from the written spec in 2 spots (package correct). Ubuntu `hachu` binary +
  threaded CECP driver patterns live in the session scratchpad (`scratchpad/chu/`).
- **#249 Heian Dai Shogi** `26f7002` — 13×13 Nichūreki reconstruction; check rules + bare-king win (sourced);
  perft 29/841/25085; deep-QA MERGE 0 fixes (independent generator, 7,200-position diff exact). FD→Dragon Horse
  + Iron-not-forced source-conflict calls upheld.
- **#250 Dai Shogi** `563a4d2` — 15×15, Chu core + 8 weak pieces (VO/FD = new bounded-slide RANGED mechanism);
  NO Lion-trading (triple-sourced + contrast-tested vs chu); promo zone = 5 (CVP diagram typo identified);
  perft 71/5041/357978; two clean HaChu differentials (build + QA); deep-QA MERGE 0 fixes.
- **#251 Duck Chess** `545b20c` — chess + shared duck; fowling = stalemated player WINS; pyffish perft
  640/379,440 exact + 23 games full turn-set equality across build+QA; deep-QA MERGE 0 fixes.
- **#252 Cannon** `9768e84` — Whitcher soldier/cannon-formation; plain-capture Town win (the .zrf 'checkmated'
  idiom documented as the alternative reading — the one judgment call); long-shot-over-occupied-middle legal
  (rulebook + .zrf beat iggamecenter's paraphrase); deep-QA MERGE doc-only, 19,840 positions 0 mismatches.
- **#253 Murus Gallicus** `be430cd` — Leduc tower-distribution siege; deep-QA MERGE 0 fixes (12,888+568+200
  positions exact); QA constructed a REAL repetition shuttle cycle proving the threefold backstop necessary.
Group A remaining: Tenjiku (XL, no oracle) → unlocks Nutty/Mitsugumi; Cashew/Macadamia as the sanctioned
Dai-Dai/Maka-Dai-Dai proxies. Next-wave queue (above): wave 2 = mixtour/blooms/shatar.

### SHIPPED overnight waves 2-4 (2026-07-11) → **262 games**, #254–262
Same pipeline per game (build → gate → adversarial deep-QA → browser → commit → push). All MERGE.
- **#254 Mixtour** `a4ce811` — Stein stack-climber; ko-triple proven ≡ board restoration (QA: 15,644 pos).
- **#255 Blooms** `44f184e` — Bentley two-colour hex capture race, v2.0 ruleset (boardspace's 1.0 rejected);
  4-colour per-piece fill render; end-of-turn simultaneous capture confirmed vs sources (QA: 22,344 states).
- **#256 Shatar** `1632305` — Mongolian chess, shak/tuk/niol/robado mate classes; full pyffish differential
  (perft d1-4 exact; ~102k positions QA); shak-chain state serialized.
- **#257 Byte** `26f7002`-family — Steere merge-only pyramids; QA attacked the Chebyshev metric w/ BFS —
  proven identical on all dark-square pairs; Fig 6 replayed checker-for-checker.
- **#258 Dodo** — Steere misère hex race; setup blob-detected from the PDF figure by build AND QA
  independently; size-2 solve reproduced; BGA random-play stats matched.
- **#259 Shogun Chess** — crazyhouse/shogi hybrid; pyffish perft d1-4 exact; **QA caught a REAL bug**
  (50-move counter not reset on promotions) — fixed + anchored.
- **#260 Omega (omega_nra)** — Romeral Andrés product scoring; place-both-colours sub-turns; rulebook's
  explicit Black-wins-ties; QA 18,320 pos 0 mismatches. (Scout's BGG id was wrong; corrected to 81588.)
- **#261 Congo** — Freeling 7x7 animal chess; timer-less drowning proven equivalent; monkey chains;
  QA 39,325 pos lockstep 0 mismatches; perft 24/576/14332.
- **#262 Urbino** — Stein shared-architect districts + official Monuments option; QA clean-room matched
  all 8,923 plies; all official scoring examples reproduced.
**Remaining scouted queue: wave 5 = veletas + banqi + (tamerlane_chess or hexagonal_chess — Erik's pick;
Gliński hex is the biggest single build, no oracle). Backups list above. Group A: Tenjiku/nut-trio.**

### SHIPPED wave 5 (2026-07-11) → **265 games**, #263–265
- **#263 Veletas** — Bolaños Mures shared-shooter claiming; QA clean-room ~14k plies, both rulebook examples;
  drawless proof verified. (Scout BGG id wrong again — verify ids; correct = 151224.)
- **#264 Banqi** — Taiwanese Dark Chess; randomness-in-state; QA exhaustive capture matrix + 80k-ply diff +
  render-leak audit (face-down pieces never expose identity).
- **#265 Tamerlane Chess** — the long-flagged historic marquee; 11 pawn types, pawn-of-pawns lifecycle,
  citadel draw, king-swap; perft 24/576/14518; QA node-level move-set equality through the perft tree.

### ▶ PerGioco Masters gap-fill IN PROGRESS — 9 shipped (#266–274), waves 1–3 done
**SHIPPED (all deep-QA MERGE + browser-verified):** zola #266, boop #267, mijnlieff #268 (solved: 2nd-player win,
verified via a 2.47B-node alpha-beta solve), neutreeko #269 (solved: draw, full 3.4M-position retrograde solve
reproducing all published stats), bobail #270, oxono #271, squadro #272, qawale #273, soluna #274. Coverage now
~57/78 categories (~73%). **NEXT: wave 4 = icebreaker + silo + rive (Mark Steere trio, uniform PDF sourcing +
BGA anchors), then wave 5 (strands/italian_draughts/alveole), wave 6 (yoxii/donuts/complica), wave 7 (VARIANT
BATCH on existing engines: draughts medley, othello variants, five-check/no-castling chess, mini xiangqi,
bestemshe, nackgammon), then the grade-B singles.** Full ranked queue below.

### PerGioco Masters coverage (Erik-directed, scouted 2026-07-11) — was **48/78 (~62%)** at scout time
Roster from pergioco.net/live/pgmasters (IIS bot-block needs full browser headers) + the 2026 schedule PDF +
playstrategy.org/variant. Platforms are BGA/PlayStrategy/AbstractPlay ⇒ every gap has a live online anchor.
All heavyweights already covered (GIPF project, draughts family, Hex/Havannah/Twixt, shogi/xiangqi/go, etc.).
**Ranked gap queue (waves of 3; waves 1–7 ⇒ ~83% coverage):**
1. ✅ zola #266 · boop #267 · mijnlieff #268 (SHIPPED 2026-07-11)
2. ✅ neutreeko #269 + bobail #270 · oxono #271 (SHIPPED 2026-07-11)
3. ✅ squadro #272 · qawale #273 · soluna #274 (SHIPPED 2026-07-12)
4. ✅ icebreaker #277 · silo #278 · rive #279 (Mark Steere trio, SHIPPED 2026-07-13)
5. ✅ strands #280 · italian_draughts #281 · alveole #282 (SHIPPED 2026-07-13)
6. ✅ yoxii #283 · donuts #284 · complica #285 (SHIPPED 2026-07-13)
7. **✅ DRAUGHTS MEDLEY SHIPPED (2026-07-13): russian_draughts #286 · spanish_draughts #287 · pool_checkers #288**
   (3 genuinely-distinct national 8×8 variants; clone gate PASSED — Russian promote-continue vs Pool deferred
   promotion produce different legal moves; Spanish = Italian inverted [men-take-kings + flying kings]; all
   perft 7/49/302/1469, deep-QA MERGE). REST OF THE VARIANT BATCH = better as OPTIONS or already covered, NOT
   built (orchestrator triage): reversi/three_check/king_of_the_hill/checkless_chess/xiangqi/backgammon/nard/
   quarto ALL EXIST → five-check (three_check checks=5 option), no-castling chess, grand/anti othello (reversi
   size+misère options), nackgammon+hypergammon (backgammon start-setup options), quarto-2×2-wins (quarto
   option) are one-toggle OPTION additions, deferred to Erik. **bestemshe = a MANCALA** (Kazakh 5-pit
   Toğyzqumalaq-family, not draughts) — future mancala add. mini_xiangqi previously clone-rejected. antidraughts/
   frysk/breakthrough-draughts/scrambled-eggs-LOA = lower-value option/near-clone material, deferred.
8. B-grades by value: cairo_corridor (Cairo pentagon tiling, pex board.json precedent) → fendo (Stein, board.walls)
   → enso (Stein) → bug (Bentley; shape-equality crux) → tanbo → linkage (nestorgames PDF) → pyrga →
   battle_of_lits → sensei/diaballik → siam → onyx (backup-list; new justification) → four → hus (DEDUP vs
   omweso!) → exit_strategy (verify rules) → kulami (prior reject; reopenable via board.json) →
   patchwork/marrakech/kingdomino (euro-weight, last).
NOT PLATFORM FIT: colorpop (secret colour = hidden info), 61-autumn-leaves (roll-and-write), flowers (card
drafting), lucky_numbers (low value). Full per-game sources in the scout report (session transcript) +
fetched pages in the session scratchpad `scout_pergioco/`.

### ▶ Group A (large shogi) STARTED 2026-07-10 — scout complete, Chu Shogi build in flight
Scout resolved the whole queue (full report in session transcript): **build Chu (12×12, M/L, flagship —
Wikipedia article is implementation-grade and is HaChu's own spec; `apt install hachu` = differential oracle,
incl. Lion-trading rules w/ okazaki toggle) → Dai (15×15, M — Chu core + 8 weak step-movers, NO Lion-trading
rules) → Heian Dai (13×13, S freebie, partially-reconstructed rules documented) → optionally Tenjiku (16×16,
XL, NO oracle — HaChu's attempt failed; jumping generals + Fire Demon burn + partial-Lion pieces = 3 new
mechanisms) which then unlocks Nutty/Mitsugumi as M follow-ups. SKIP historic Dai Dai (17×17) & Maka Dai Dai
(19×19): Edo sources contradict each other piece-by-piece, no oracle, 96 pieces/side — Muller's 13×13 Cashew
(Dai-Dai-flavor) + Macadamia (Maka-Dai-Dai-flavor) are the clean modern proxies. **Nut-named verdicts: ALL
REAL** (Muller: Nutty/Cashew/Macadamia 13×13 shrinks; DeWitt: Suzumu 16×16 fixed Tenjiku + Mitsugumi 13×13
shrink; all on chessvariants.com). Key engine facts: all six drop-less AND no check rule (win = capture all
royals, pseudo-legal movegen — big perf win); Elven Chess's Warlock = complete Chu Lion incl. f>m>t/igui
encoding; Wa Shogi = the (slides,leaps,ranged) large-board template; square render proven to 19×19 (Go),
labels ≤2 chars. Suggested seam: a shared large-shogi layer (ShogiLike + Wa tables + direction-scoped Lion
component) proven by Chu, making Dai/Heian-Dai table-transcription builds.

### KNOWN Group C remaining (harder/lower-value long tail): star_star (*Star — BUILDING NOW), pex (BUILDING NOW),
yvy (board+sprout transcription), snodd (yodd-on-snub-square near-clone), side_stitch (exo_hex near-sibling); medusa
DEFERRED. **Group A (large shogi: Chu/Dai/Tenjiku/Dai-Dai/Maka-Dai-Dai/Heian-Dai; verify the "nut-named" jokes) fully
untouched.** DECISION POINT for Erik: continue the C long-tail (pex/yvy/star_star are the most distinct), start
group A (marquee-hard focused builds), or pause. Ops this session: Fable cap → opus relaunch worked well; ~4 more
session-limit agent deaths, all recovered (partials cleaned + relaunched); every game deep-QA'd MERGE with ≤1
trivial fix (only real fix all session: exo_hex invented-winner → honest draw).

---

## Previous handoff (2026-07-01, superseded)

**218 games** on `origin/main` at HEAD `1a2f7b6`.

### What this session (2026-06-30 → 07-01) did — +13 games (#206–218) + 1 UX fix
All browser- **and** anchor-verified, each its own commit, `GAME_STATUS.md`/this file/memory kept current.
- **Traditionals/small:** Hexapawn #206 (Gardner 3×3, minimax anchor), Micro Shogi #207 (4×5 flip-on-capture),
  Whale Shogi #208 (6×6 Kujira), Lasker Morris #209 (interleaved place/move), Cheskers #210 (Golomb chess/checkers),
  Wa Shogi #211 (11×11 animal), Omweso #212 (first 4-row mancala), Nard #213 (no-hitting backgammon).
- **Multi-move chess (Erik-directed):** Monster #214, Progressive #215, Marseillais #216. **KEY REUSABLE PATTERN:**
  multi-move turns = the backgammon pattern (apply_move keeps `to_move` until the sub-move budget is spent) →
  **NO UI change**; each is a self-contained ChessLike subclass with `MState(CState)` adding `moves_left`, reusing
  `_pseudo`/`attacked`/`in_check`, own move-gen (NOT `super().legal_moves`); the other ~40 chess variants untouched.
- **Coverage + Reddit (Erik-directed):** King's Valley #217 (5×5 slide-to-center; closed the LAST gap vs
  **playabstractgames.com** — we now cover all 19 of theirs) + Ponte del Diavolo #218 (10×10 island/bridge,
  triangular scoring, bridges via the TwixT `board.overlay` primitive).
- **UX fix:** GamePicker search was an unranked substring match → exact names buried (Erik hit this with "Tak").
  Added `relevance()` ranking (exact name>prefix>word-prefix>substring>tag>category>desc); searching shows a flat
  best-first list, browse keeps category groups (`web/src/GamePicker.jsx`). Deployed.

### ▶ NEXT TASK (queued, Erik-directed): games from Dr Eric Silverman's blog
`https://drericsilverman.com/2021/02/12/quick-picks-interesting-abstract-games-in-brief/` — 60 titles.
**Already deduped (2026-07-01):** ~18 already exist (Catchup, Grand Chess, Shako, Kensington, Othello[=reversi],
Hex, Game of Y[=`y`], Yodd, Star, Starweb, Havannah, Shatranj, Trike, Tumbleweed, Lines of Action, Poly-Y, TwixT,
Courier Chess). **~42 candidates**, grouped:
- **A. Large shogi (marquee-hard, Chu-tier — focused builds, may want Erik input):** Chu Shogi (12×12), Dai Shogi
  (15×15), Tenjiku Shogi (16×16, jumping generals — brutal), Dai Dai (17×17), Maka Dai Dai (19×19), Heian Dai
  (13×13). ⚠️ VERIFY which "nut-named" ones are real vs the blogger's jokes: Nutty/Cashew/Macademia/Mitsugumi/
  Suzumu Shogi.
- **B. Chess variants (standard-ish render, perft-anchorable — the reliable seam):** Omega Chess (10×10 + 4 corner
  cells + Wizard/Champion — needs a slightly custom board), Opulent Chess, Metamachy (Cazaux 12×10), Grand Shatranj
  (10×10), Caissa Britannia, Elven Chess, Decimaka, Gross Chess, Zanzibar-XL.
- **C. Connection / Y / hex-render family (mostly hex/polygons — primitives exist; some may need render work):**
  Iris, Lotus, Medusa, Rosette, Exo-Hex, Pex, Volo, Tintas, Ayu, YvY, Side Stitch, Permute; Y-family: Odd-Y, 5-Y,
  Snodd, Xodd, Star-Y, Double Star, Superstar.
- Plus the long-flagged marquees **Tamerlane** & **Bao** (Bao not on the blog; still queued).
**Recommendation:** start with B (chess variants — reliable, fast, perft-anchorable), sample C (verify render needs
first — hex boards use the polygons primitive), and treat A as focused one-at-a-time builds needing Erik's eye.

### How the loop works (quick reminder for a fresh session)
Per game: launch a general-purpose build agent (verify rules vs sources + OVERRIDE the brief on conflict; subclass
`agp.chesslike`/`agp.shogilike` for chess/shogi; pure-stdlib `selftest.py` with a perft/known-result anchor; do NOT
commit) → orchestrator QA (validate + selftest + probe the signature mechanic) → **browser-verify** (restart backend
by PORT only; pinchtab: QuickPlay → search the FULL distinct name [gotcha: "Lasker"→Lasca, substrings match desc] →
click `button.game-card-main --mode dom` → START → screenshot) → commit (one game/commit) → regen `GAME_STATUS.md`
(`engine/tools/gen_game_status.py`) → log a row here → push (auto-deploys; verify via RENDER_API_KEY, pin commitId).
Read `[[game-factory-continuation]]` + `[[platform-direction]]` memories + `CLAUDE.md` for full conventions.
DEDUP every candidate first; decline clones. Standard-render chess/shogi = fast-path (anchor + render-probe, batch
browser checks); custom-render games = always browser-verify.

### ⚠️ Needs your decision: _none blocking._ Next task is queued (blog games above); pick a group to start.

---

## Capability work — drops / reserve tray (2026-06-21, with Erik in the loop)

**Shipped the #1-ranked UI investment: an off-board reserve + drop moves**, with
**Crazyhouse** (game #55) as the first consumer. Design approved by Erik up front
(guarded hooks in `ChessLike`; two trays top/bottom).

- **Engine:** a `DROPS` strategy on `agp.chesslike` (`NoDrops` default →
  `CrazyhouseDrops`) adds `CState.hands` + a `promoted`-square set, all no-op and
  absent from serialize/poskey unless enabled → the other ~20 chess variants are
  byte-identical (suite green). Drop move = `"L@c,r"`; captures bank to the
  reserve (promoted piece → pawn); `_insufficient` off when drops enabled.
- **Web:** `Board.jsx` renders two seat-colored reserve trays (seat 1 top / seat 0
  bottom) + click-chip-then-empty-cell to drop; drop targets highlight and the
  pawn back-rank rule is enforced visually. **No server change** (enforced path is
  `move in legal_moves`).
- **Anchor:** differential vs python-chess `CrazyhouseBoard` — perft
  20/400/8902/197281 (start) + 62/4715/197413 (drop-bearing midgame), and a
  400-game synchronized move-set walk (46,427 plies, **0 mismatches**). Committed
  selftest is pure-stdlib with frozen perft + capture/demotion/back-rank checks.
  Verified in-browser (Quick Play hotseat): capture→reserve→drop full lifecycle.
- **Next on this primitive:** Shogi (own `DropRules`: promotion zone + nifu) and
  the Morris family (custom adjacency + mill-removal, not a ChessLike consumer).
  See `GAME_BACKLOG.md` §1.

---

## Autonomous expansion run (2026-06-21/22) — 54 → 72 games + ALL 7 UI capabilities

**Final tally:** 18 games added across the run, **all seven UI capabilities on the
backlog shipped, each with a flagship consumer**, plus a multi-action-turn demo and
the renderer primitives below. All on `main`, suite green throughout, every game
browser-verified; 11 verification sub-agents ran (UI review + 10 rule reviews),
all MERGE.

| Capability | Flagship consumer(s) |
|---|---|
| drops / reserve | Crazyhouse #55, Shogi #56, Mini Shogi #59 |
| stacking (towers) | Lasca #60 |
| territory scoring | Go #61 |
| >2-seat (up to 6) | Rolit #63 (4p), Chinese Checkers #68 (6p) |
| walls / point-and-line | Quoridor #69, TwixT #70 |
| dice / randomness | EinStein würfelt nicht #71 |
| cards | Onitama #72 |

Other games: Nine Men's Morris #57, Bagh-Chal #58, Pentago #62 (place+rotate via
the =CHOICE picker), Alquerque #64, Kalah #65, Y #66, Yote #67. Renderer gained:
reserve trays, stacking glyph, `board.lines` (under-cell grooves), `board.overlay`
(over-cell bridges), `board.tints` (terrain/edges), `board.walls` (groove slots),
6 seat colours, triangular-hex + 6-pointed-star polygon layouts, extent-margin.

**The entire UI-capability roadmap is now complete (all 7 of GAME_BACKLOG.md's
ranked gaps).** Remaining work is purely incremental games on existing primitives:
DVONN/Focus/Tak (stacking), Surakarta (loop-capture), Mu Torere, Tapatan, Twelve
Men's Morris.

---

## (superseded) earlier note — 54 → 63 games + 4 UI capabilities

Erik set the loop to "keep going for hours, spin off sub-agents, maintain a status
artifact." On-disk state, all on `main`, suite green:

- **`GAME_STATUS.md`** (new) — the living catalogue of every game (board,
  verification anchor, selftest/rules/browser status), generated by
  `engine/tools/gen_game_status.py`. **This is the artifact to read for current
  status.** Regenerate after each new game.
- **Shogi (#56)** — new `agp/shogilike.py` core (colour-relative move-gen + drops
  + zone promotion); python-shogi-verified (perft 30/900/25470/719731 + 41k-ply
  walk, 0 mismatches). A walk-found slide bug (`dr` vs `dr*fwd`) was fixed.
- **Nine Men's Morris (#57)** — 24-point mill game; independent rule review = MERGE.
- **Bagh-Chal (#58)** — 5×5 alquerque Tigers & Goats; review = MERGE (capture
  inference fuzzed over 20k boards).
- **Mini Shogi (#59)** — 5×5 shogi on the verified ShogiLike core; published perft
  14/181/2512 (depth-1 hand-checked).
- **Lasca (#60)** — Lasker's draughts-with-towers; **first STACKING game** →
  added the stacking renderer (towers as layered owner bands + height badge);
  review = MERGE (under-tucking + liberation + mandatory-not-maximum capture).
- **Go (#61)** — full Go with **TERRITORY SCORING** (the 3rd big capability and
  the flagship hole): liberty core + two-pass end + **Tromp-Taylor area scoring**
  (algorithmic, so no dead-stone UI) + komi + 9/13/19 sizes; review = MERGE
  (scoring hand-verified, ko/superko confirmed). **All three capabilities Erik
  named — drops, stacking, territory scoring — are now shipped.**
- **Pentago (#62)** — place-then-rotate-a-quadrant; rides the existing `=CHOICE`
  picker (the **multi-action-turn** primitive) + `board.lines` quadrant dividers.
- **Rolit (#63)** — four-player Reversi; the platform's **first >2-player game**,
  which drove the **>2-seat UI** capability: `colors.js` now has 6 seat colours,
  and `QuickPlay.jsx` seats N players (chips + turn cycling) with bot mode playing
  all non-human seats. The MCTS already backed up per-player payoffs, so no engine
  change. Verified in-browser (full P1→P4 round, flips, per-seat scoring); existing
  2-player games unaffected (Amazons' neutral arrow is now green, reads fine).
- **Renderer** — added `board.lines` (cosmetic connecting lines) + `board.tints`
  (terrain colours) + an extent-relative viewBox margin. Drove a **UI-review pass**
  (a sub-agent) on the unusual boards → fixed **Jungle's invisible river** (now
  tinted), drew **Fanorona's alquerque lines**; verified Oware renders correctly.
- **Method:** per game, build → conformance → an independent adversarial
  rule-review sub-agent (or a published/perft anchor) → browser-verify → commit.
  Verifier is always a *different* agent than the implementer.

---

## The gate (option 1, updated 2026-06-21)

Erik delegated merge authority: the orchestrator may auto-merge after a **detailed
independent code review**, without separate approval.

- **AUTO-MERGE to `main`** — `agp validate` green **AND** the rules are confirmed
  faithful by an *independent* check: a published numeric anchor (chess-family
  **perft** / solved result) **OR** a clean adversarial rule-review (a fresh agent
  re-deriving every move + win condition with no faults) **plus the orchestrator's
  own code review**. A published anchor is preferred but no longer required.
- **QUEUE for review** — only when the review surfaces a genuine **open ruleset
  decision** that's Erik's to make, a **new board shape/rendering** needing his
  eyes, or an issue that can't be confidently auto-resolved. Held on a `factory/*`
  branch + listed under *Needs human*.
- **BLOCKED** — needs a missing platform primitive (stacking, hand/drops, Go
  territory scoring, point-and-line edges, >2-seat UI). Deferred; see
  `GAME_BACKLOG.md`.

The loop: discover → implement (isolated, reference an existing package) →
`agp validate` + anchor self-test → **independent** adversarial rule-review →
deterministic gate → auto-merge or queue. Verifier is a *different* agent than the
implementer.

## Legend
`queued` · `building` · `done(auto)` · `review` (queued for Erik) · `blocked`

## Batch 1 — harness proof (2026-06-20)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| King of the Hill | auto | chess perft 20/400/8902 (re-derived) + center-king win | **done(auto) → main** |
| Three-Check | auto | chess perft 20/400/8902 (re-derived) + 3-check win | **done(auto) → main** |
| Tablut (9×9 tafl) | review | conformance + capture/escape positions; no published number | **done → main** (king-assist resolved from Cyningstan) |

Both auto games were independently re-verified (the verifier recomputed perft to
197281 at depth 4, matching standard chess) and re-checked by me before merge. The
factory's per-package `selftest.py` is run by the suite via `test_package_selftests`.

## Batch 2 — chess-variant pack (2026-06-20)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Racing Kings | auto | shakmaty perft 21/421/11264 + 31,920 python-chess differential positions, 0 mismatches | **done(auto) → main** |
| Makruk (Thai chess) | review→auto | independent adversarial review (option 1) | **done → main** |
| Shatranj (medieval) | review→auto | independent adversarial review (option 1) | **done → main** |
| Capablanca (10×8) | review→auto | independent adversarial review (option 1) | **done → main** |

Under the option-1 gate, all three merged after a detailed independent review:
three fresh adversarial code reviewers (separate from the factory's verifiers),
each returning MERGE with no required fixes, plus the orchestrator's own code read
and runtime probes of the risk areas (Makruk 6th-rank promotion, Shatranj Alfil
leap / bare-king, Capablanca castling).

## Batch 3 — draughts + connection (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| International Draughts (10×10) | auto | published WDF perft 9/81/658/4265(/27117/167140), re-derived by verifier + orchestrator | **done(auto) → main** |
| Turkish Draughts (Dama) | review→auto | independent review; apply_move cross-checked over 40k positions + 489k jump-chains, 0 double-jumps | **done → main** |
| Havannah (hexhex) | review→auto | independent review of ring/bridge/fork (outside-flood-fill ring); exhaustive shape tests | **done → main** |

International was perft-locked (gold-standard anchor). Turkish + Havannah merged
after fresh adversarial reviewers + the orchestrator's own read of the hard logic
(Turkish immediate-removal-during-chain; Havannah ring detection). All MERGE.

## Batch 4 — divergent chess variants (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Horde Chess | auto | python-chess HordeBoard: perft 8/128/1274/23310 + 400-game move-gen & 2000-game outcome differential, 0 mismatches | **done(auto) → main** |
| Antichess (Losing Chess) | auto | python-chess AntichessBoard: perft to depth 5 (…/2732672) + 789 terminal positions, 0 mismatches | **done(auto) → main** |
| Courier Chess (12×8) | review→auto | independent review; **caught + fixed** an insufficient-material bug masking K+2Manns mate | **done → main** |

Horde (king-less White) and Antichess (non-royal king, forced capture, stalemate-
as-win) both got python-chess differential verification. Courier merged after the
review-caught insufficient-material fix.

## Batch 5 — atomic + tafl + CGT (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Atomic Chess | auto | python-chess AtomicBoard differential (1500 games, kiwipete perft d4=3,492,097), 0 mismatches | **done(auto) → main** |
| Hnefatafl (Copenhagen 11×11) | review→auto | independent review vs canonical Copenhagen sources + my probes | **done → main** |
| Konane (Hawaiian) | review→auto | independent 3000-position move-gen cross-check + my probes | **done → main** |

(Atomic's committed selftest was rewritten pure-stdlib post-merge — see Quality
signals above.)

## Batch 6 — Janggi + tafl + Frisian (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Janggi (Korean Chess) | review→auto | reviewer hand-derived 31-move opening + full cannon/elephant/palace re-derivation; perft baseline 31/949/29697 | **done → main** |
| Ard Ri (7×7 tafl) | review→auto | independent rule re-derivation (Tablut-family) | **done → main** |
| Frisian Draughts | review→**fix**→auto | review REJECTED a weighted-capture bug; fixed to king=1.5 summed value, re-verified | **done → main** |

## Batch 7 — Go-family (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Atari Go (Capture Go) | review→auto | independent re-derivation; liberty/group-capture + positional superko; my capture/suicide probes | **done → main** |
| NoGo (anti-Go) | review→auto | independent re-derivation; capture & suicide both illegal | **done → main** |
| Tawlbwrdd (11×11 tafl) | — | review found it AST-identical to Hnefatafl | **DISCARDED (clone, not shipped)** |

## Batch 8 — connection + draughts + wide chess (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Gonnect | review→auto | Go capture (reuses atari_go core) + edge connection; reviewer read official rulebook | **done → main** |
| Brazilian Draughts (8×8) | auto | perft 7/49/302/1469 = published 8×8 counts; international-rules engine at N=8 | **done(auto) → main** |
| Wildebeest Chess (11×10) | review→**fix**→auto | review REJECTED a castling bug; replaced with NoCastling (unsourced rule), re-verified | **done → main** |

## Batch 9 — Mancala + Go-family + classic (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Oware (Mancala/Awari) | review→auto | re-derived vs canonical Awari; 2000-game seed-conservation + unreachable-state proof | **done → main** |
| Tanbo (Mark Steere) | review→auto | agent read Steere's official PDF; distinct 'bounded-root' capture + 2026 layout | **done → main** |
| Dao (4×4) | review→auto | re-derived vs US patent + Wikipedia/BGG; maximal-slide + 4 win conditions | **done → main** |

## Batch 10 — distinct traditionals (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Fanorona | review→auto | re-derived vs canonical Wikipedia; approach+withdrawal captures, chains | **done → main** |
| Dou Shou Qi (Jungle) | review→auto | full rank hierarchy, river jumps, traps, dens verified | **done → main** |
| Connect6 | review→auto | 1-then-2 stone mechanic + gap-bridging six verified | **done → main** |

## Batch 11 — incremental traditionals on existing primitives (2026-06-22)
_First batch of the post-roadmap "incremental games" phase — all reuse the
Morris/polygons adjacency primitive; no new capability._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Tapatan (Three Men's Morris) | review→auto | independent re-derivation of the 8-line 3×3 board (centre↔all 8, no corner–corner adjacency); no-capture mill-to-win; 5000-game termination proof | **done → main** |
| Mū Tōrere | review→auto | re-derived vs canonical (Bell) ruleset; the centre-entry-only-when-adjacent-to-enemy rule + loss-on-no-move; novel 8-pointed-star polygon layout, browser-verified | **done → main** |
| Twelve Men's Morris | review→**fix**→auto | reviewer flagged a genuine fork: full-board (12+12 fill all 24 pts, no mill) was scored a LOSS for the mover via the generic no-move rule. I resolved it to the **traditional DRAW** (faithful rule, not an open choice — it's the variant's signature drawishness), documented in rules.md + asserted in selftest, then auto-merged | **done → main** |

## Batch 12 — stacking + loop-capture on existing primitives (2026-06-22)
_All three reuse shipped primitives (piece.stack towers / reserve trays / board.overlay). One generic renderer fix was needed; see note._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Surakarta | review→auto | independent re-derivation; exhaustive proof that NO zero-loop slide can capture + first-piece-only/no-jump; 2-ring loop topology traced. **Renderer fix:** the 8 corner loop arcs (3-point Bézier overlay) were clipped + mis-drawn — generalized `board.overlay`/`board.lines` to N-point paths (2pt line / 3pt quadratic arc / Npt polyline) and grew the viewBox to include decorations. Browser-verified (gold inner + blue outer loops now render) | **done → main** |
| Focus (Domination) | review→auto | re-derived Sackson rules; over-5 bottom-removal split (own→reserve, enemy→captured), move-top-k-exactly-k-cells, reserve drop, last-to-move win; 52-cell octagon (polygons honours `cells`). Browser-verified (octagon + towers + reserve trays) | **done → main** |
| DVONN | review→auto | re-derived vs official rules — build agent CORRECTED my prompt (stacks move all **6** hex directions, jumping allowed, land-on-occupied) and the DVONN-disconnection removal incl. the bridge-break case; canonical 49-field elongated-hex board (9-10-11-10-9). Browser-verified (board geometry + placement phase) | **done → main** |

## Batch 13 — stacking draughts + small traditionals (2026-06-22)
_Certain geometry, well-documented rules; each reuses a shipped primitive (stacking / board.lines / custodial capture)._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Bashni | review→auto | re-derived vs mindsports.nl + draughts.github.io; the top-to-bottom prisoner rule, mandatory+chained+backward capture, Russian flying king, re-jump-same-square legality all confirmed; 2000-game piece-conservation (24 constant). Reuses Lasca towers. Browser-verified | **done → main** |
| Tsoro Yematatu | review→auto | re-derived canonical 7-point figure (5 lines of three); place-3-then-slide/jump (non-capturing), 3-in-a-row win, movement-phase-only scoring gate (option `placement_win`). Browser-verified (figure + placement) | **done → main** |
| Hasami Shogi | review→auto | Dai Hasami Shogi ruleset; rook movement + active custodial/corner capture (reuses brandub flanking) + dual win (decimation OR off-home-row 5-in-a-row, ortho/diag), both verified reachable in 400-game fuzz. Browser-verified | **done → main** |

## Batch 14 — the stacking flagship (2026-06-22)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Tak | review→**fix**→auto | the road-building flagship: NxN (size option), flats/walls/capstones, opening double-move, carry-limit spreads, road-BFS win + flat-count win. **Review REJECTED a real bug** — the flat-count win fired when the FLAT reserve emptied, but official Tak ends only when the ENTIRE reserve (flats AND capstone) is gone; fixed to require both + added a 5×5 regression test (the package's own rules.md already stated the correct rule). **Two generic renderer touches:** the `=choice` picker now takes per-game `choiceNames`/`choiceTitle` from the RenderSpec (Tak's F/S/C → Flat/Wall/Capstone, which collided with chess C=Cardinal). Browser-verified end-to-end (opening swap, type picker, wall/capstone glyphs, reserves, bot capstone) | **done → main** |

## Batch 15 — GIPF stacking + phalanx + jump-race (2026-06-22)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Epaminondas | review→auto | Abbott's phalanx war game (14×12); maximal-line phalanx slides 1..L, strictly-longer head-on capture removes the whole on-axis enemy run, deferred one-reply strict-majority 'crossing' win — all re-derived clean by the reviewer. Browser-verified | **done → main** |
| TZAAR | review→**fix**→auto | GIPF #4 stacking on a 61-cell hexhex (centre empty), 6/9/15 Tzaar/Tzarra/Tott, two-action turn, type-survival loss. **Review REJECTED a game-defining bug** that traced to MY spec — I wrongly said "no long slide"; official gipf.com rules have pieces SLIDE in a straight line over vacant cells to the first occupied cell (both capture & stacking, no jumping). A focused fix-agent rewrote move-gen to sliding (`_slide_targets`/`_slide_path_clear`) + added long-range/blocked/long-stack selftests; I re-verified + fixed the manifest desc. Browser-verified (hexhex render + slide capture) | **done → main** |
| Halma | review→**fix**(fork)→auto | the jump-race ancestor of Chinese Checkers (8×8/16×16 option). Review QUEUED the classic 'spoiling' fork (a squatter could deny the win → draw). I resolved it to the **standard 'enemy pieces don't block your win'** rule (target camp full + ≥1 of yours) + added the canonical 'can't leave the opposing camp once entered' + dropped a non-canonical anti-stall band-aid; documented as a deliberate choice. Browser-verified (8×8 camps + step) | **done → main** |

## Batch 16 — clean square-grid abstracts (2026-06-22)
_All three auto, certain geometry, no renderer change._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Ataxx | review→auto | 7×7 expansion/infection; grow(clone, dist-1) vs jump(relocate, dist-2), 8-way infect-on-land, most-pieces win; reviewer confirmed the end-and-count vs award-empties fork never diverges in 300 games. Browser-verified | **done → main** |
| Teeko | review→auto | Scarne 5×5; drop-4-then-slide, win = line-of-4 OR 2×2 square (44 win shapes, all re-derived). Browser-verified | **done → main** |
| Squava | review→auto | 5×5 misère hybrid (placement only): four-in-a-row WINS, three-in-a-row LOSES, four-takes-precedence, full-board draw. Browser-verified | **done → main** |

## Batch 17 — custodial + knight-race + linear draughts (2026-06-22)
_All three auto, certain geometry, no renderer change._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Mak-yek | review→auto | Thai/Cambodian (Apit-sodok) 8×8; rook move + BOTH active capture modes — custodial flanking AND intervention (land between two enemies takes both); annihilation win; first/third-rank setup. Browser-verified | **done → main** |
| Jeson Mor | review→auto | Mongolian 9×9 all-knights; (1,2) leaper, capture-by-landing, win by occupy-then-VACATE the centre (4,4) (tinted); implemented directly (not ChessLike — no king/check). Browser-verified (knights + center tint + move) | **done → main** |
| Dameo | review→auto | Freeling 8×8 all-squares draughts; the build agent cross-checked mindsports.nl and correctly implemented the faithful LINEAR move = a connected file shifts exactly ONE square (I'd mis-specified "any distance"), forward man-steps, mandatory+maximal+chained orthogonal capture w/ end-of-move removal, flying kings; canonical triangular 18-man wedge setup. Browser-verified (wedge + linear move) | **done → main** |

## Batch 18 — Conway jump-game + pro-Gomoku + hex escort (2026-06-22)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Phutball (Philosopher's Football) | review→auto | Conway's jump-to-goal: neutral shared men + one ball, place-a-man-OR-ball-jump-chain, jumps remove the leapt men, win by the ball reaching/crossing your goal line. Build agent modeled the unbounded chain as repeated single hops + a "stop" action (Oust-style multi-action turn) to avoid combinatorial blowup — rule-equivalent. 15×19 board, goal tints, ball glyph 'O'. Browser-verified | **done → main** |
| Renju | review→**fix**→auto | pro-Gomoku 15×15 with Black handicap (exact-five only for Black incl. no-overline, double-three/double-four/overline forbidden losses, White unrestricted). **Review REJECTED a game-breaking bug** — a STRAIGHT FOUR was miscounted as an open three, so Black's key 'four-three' winning tesuji was wrongly ruled a forbidden double-three loss; a fix-agent corrected `is_open_three_in_dir` (exclude run≥4 + require the dev point to extend THIS three) + added a four-three regression test. Deeply-nested RIF open-three recursion remains a documented approximation. Browser-verified | **done → main** |
| Agon (Queen's Guard) | review→auto | Victorian hex escort on a hex-of-hexes (side 6, 91 cells); inward/sideways-only movement, custodial send-to-outer-ring capture, win = Queen on the throne ringed by all 6 own guards; re-derived vs Wikipedia. New board shape — browser-verified (throne tint + Q glyphs + inward move) | **done → main** |

## Batch 19 — mancala + two race games (2026-06-22)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Toguz Kumalak | review→**fix**→auto | Kazakh 2×9 sowing mancala; leave-one-behind, even-count capture, the full tuzdik (sacred-hole) rule + its 3 restrictions, >81 win. **Review caught an end-game bug** — remaining board balls weren't swept to each side's kazan at game end (could flip the winner); fix-agent added the own-side sweep + regression test. Browser-verified (capture fired: 10–10). Reuses the Kalah/Oware pit render | **done → main** |
| Gygès | review→auto | Leroy's ownerless 6×6 height-race; pieces (height 1/2/3, no owner) move exactly their height in steps, bounce/replace on landing, win by reaching your goal cell; re-derived vs the official Leroy PDF. Reuses Lasca height glyph. Browser-verified | **done → main** |
| Conspirateurs | review→**fix**→auto | French Halma-style step-and-jump race, 17×17. **My spec was WRONG** (I said queen-move/no-adjacent) — the build agent verified 4 sources and built the REAL game (step + jump, no capture, shelter all your men in the perimeter sanctuaries). Review then caught MEN=21 (should be 20 in play; 21 cones = 1 spare) — fixed to 20. Sanctuary map is a documented 40-cell reconstruction (exact published coords unrecoverable). Browser-verified (0/20 + sanctuary tints) | **done → main** |

## Batch 20 — render-primitive investments (rings/markers → YINSH) (2026-06-22)
_Erik asked to build the 3 deferred render primitives in order: **rings/markers → YINSH** (this), then nesting → Gobblet, then shrinking board → ZÈRTZ._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| **(primitive) ring/marker glyphs** | — | generic `piece.shape` = `ring` (hollow, +optional `inner` marker + `label`) / `marker` (small disc) in the RenderSpec; documented in SPEC.md; all 97 prior games render byte-identical | **done → main** |
| YINSH | review→auto | GIPF #5; 85-point hex lattice (cols 4-7-8-9-10-9-10-9-8-7-4, 3 line families) — geometry verified vs the sharkdp/yinsh reference + gipf.com; 5 rings/side, place-marker-then-slide-ring with jump-and-flip, ring-blocking, row-of-5 removes 5 markers + 1 ring, win = remove 3 rings. First consumer of the ring/marker primitive. Browser-verified (85-pt board + hollow ring glyph render). NOTE: MCTS bot is slow on the 85-pt board (generic large-board perf, not a bug) | **done → main** |

## Batch 21 — render-primitive 2 (nesting → Gobblet) (2026-06-22)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| **(primitive) piece.size nesting** | — | generic `piece.size` (disc scaled by size; emit only the top cup) + DROP_RE widened to accept a digit reserve key (`4@c,r`) so the reserve-chip drop flow works for sizes; documented in SPEC.md; backward-compatible (Crazyhouse letters still match) | **done → main** |
| Gobblet | review→auto | Denoual/Blue Orange; 4×4, 3 off-board nested stacks of cups (sizes 1-4), strictly-larger gobble, off-board-gobble-only-on-a-3-line restriction, uncovering reveals the cup beneath, win = 4 same-colour tops in a line (incl. uncover-loss); + a 3×3 'Gobblet Gobblers' `size` option. Verified vs the Blue Orange rulebook. First consumer of the nesting primitive. Browser-verified (sized cups render + reserve-tray drop + nested stacks update) | **done → main** |

## Batch 22 — render-primitive 3 (shrinking board → ZÈRTZ) · 100 GAMES (2026-06-22)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| **(primitive) shrinking board + marble fill** | — | `board.extent` pins the viewBox so a board can shed cells without rescaling; `piece.fill`/`piece.stroke` give a piece an explicit (non-seat) colour. Documented in SPEC.md; backward-compatible | **done → main** |
| ZÈRTZ | review→**fix**→auto | GIPF #2; 37-ring hexagon that SHRINKS (rendered as `polygons` so removed rings vanish + `board.extent` keeps it stable — the hex renderer ignores a cell list), shared 6W/8G/10B neutral marble pool (`piece.fill`), place-marble-then-remove-free-ring, mandatory chained jump-capture into your reserve, isolation capture, win = 3-of-each / 4W / 5G / 6B. **Review caught a real bug** — isolation only fired on ring-removal, not when a placement fills an isolated group's last vacancy with no free ring removable; fix-agent added the placement-path isolation (with a `prev` guard so pre-existing islands aren't re-swept) + regression test. **Also a render-only UX fix:** exposed the shared pool as the mover's armable reserve tray (placement was unplayable — the pool had no clickable source), captured marbles → caption. Browser-verified (board shrinks with gaps, 3-colour marbles, pool placement + ring removal) | **done → main** |

_All three deferred render primitives (rings/markers, nesting, shrinking-board) now shipped — 100 games._

## Batch 23 — distinct drop-ins on existing primitives (2026-06-23) · 103 games
_Built under a sustained Anthropic API 529-overload — handled by hand (see note)._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Quixo | hand-built→auto | Gigamic 5×5 take-a-border-cube-stamp-and-slide; win = five of your symbol, opponent-completion hands them the win. I WROTE this package by hand (the build agent kept 529-ing); slide/win baked in selftest. Browser-verified (slide picker via `=CHOICE`, slide renders). Fixed U/D picker labels for the renderer's y-flip | **done → main** |
| Kamisado | agent-build→**self-verified**→auto | Burley 8×8 colour-chain race; Latin-square colour board (`board.tints`) + 8 colour towers (`piece.fill`), forward-only slide, colour dictates the opponent's next tower, official deadlock rule, reach-far-row win. Verify agent died on 529 → I did the independent adversarial review myself. Browser-verified (colour board + colour-chain). **Renderer fix:** a piece with both `fill`+`label` (a tower on its own-colour cell) was invisible (label-only in the fill colour) → now drawn as a disc + contrasting-outline label | **done → main** |
| Battle Sheep | agent-build→**self-verified**→auto | Blue Orange split-and-slide on a fixed 32-hex board; split a stack (leave ≥1), slide as far as possible, most-hexes win (tie-break largest herd). Verify agent died on 529 → self-reviewed. Reuses `piece.stack`. Browser-verified (hex stacks + split via count picker) | **done → main** |

_Note: a multi-hour Anthropic API 529 overload killed build/verify subagents repeatedly. I backed off + resumed (cached builds), wrote Quixo by hand, and did the independent rule-review for Kamisado/Battle Sheep myself (a valid second reviewer) — all 3 also browser-verified._

## Batch 24 — the GIPF namesakes (2026-06-23) · 105 games
_Completes the realistically-addable GIPF project (DVONN, TZAAR, YINSH, ZÈRTZ already in). TAMSK is real-time sand-timers → not implementable in a turn-based engine (skipped). "Potentials" (the cross-game meta-layer) deliberately NOT done — it couples games and breaks the independent-module design; each GIPF game ships standalone._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| GIPF | review→auto | the namesake (basic game): radius-3 hex of 37 spots + 24 entry dots, introduce-from-reserve-and-shove inward, 4-in-a-line removal (own pieces → reserve, opponent's captured out), lose on empty reserve. Geometry + rules verified vs gipf.com/Rio Grande. Reserve tray + hex board.lines. Browser-verified (board + shove). GIPF-pieces/doubles variant documented out-of-scope | **done → main** |
| PÜNCT | review→auto | GIPF #6 connection+stacking: 211-field side-9 hexagon, 18 triomino pieces (straight/angular/triangular) placed flat or stacked (bridging/support rules), connect a pair of opposite edges (Hex-style BFS over top colour). Rules verified vs gipf.com/UltraBoardGames. Rendered PER-FIELD (a 3-field piece = 3 same-colour discs + height label) — no multi-cell-piece primitive. Browser-verified (211-hex board + triomino placement). **Documented base-game limitations:** placement is offered as an action-button LIST (the P/A/B move notation isn't cell-clickable) — a future click-to-place-triomino + shape-outline UI would improve it; rotate-in-place omitted (PÜNCT must slide ≥1); shapes tracked as a count not a 6/6/6 split; standard PÜNCT-marker/central-control out of scope | **done → main** |

## Batch 25 — stacking-draughts + 2 modern abstracts (2026-06-23) · 108 games
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Emergo | review→auto | Freeling stacking draughts on the 41 dark squares of 9×9; off-board ENTRY phase (drop men, then all-remaining-as-one-column), no kings, omnidirectional single-step, mandatory+maximum chained capture with the jumped TOP man tucked UNDER the mover (Lasca model), capture-all win. rules.md documents how it differs from Lasca/Bashni (entry phase, kingless, max-capture, capture-all). Browser-verified (entry drop). | **done → main** |
| Trike | review→auto | Erickson 2020, side-11 triangular hex board, ONE shared neutral pawn; move the pawn in a straight line over empty cells + drop your stone on the landing; ends when the pawn is trapped; winner = majority of stones on the pawn's cell + its neighbours (pie/swap supported). Verified vs the Kanare/Erickson rulebook. Reuses triangular polygons. Browser-verified | **done → main** |
| Tumbleweed | review→**fix**→auto | Zapawa modern hex influence game (side-8 hexhex); place a stack of height = your line-of-sight count, strictly greater than the target. **Review caught a scoring bug** — it counted only OCCUPIED hexes, but Tumbleweed scores 'owned + controlled' (every empty cell goes to the player with strictly-greater LOS) — wrong winner in ~every game; fix-agent rewrote `_control_counts` to the owned+controlled territory score + a winner-flip regression test. Browser-verified (territory score updates live: 27-27 → 42-23 after a placement). | **done → main** |

## Batch 26 — modern hex abstracts (2026-06-23) · 111 games
_All three on a side-5 hex-of-hexes, reusing the hex renderer + line/Go-liberty/group machinery; all auto._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Yavalath | review→auto | Cameron Browne / LUDI 2007 — the hex analogue of Squava: place stones, 4-in-a-row WINS, exactly-3 LOSES, four-takes-precedence; full board = draw. Optional pie/swap. Browser-verified | **done → main** |
| Pentalath | review→auto | Browne (Ndengrod): 5-in-a-row on a hexhex WITH Go-style group capture (zero-liberty enemy groups removed, no suicide, edge gives no liberty — verified vs cambolbro.com); reuses the Go liberty core. Browser-verified | **done → main** |
| Catchup | review→auto | Nick Bentley: place 1 (first move) then 2, or 3 when catching up (opponent's last turn grew/tied the largest group AND is ≥ yours); fill the board, score = largest connected group (tie-break next-largest…). Browser-verified | **done → main** |

## Batch 27 — custodial + connection + dice (2026-06-23) · 114 games
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Seega | review→auto | Egyptian custodial-capture; 5×5 (5/7/9 option), 2-stones-per-turn placement w/ empty centre, then orthogonal single-step movement, active custodial capture, safe centre, reduce-opponent-below-2 / blockade win. Three source-ambiguities (first mover, single-move, blockade=loss) flagged in rules.md. Browser-verified (placement + marked centre) | **done → main** |
| Slither | review→**doc-fix**→auto | Clark 2010 connection, 8×8 (size option). **Build agent caught that my brief INVERTED the rules** and built the REAL published game (no-bare-diagonal restriction + ORTHOGONAL connection win + optional king-step slide then place). Review QUEUED on an undocumented termination deviation (real Slither passes on no-move + can't draw; we use no-move=loss + ply-cap-draw to guarantee termination) — I documented it in rules.md as a flagged platform termination choice → auto. Browser-verified | **done → main** |
| Cephalopod | review→**fix**→auto | Steere dice-capture majority, 5×5; place a die, must-capture an adjacent set summing ≤6 (die shows the sum) else a "1", board fills, dice majority wins. **Review caught a termination bug** — the ply cap (4·cells) fired BEFORE the board filled (a capture frees cells, so filling needs ~165 plies on 5×5), scoring a partial board in ~100% of games; fix-agent set is_terminal=board-full + a safe high backstop + a full-game regression. Browser-verified (dice pips render, games now fill: avg 136 moves) | **done → main** |

## Batch 28 — CGT classics + a hunt (2026-06-23) · 117 games
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Domineering | review→auto | Berlekamp-Conway-Guy domino game; 8×8 (size option), Vertical vs Horizontal dominoes, last-to-place wins. Anchored by small-board CGT outcomes (full-search-verified: 1×1/2×1 mover loses, 2×2/3×3/4×4 first-player wins; both reviewer + build independently minimaxed). Browser-verified (V/H dominoes render distinctly) | **done → main** |
| Col | review→auto | Vout's map-colouring game; 5×5 (size option), place your colour not orthogonally adjacent to your OWN colour, last-to-move wins. Reviewer cross-checked legal-move gen over 3000 self-play games. Browser-verified | **done → main** |
| Hare and Hounds | review→**fix**→auto | Soldier's Game on the 11-point board (3×3 + L/R apexes, central-X diagonals); 3 hounds (no-retreat) vs 1 hare; hounds trap-win, hare escape/stall win. **Review caught the stalling rule was DEAD CODE** (the counter reset on every hare move, so it could never reach the threshold in alternating play); fix-agent made it count consecutive non-advancing HOUND moves not reset by the hare + a real alternating-play regression. Browser-verified (no-retreat hound move) | **done → main** |

## Batch 29 — CGT pair + a mancala (2026-06-23) · 120 games
_All auto._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Snort | review→auto | Norton's CGT game, the exact dual of Col (place not-adjacent-to-OPPONENT's-colour, last-to-move wins); differentially checked vs the col package. Browser-verified | **done → main** |
| Cram | review→auto | impartial domino game (both orientations, either player), last-to-place wins; build agent corrected my wrong parity-anchor (only both-even→2nd-player holds; 3×3 is a 2nd-player win) and baked full-search small-board outcomes (both build + reviewer minimaxed). Browser-verified | **done → main** |
| Congkak | review→auto | Malay mancala (2×7 + 2 stores, 98 seeds); sow incl. own store/skip opponent's, relay-on-occupied continuation, extra-turn-on-store, own-empty-hole capture; distinct from Kalah/Oware/Toguz (relay + end condition). Browser-verified (sow + store + extra turn) | **done → main** |

## Batch 30 — African capture + connection + attribute-matching (2026-06-23) · 123 games
_All auto._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Dara | review→auto | West African (Derrah) 2-phase: place 12 each (no scoring threes), then orthogonal slide; form EXACTLY-3 (4+ forbidden) to remove an enemy; anti-shuffle (no immediate re-form); win = opponent below 3. 6×5 default + 6×6/7×6 options (board-size source-ambiguity flagged). Reuses morris place+line+capture. Browser-verified | **done → main** |
| Bridg-It | review→auto | Gale / Shannon switching game; two interleaved 5×6/6×5 dot lattices, draw a unit edge between your dots, no crossing the opponent's edge, connect your two sides (BFS); no draws (verified 2000+ games). Edges rendered via `board.overlay`, dots via `piece.fill`. Browser-verified (edge segments draw correctly) | **done → main** |
| Quarto | review→auto | Gigamic attribute game; 16 pieces × 4 binary attributes (code e.g. SDQF), the signature place-the-piece-your-opponent-gave-you-then-give-one turn (first move give-only); win = a line of 4 sharing any attribute. Win-detection exhaustively checked vs brute-force oracle (0/1820 mismatch). Neutral pieces shown by code label + in-hand piece in reserve tray. Browser-verified | **done → main** |

## Batch 31 — unusual-board traditionals (2026-06-23) · 126 games
_All auto._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Kaooa | review→auto | Indian "vultures & crows" hunt on a 10-point PENTAGRAM ({5/2} star — adjacency derived geometrically); 1 vulture vs 7 crows, crows place then slide, vulture steps/jumps (draughts-style, active during placement), vulture wins at 4 captures / crows win by trapping. Browser-verified (star board + crow placement) | **done → main** |
| Achi | review→auto | Ghanaian 3×3 alignment with 8 lines; FOUR pieces each (vs Tapatan's 3), place all 8 then slide to the single empty point, three-in-a-row wins. Reuses morris place+line. Browser-verified | **done → main** |
| Pah Tum | review→auto | ancient grid run-scoring; 7×7 (9×9 option) with a fixed symmetric set of BLOCKED cells, place until full, score escalating runs of ≥3 (3→3,4→10,5→25,6→56,7→88), most points wins. Blocked cells via `board.tints`, running score in caption. Browser-verified | **done → main** |

## Batch 32 — CGT + medieval + Kenyan alignment (2026-06-23) · 129 games
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Clobber | review→auto | Albert/Grossman/Nowakowski CGT game; checkerboard-filled grid (5×6 default), move onto an orthogonally-adjacent ENEMY (clobber it), last-to-move wins. Small-board outcomes independently minimaxed (1×2/1×3/2×2/3×3 P1-win, 2×3 P2-win). Browser-verified (`0,0x0,1`) | **done → main** |
| Camelot | review→**fix**→auto | Parker Bros medieval on the 160-square cross board + 2 castles; 4 knights+10 men/side, PLAIN/CANTER/JUMP + Knight's Charge, win by 2-men-into-enemy-castle or annihilation. Build agent fixed my brief (jumping is COMPULSORY per WCF, not optional). **Review caught jump-continuation not enforced** (premature-stop jumps offered as legal) → fixed to emit only continuation-maximal chains (branching preserved) + regression. Browser-verified (cross board + castles render, `C6-C5`) | **done → main** |
| Shisima | review→auto | Kenyan octagon (8 rim + centre, rim ring + 4 diameters); 3 pieces each, slide to adjacent empty point, three-in-a-row THROUGH THE CENTRE wins. Reuses tapatan slide+line on the octagon graph. Browser-verified (octagon board, `point 2->point 3`) | **done → main** |

## Batch 33 — Korean/Asian traditionals (2026-06-23) · 132 games
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Four Field Kono | review→**fix**→auto | Korean 4×4 (full board start); capture by jumping over your OWN piece onto an enemy beyond. **Review caught my spec was over-restrictive** (capture-only degenerated to ~6 moves) → fix-agent added the standard non-capturing orthogonal slide-to-empty; now avg 126.9 moves, win = no jump AND no slide. Browser-verified (`a1xa3`) | **done → main** |
| Five Field Kono | review→auto | Korean 5×5 race; 7 pieces each (back row + 2 outer second-row), move one step DIAGONALLY to empty, first to occupy the enemy's home set wins. Browser-verified (`0,0→1,1`) | **done → main** |
| Pong Hau K'i | review→auto | Chinese/Korean 5-point blocking game; canonical 5-node/7-edge graph (centre↔4 corners, bottom edge, NO top edge), 2 pieces each, slide to the single empty point, no-move loss; perfect-play DRAW value confirmed. Board via points+`board.lines`. Browser-verified (`tl->c`) | **done → main** |

## Batch 34 — fighting-serpents + Othello-Go + circular (2026-06-23) · 135 games
_Two render-format bugs caught only in-browser (validate/selftest can't see the JS renderer) → SPEC.md now documents the exact `polygons` cells format._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Awithlaknannai Mosona | review→auto→**render-fix** | Zuni "fighting serpents" — 25-point elongated serpent lattice, 12v12, slide or mandatory chained jump-capture (Alquerque-style), capture-all win. Auto on logic; **browser-verify caught the render crash** (cells used key `polygon` not `points`) + a cosmetic describe_move mislabel — both fixed. Browser-verified (serpent board, `7,2-8,1` step / `9,0x7,2` capture) | **done → main** |
| Sygo | review→auto | Freeling's Othello/Go hybrid — build agent corrected my premise (it's GO with "othelloanian capture": a group losing its last liberty FLIPS to the captor's colour, not removed); empty board, no-suicide, territory majority. Single-stone-per-turn simplification (vs the grow-all turn) flagged. Browser-verified (`W:E15`) | **done → main** |
| Pretwa | review→**fix**→auto→**render-fix** | Indian concentric-circle board (3 rings × 6 spokes + centre = 19 pts), 9v9, step/chained-jump-capture. **Review caught win/draw logic** (win at opp≤3 not ≤2; no-move resolves by piece-majority not auto-loss) → fixed. **Browser-verify caught the render crash** (cells emitted as a dict not a list) → fixed. Browser-verified (concentric board, `1,0-0,0`) | **done → main** |

## Focused build — Gess (2026-06-23) · 136 games
_First post-roadmap "distinct focused build" (Camelot-style: one build agent + one independent rule-verify agent + browser-verify) — Erik's pick over continued incremental mining. No new render primitive._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Gess | build→independent-verify(**MERGE**)→browser→doc-fix | The Archimedeans (Cambridge, 1994) Go+chess hybrid: 3×3 "footprint" pieces of your own stones on the 18×18 inside a 20×20 grid; outer cells set move directions (corner=diagonal/edge=orthogonal), center sets range (filled=unlimited/empty=max-3); rigid slide stops at the first stone & captures the whole destination 3×3 (self-capture incl.); border = kill-zone; win = make opponent ringless (ring = 8 stones around an empty center; **multi-ring** rule, mutual-ringless→mover loses). `square` 20×20 (no new primitive), border tinted; move = center→center `cx,cy>dx,dy` into the two-click UI (empty ring-center is a clickable source). Independent verifier (different agent) confirmed every contested rule vs Wikipedia / red-bean SGF spec / Archimedeans (incl. center-must-stay-inner, resolving the jpneto ambiguity for us) + pure apply_move + serialize round-trip; **verdict MERGE**, only a cosmetic "180°"→vertical-mirror doc nit (fixed). Browser-verified end-to-end (board renders, empty ring-center selects, footprint move applies, ring caption `B 1 / W 1`, move logged `l3-l5`). Anchor: pure-stdlib baked-rule selftest (no perft exists for Gess). House-rule draw caps (60-ply no-capture / 400-ply) added for termination, flagged non-original in rules.md | **done → main** |

## Deeper Gess testing + Ataxx hardening + Hexxagon (2026-06-23) · 137 games
_Erik asked for deeper Gess gameplay testing (he hasn't played, so can't eyeball rule bugs) and to add Ataxx (already shipped as #86) + Hexxagon. The deeper testing CAUGHT A REAL BUG._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Gess (bug fix) | gameplay-research→probe→**fix**→independent-re-verify(**CLEAN**) | A research agent pulled the original Archimedeans article's two worked example moves + the chess-piece opening move-sets; probing them found a **slide-through bug** — move-gen exempted the carried stones' PROJECTED cells from the collision check, so a leading carried stone could mask a blocker and the piece slid THROUGH it (illegal jump-over moves; opening inflated 735→ true **416**). Fix: exempt only the carried stones' SOURCE cells (`lifted`). A fresh independent agent re-verified **CLEAN** (no slide-through in any of 8 dirs for enemy/own blockers, single+multi-stone; path-walker confirmed no move passes its footprint over a stone). Selftest hardened: occupied-center masking regression + authoritative-opening chess-piece move-set anchors (rook=orth / bishop=diag / queen+king=all-8 / empty-center range-3 cap / pawn-pusher) + bishop-unlimited. **The first MERGE review missed it by sidestepping the masking case** — lesson: collision tests must use an OCCUPIED-center (unlimited-range) piece so the empty-center cap can't hide a slide-through | **done → main** |
| Ataxx (hardening) | verify-vs-canonical→**add auto-fill** | Existing #86 confirmed faithful to Wikipedia-canonical Ataxx (7×7, opposite-corner setup, grow=dist1/jump=dist2 Chebyshev, 8-nbr infection, pass-and-stop). Added the **arcade/video-game auto-fill-on-elimination** (a move wiping the opponent fills the board for the survivor) — outcome-identical on the holeless 7×7 but instant, and required for Hexxagon's hole board. Guarded on "opponent had pieces before" so synthetic one-colour test positions don't trip it | **done → main** |
| Hexxagon | build→independent-probe-verify→browser | Hex Ataxx: side-5 hexhex (61 cells, axial q,r) − 3 central holes (3-fold-symmetric default (1,0)/(-1,1)/(0,-1); option holes=standard\|none) = 58 playable; 2 players × 3 pieces on alternating corners (each opposite an enemy); grow=hex-dist-1 (6 nbrs)/jump=hex-dist-2 (12-ring), 6-nbr infection, holes never targetable, auto-fill-on-elimination, most-pieces win (tie possible, 58 even). Reuses Ataxx logic + Havannah hex render (`type hex`/`shape hexagon`/`size 5`) + Pah-Tum-style tints for holes. Orchestrator did the independent probe-review (28 checks: geometry, distances, corners, mechanics, holes, auto-fill all pass). **Browser-verified** (hexhex + dark holes render — the untested hex+tints combo works — grow move applies, count 3→4, `R:grow 3,0`). Pure-stdlib selftest | **done → main** |

## Santorini (2026-06-23) · 138 games — NEW render primitive
_Erik's overnight queue item #1. Needed a new generic render primitive first (per-cell build height = two-things-per-cell)._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| **(primitive) board.levels height** | — | generic `board.levels = {cellId: 1..4}` in Board.jsx — per-cell build height drawn as stacked wedding-cake tiers (1-3) + a blue dome cap at 4 + a height badge, *under* the worker piece (two-things-per-cell). Documented in SPEC.md; opt-in, all 137 prior games byte-identical | **done → main** |
| Santorini | build→independent-verify(**MERGE**)→browser | Roxley base game (no god powers). 5×5, 2 workers/side, placement [0,0,1,1], turn = MOVE (≤1 up / any down, not onto worker/dome) THEN BUILD (+1 level, L3→dome) with the same worker; win = MOVE up onto a level-3 building (2-cell climb, no build) or opponent stuck. Move = `wfrom>wto>build` 3-cell path (winning climbs are 2-cell). First consumer of `board.levels`. Independent verify MERGE (placement, ≤1-up, mandatory-build, climb-only-by-moving, stuck-loss, 300 random games terminate). **Browser-verified** end-to-end: placement, the 3-click move→build flow, and all four height visuals (tier-1 badge → 3 nested tiers → dome). New "Build & climb" category. Pure-stdlib selftest | **done → main** |

## Hexxagon 3-player (2026-06-23) · 139 games
_Erik's overnight queue item #2._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Hexxagon (3-player) | build→independent-probe-verify→browser | Separate package `hexxagon3` (num_players fixed=3). Same side-5 hexhex − 3 holes; 6 corners owned P0,P1,P2,P0,P1,P2 (each player 2 opposite corners, 2-2-2 start). Grow/jump/holes identical; infection flips ANY adjacent opponent (either other colour); turn cycles 0→1→2 skipping eliminated/stuck; last survivor auto-fills+wins; returns = 3-vector matched to Rolit (sole leader +1, others −1, lead-tie=0). Reuses hexxagon geometry + Rolit multi-seat returns/cycling. Probe-verified (corner alternation, 3-way infection, skip-eliminated, last-survivor [1,−1,−1]). **Browser-verified** (3 distinct seat colours Red/Blue/Green, alternating corners, grow → turn advances Red→Blue, 3-2-2). Pure-stdlib selftest | **done → main** |

## Batch 35 — GAME_BACKLOG mining, famous Tier-0 (2026-06-24) · 141 games
_Erik's overnight queue item #4: work through GAME_BACKLOG.md with the same gate. Targeting famous/distinct unbuilt Tier-0 games._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Abalone | build→independent-verify(**MERGE**)→browser | The 1987 marble-pusher. Side-5 hexhex (61 cells), 14 marbles/side STANDARD start (5+6+3 wedge, point-symmetric — not Belgian Daisy). In-line 1/2/3 group slides + SUMITO push (2v1/3v1/3v2, empty/off-board behind → edge ejection) + 2/3 broadside; win = eject 6. ANCHOR: **opening = 44 moves** (published branching factor). Independent verify MERGE (sumito + edge-eject + illegal-pushes-absent + group-integrity + broadside + win-at-6 all probed). Browser-verified (standard position on the hexhex, single-marble move). KNOWN UX: 2/3-marble GROUP moves have a clunky multi-cell click path (documented, like PÜNCT/Tsoro). Reuses Havannah hex render; no new primitive | **done → main** |
| Chess960 (Fischer Random) | build→probe-verify→browser | Randomized back rank (Scharnagl id→rank, stored in C9State.homes, has_randomness) with bishops-opposite / king-between-rooks / mirrored; new Chess960Castling (by king/rook FINAL squares, KING-CAPTURES-OWN-ROOK input). ANCHOR: std chess = #518 → perft 20/400/8902/197281 (move-gen unchanged); build agent's differential test = same reachable positions as `chess` over 60×45 incl. castling. Probe-verified 200-seed constraints + castling on non-standard ranks. Browser-verified (randomized board renders + plays; castling headless-verified). On agp.chesslike | **done → main** |
| Martian Chess | build→probe-verify→browser | Looney Pyramids zone-ownership chess. 4×8 board, canal splits two 4×4 zones; Pawn(diag-1)/Drone(ortho-1/2)/Queen(any-line); ownership = zone a piece is currently in (a piece crossing the canal becomes the opponent's); capture scores Q3/D2/P1 to mover; field-merge + no-take-back + tie-break; zone-empty end, most-points win. Probe-verified (zone-ownership, cross-canal scoring, zone-empty end; opening=5 hand-checked). Browser-verified (4×8 + 2 tinted zones + P/D/Q labels; drone crosses canal red→blue). Pure-stdlib selftest | **done → main** |
| Knightmate | build→**brief-corrected**→probe→browser | Bruce Zimov's royal-knight chess on agp.chesslike. King→Royal Knight (knight moves, IS royal); knights→Commoners (king moves, non-royal/capturable); back rank R·C·B·Q·K·B·C·R. Royalty wired by letter (K=royal knight, C=commoner). **Build agent corrected my brief** (Knightmate DOES castle — royal knight + rook; added KnightmateCastling disambiguating same-rank castle from the knight's 2-file rank-changing leap). Promote to Q/R/B/Commoner. ANCHOR perft 18/324/6765/139774. Probe-verified (royal-knight royal, perft d2=324). Browser-verified (setup renders). On agp.chesslike | **done → main** |
| Crossway | build→probe→browser + **renderer fix** | Mark Steere connection game (official PDF read). N×N (size 9/11/13/19, default 13); Black top↔bottom, White left↔right. The "no-crossing" rule is a PLACEMENT restriction (never complete the 2×2 BW/WB checkerboard) → no two opposite-colour diagonals cross; connectivity = plain 8-adjacency; can't draw (verified 60 games → always exactly one connector). Pie via "swap". Probe-verified. **RENDERER: extended the coloured goal-edge frame to SQUARE boards** (was hex-rhombus-only) → Crossway + the existing Gonnect now show goal sides; browser-verified both, no regression | **done → main** |
| Symple | build→**P-corrected**→probe→browser | Freeling/Rosenau group game. Odd square (19 default/13). Turn = place a NEW group (not adj to own) OR GROW all growable groups by 1 (bridging stone merges groups; no double-grow; surrounded skip); 2nd-player balancing grow+place. Score = stones − P·groups (**P = even const 4..12 default 8, corrected from my P=N guess** per mindsports.nl). Grow = multi-step same-player turn (action button → one cell/group → auto-end). Probe-verified (single+multi-group grow, merge). Browser-verified (score caption, the grow→cell→end flow, group grew −7→−6) | **done → main** |
| Irensei | build→**brief-corrected**→probe→browser | 囲連星 Go/Gomoku hybrid (19×19). Build agent corrected my brief: it's **SEVEN** in a row (not 5) in the central 15×15 (outer 2 lines excluded), Black exact-7 (overline-8 loses) / White ≥7; full Go captures + ko/superko + suicide-illegal-unless-winning; reuses the Go liberty core. Edge frame tinted (136 cells). Probe-verified (inner-7 wins, edge-7 doesn't). Browser-verified (19×19 + tinted edge). NOTE: validate slow (~2.5min, Go legality) but passes; suite uses fast frozen selftest | **done → main** |
| Meridians | build→**designer-corrected**→probe→browser | Kanare Kato 2021 (NOT Steere — agent found the real PDF). Centerless triangle-tessellated hexagon (2 short+4 long sides, **114 pts**; 80/154 size options). Turn = remove opp dead groups then place a stone in LINE OF SIGHT of a friendly (turn 2+); a group is alive iff a clear all-empty line reaches a DIFFERENT friendly group; annihilation win. ANCHOR 114 opening moves (AiAi). Render polygons (matched nine_mens_morris, cells=LIST of {id,points}). Probe-verified (114 moves, polygons format correct). Browser-verified (asymmetric-hexagon triangular board renders, no white-screen) | **done → main** |
| Entropy | build→probe→browser | Eric Solomon order-vs-chaos (7×7, 49 chips/7 colours). CHAOS draws a random chip (stored as next_tile, EinStein has_randomness pattern) + places; ORDER slides a chip ortho through empties (no jump) or passes; board fills → Order scores all length-≥2 palindromic runs (=length, overlaps count, RRR=2+2+3). Single-game adaptation of the 2-round match: Order wins if score>PAR=30 (documented). Tiles via piece.fill+label (not seat-owned). Probe-verified (next_tile, alternation, termination). Browser-verified (purple "F" chip renders, Chaos F@3,3, Order pass/slide turn) | **done → main** |
| Starweb | build→probe→browser | Christian Freeling 2017. Six-fold "web" board (hexhex-7 + a 15-cell triangular bump/side = **217 cells**, **18 stars** = 12 outward tips + 6 inward notches). Place/pass; group with n stars scores triangular n(n+1)/2; most points, DRAWLESS (tie→2nd). Pie/swap. Board geometry reconstructed from the official diagram + verified cell-for-cell vs a generative construction. Render polygons (matched battle_sheep), stars gold-tinted. Probe-verified (217 cells, 18 tints, drawless). Browser-verified (web board + six bumps + gold stars render) | **done → main** |
| Unlur | build→probe→browser | Jorge Gómez Arrausi 2001 asymmetric hex connection. Hexhex (6 default). BLACK wins by a chain touching 3 NON-ADJACENT sides (Y), WHITE by 2 OPPOSITE sides (line); SELF-LOSS = making the opponent's shape → DRAWLESS. The "contract" opening: both play black/pass; passer becomes Black, other White & moves first. Pie OFF. Render Havannah-style + board.tints alternating the 6 sides. Probe-verified (30 tints, contract→White, drawless). Browser-verified (alternating side tints + "Contract phase" caption render) | **done → main** |
| Storisende | build→probe→**QA-fix**→browser | Freeling 2018 territory/stacking (hexhex base 4). Stacks move/split by height (jump), merge/capture-by-replacement; vacating a virgin cell CRYSTALLISES it green (territory) or dark Wall; control a territory iff only you have men in it; most controlled cells wins. Render matches tumbleweed (stacks) + kamisado (tints). **DEEP-QA CAUGHT A REAL BUG:** literal "3-fold repetition = draw" made EVERY random/bot game a draw (a 16-0 board scored "Draw" — stacks shuffle, leader denied the pass-win) → fixed to resolve repetition/cap BY SCORE (tie still draws), flagged deviation; active play 0/40→40/40 decisive. Browser-verified (setup renders) | **done → main** |

## Batch 36 — Chess Variant Pages pool (2026-06-24) · 153 games
_Famous-distinct backlog drained; now mining CVP chess variants (reliable, perft-anchorable) + distinct abstracts._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Maharajah and the Sepoys | build→probe→browser | Asymmetric: seat 0 = a lone AMAZON "M" (Queen+Knight, royal) on e1 vs seat 1 = a full Sepoy army with NO pawn promotion; sepoys move first. Both sides royal (overrode ChessLike `_royal_sq`: "M" for White, "K" for Black). Win = checkmate the enemy royal. ANCHOR opening 20. Probe-verified (Amazon = 8 knight jumps + queen rays, 1v16, two royals). Browser-verified (lone M vs full army renders). On agp.chesslike | **done → main** |
| Extinction Chess | build→probe→browser | Schmittberger "Survival of the Species". Standard chess BUT king not royal (no check/mate; moving into check legal); WIN by capturing ALL of any one enemy piece-type {K,Q,R,B,N,P}. On ChessLike: overrode `_legal` to drop king-safety, NoCheckCastling, promote-to-Q/R/B/N/K, extinction win as event. ANCHOR perft 20/400/8902/**197742** (d4 diverges from chess's 197281 → proves royalty filter off). Probe-verified (perft, last-knight-capture wins, into-check legal). Browser-verified (chess setup renders) | **done → main** |
| Almost Chess | build→probe→browser | Betza: queens → CHANCELLORS ("M"=R+N, reused from Grand Chess's Marshall) on d1/d8, else standard. ANCHOR perft **22**/484/11895/290522 (d1=22 not 20 — build agent caught that the Chancellor's knight leaps give 2 extra opening moves). Promote M/R/B/N. Probe-verified (no queen, Chancellor=rook∪knight no diagonals). Browser-verified (R·N·B·M·K·B·N·R renders). On agp.chesslike | **done → main** |
| Star | build→probe→browser | Schensted 1983 drawless connection-scoring. Hexagon with ALTERNATING-length sides (A5/B6 → 106 playing cells; odd perimeter → drawless) + 39 non-playable "partial hexagon" border cells (corner touches 3 / edge 2 / interior 0). Group touching ≥3 borders scores (borders−2); most points wins. Render polygons (145 cells, gold border tints). Probe-verified (106 cells, drawless 8/8). Browser-verified (alternating-side star board + gold border render). GOTCHA: search "Star" substring-matches "starts" in many descs → filter by Connection category to surface the right card | **done → main** |
| Andernach Chess | build→probe→browser | A CAPTURING piece changes to the opponent's colour (kings exempt); en passant flips; pawn-capture-to-last-rank promotes then flips. On ChessLike: one `_resolve` does move+capture+promo+flip, routed through BOTH `_legal` and apply (king-safety tested on the POST-FLIP board). ANCHOR perft 20/400/8902/197410 (d4≠197281). Probe-verified (capture flips W→B, king-cap doesn't, quiet doesn't). **Browser-verified the signature** (Pe4xd5 → the capturing White pawn became a BLACK pawn). On agp.chesslike | **done → main** |
| Poly-Y | build→probe→browser + **renderer fix** | Schensted/Titus polygonal Y. Pentagon of hexes (mudcrack-pie, 101 cells; 5 corners → DRAWLESS); corner owned via the Y connection-test (corner's 2 sides + any other side); majority of 5 wins. Verified every corner always resolves (25k random). Render polygons (5 gold corners). **RENDERER FIX (Board.jsx):** cell-move detection now keys off the real board cell-id SET (not the numeric "c,r" regex) → irregular polygons boards with LABELLED ids (Poly-Y "c"/"f,0,1,1", **Tsoro "0".."6"**) are click-to-place not a 101-button list. Browser-verified BOTH (Poly-Y click-to-place; Berolina/chess click-to-move still works = no regression) | **done → main** |
| Dunsany's Chess | build→**brief-corrected×2**→probe→browser | Lord Dunsany asymmetric: Black = full army (ranks 7-8), White = 32 pawns (ranks 1-4, no king). Agent corrected my brief twice (BLACK/pieces move FIRST; only Black's pawns double-step). White wins by mate, Black by capturing all 32 pawns (annihilation via returns, Horde-style). ANCHOR perft 20/166/3550/33601. Probe-verified (32 pawns, no White king, Black-first, white single-step-only, annihilation=[-1,1]). Browser-verified (32-pawn wall vs full army). On agp.chesslike | **done → main** |
| Cylinder Chess | build→probe→browser | The a/h files join into a vertical cylinder — sliders/knights/pawn-captures wrap (file mod 8); ranks don't wrap. On ChessLike: file-mod-8 geometry, rays capped at WIDTH-1 (no self-loop) + stop at first blocker + per-piece dedup; wrapped check; CylinderPawn diagonal-capture wrap; standard castling. ANCHOR perft 20/392/9162 (d1=20 — full back rank blocks wraps at start, agent corrected my d1>20; d2/d3 diverge). Probe-verified (rook/knight/bishop all wrap a→h, no loop). Browser-verified (8×8 renders). On agp.chesslike | **done → main** |
| Checkless Chess | build→probe→browser | Giving check is ILLEGAL unless it's checkmate. On ChessLike: after own-king-safety, remove any move leaving the opponent in check-but-not-mate (mate tested via the ordinary-chess reply gen → no recursion; mate = ordinary mate, documented). ANCHOR perft 20/400/**8890** (=8902−12, the 12 removed = non-mating depth-3 checks, verified). Probe-verified (non-mating check absent, mating check legal+wins). Browser/API-verified (32 pieces render). On agp.chesslike | **done → main** |
| ConHex | agent(session-limited)→orchestrator-verified→browser | Antonow 2002 two-layer connection. 41 cells (squares/pentagons/4 diamond corners) on 69 placement points; place a peg, own a majority of a cell's points → claim it; connect your two sides with a chain of owned cells (corners belong to both sides); drawless, pie. Render polygons (110 = 41 cells + 69 point markers); place-on-point click via the labelled-id renderer fix. **Agent completed but a session-limit cut its report → orchestrator verified** (validate OK, selftest OK, probe: polygons format/69 points/drawless 8-0, suite green). Browser-verified (concentric-ring board + points render) | **done → main** |
| Pocket Knight Chess | build→probe→browser | Standard chess + each side has ONE extra knight in pocket, droppable on any empty square once (may check/mate). On ChessLike: PocketKnightDrops(DropRules) — enabled, initial_hands {N:1}/side, captured_to_hand=None (no Crazyhouse banking → one-time). Reuses the reserve tray + "N@c,r". ANCHOR opening 52 (20+32 drops). Probe-verified (1 knight/side, drop empties hand, capture doesn't bank). Browser-verified (both reserve trays show the pocket knight). On agp.chesslike | **done → main** |
| Legan Chess | build→**setup-corrected**→probe→browser | Legan 1913 corner-to-corner chess. Armies in opposite corners (K h1/a8) behind diagonal pawn walls; LEGAN PAWN moves diagonally toward the enemy corner, captures orthogonally; promote at the corner edges; no castling/ep. Agent used the consistent Wikipedia point-symmetric setup (gambiter's was garbled). ANCHOR perft 8/64/724 (hand-verified d1=8). Probe-verified (corner kings, pawn diagonal-move/orthogonal-capture). Browser-verified (diagonal corner armies + pawn walls render). On agp.chesslike | **done → main** |
| Grasshopper Chess | build→probe→browser | Boyer: standard chess + a rank of 8 GRASSHOPPERS ("G", rank 3/6). Grasshopper moves along queen-lines but must hop over exactly ONE hurdle (either colour) and land IMMEDIATELY beyond it. On ChessLike: "G" empty slide/leap + hurdle-scan (like xiangqi cannon but land at the next square); attack-by-hop → checks+pins. ANCHOR perft 14/212/4074 (d1=14: only G hops; the e-file G is PINNED). Probe-verified (hop lands one-past-hurdle only). Browser-verified ("G" rank renders, only G's movable at opening). On agp.chesslike | **done → main** |
| Anti-King Chess | build→probe→browser | Aronson v.II: standard chess + a second royal, the Anti-King "A" (d6/d3, each starts pawn-attacked). INVERTED check: the anti-king is safe only when ATTACKED; you may never leave your own anti-king un-attacked; anti-checkmate (can't keep it attacked) loses. A moves like a king, captures FRIENDLY only, never captured, gives no check; kings don't attack A's. Win = mate the King OR anti-mate the Anti-King. On ChessLike: A out of PIECES + custom _pseudo; _in_danger = king-check OR A-not-attacked; _legal filters all moves. ANCHOR perft 22/490/11469. Probe-verified (A only to attacked squares, NOT to un-attacked; two-royal serialize). Browser-verified (both kings + both "A" render). On agp.chesslike | **done → main** |
| Slimetrail | build(+agent-browser)→probe→browser | Bill Taylor 1992 pursuit-race. N×N (default 8); a shared NEUTRAL "@" snail at centre; slide it one king-step, the vacated cell becomes permanent slime (no revisit). Goals in opposite corners; moving onto a goal makes that goal's OWNER win (can be forced to deliver opp's win); no-move loses. Bounded (≤N² moves). Render square + tints (goals+slime) + neutral @ disc; single-click destination. Probe-verified (slime-no-revisit, 12/12 decisive). Browser-verified (snail + 2 goal corners + move dots; green slime trail). First non-chess of the run's tail (lobby balance) | **done → main** |
| Knight Relay Chess | build→**brief-corrected**→probe→browser | Charosh: a piece DEFENDED by a friendly knight also moves as a knight (relay). **Build agent corrected me: the KING does NOT relay** (all sources exclude it). Knights can't capture/be-captured/give-check-alone but relay. On ChessLike: attacked() skips real knights + adds relayed knight-attacks; _pseudo forbids landing on an enemy knight + adds leaps to knight-guarded pieces; guard from raw positions (no recursion). ANCHOR opening 28 (16+4+8 relayed from knight-guarded d2/e2), perft 784/24044. Probe-verified (guarded pawn relays, knight can't capture nor be captured). Browser-verified (chess board). On agp.chesslike | **done → main** |

## Batch 37 — asymmetric chess + a paper-and-pencil classic (2026-06-24) · 169 games
_New session resuming the loop (167 → 169). One chess variant + one non-chess (lobby balance), each through the full gate; orchestrator QA caught a real Hoplite bug the build's own selftest missed._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Spartan Chess | build→**QA-fix**→probe→browser | Steven Streetman 2010 asymmetric two-civilization variant. Persians (White, seat 0) = orthodox FIDE army, one King, move first; Spartans (Black, seat 1) = TWO Kings + unique pieces (General=R+F, Warlord=B+N, Captain=1/2-orth-jump, Lieutenant=1/2-diag-jump + non-capturing sideways step, Hoplite=reverse pawn: diagonal move / straight capture / initial diagonal jump). On agp.chesslike via _kings/_in_danger: two-King CHECK IMMUNITY — in danger only on DUPLE-check (both Kings attacked); Persian may capture a lone Spartan King; reduced to one King → orthodox. Hoplite promotes to G/W/C/L (and King only when down to one King). **Orchestrator QA caught a real faithfulness bug** the build's selftest missed: the Hoplite initial double-step was nested under the single-step-empty check, so it would NOT jump an occupied intermediate — but the inventor's rules (verified) say the two-square move "is also a jumping movement … it can hop over intervening pieces"; un-nested it (perft anchor unchanged since opening intermediates are empty). ANCHOR opening 20/32, perft 20/640/14244. Probe-verified (two-King immunity, duple-check, King-capture, Hoplite move/jump/straight-capture, Lieutenant diag-capture-vs-sideways-no-capture). Browser-verified (two kings render, Persian Pe2-e4, **Hoplite reverse-pawn diagonal He7-d6** with diagonal single + double-jump targets). On agp.chesslike | **done → main** |
| Dots and Boxes | build(+agent-browser)→probe→browser | Édouard Lucas's "La Pipopipette" (1889). m×n box grid ((m+1)×(n+1) dots, default 5×5, size option); draw an undrawn edge between adjacent dots; completing a box's 4th side claims it + grants the SAME player another move (one extra even if a single edge closes two boxes — chains via successive completing moves); else turn passes; most boxes wins, equal=draw. Non-chess (lobby balance), Territory category, implements agp.game.Game directly. Move encoding = each edge is its OWN clickable `polygons` cell whose id IS the move string ("Hc,r"/"Vc,r") → undrawn edge = legal 1-cell move = click-to-place (the Quoridor board.walls primitive can't represent D&B edges — 2-cell grooves, no border edges — so polygon edge-cells instead). Closed boxes tinted owner-colour + labelled; to_move unchanged when ≥1 box closed. ANCHOR opening = edge count m(n+1)+n(m+1) = 60 (naturally finite, no cap). Pure-stdlib selftest (8 cases incl. double-box-one-extra-move, full playouts sum(scores)=m*n, tie→draw). Browser-verified (edge slots + dots + boxes render, edges draw gold, **box (0,0) closed → tinted + labelled + mover kept the turn** = extra-turn confirmed) | **done → main** |

## Batch 38 — 10×10 chess + a graph-theory classic (2026-06-24) · 171 games
_Same session continuing. NOTE: initially also assigned a "Pente" build — caught that pente ALREADY exists (committed); the build agent had silently overwritten it (changed default opening + REMOVED the ply-cap termination backstop on faulty reasoning that captures fill the board — they don't, a capture is net −1 stones so Pente can cycle). Reverted wholesale; swapped in Sim. Lesson: dedup every candidate (`ls games/` + `git cat-file -e HEAD:…`) before assigning a build._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Sim | build→probe→browser | Gustavus Simmons 1969 Ramsey graph game. Board = complete graph K6 (6 vertices, all 15 edges); players alternately COLOUR one uncoloured edge in their own colour (Red first). MISÈRE: the mover who completes a triangle of their OWN colour LOSES. By Ramsey R(3,3)=6 NO draw is possible (decisive ≤15 plies, no cap). Non-chess (lobby balance), Territory category, agp.game.Game directly. Render REUSES the verified Dots-and-Boxes edge-cell pattern: `polygons` (6 vertex diamonds non-clickable + 15 edge quads whose id = move string "e{i}-{j}") → click-to-place, claimed edges tinted owner-colour; hexagon vertex layout in origin-centred coords (auto-fit). ANCHOR opening = 15. Pure-stdlib selftest (loss-via-own-third-edge, no-loss-from-opponent-triangle, exhaustive losing-move scan, 400 always-decisive playouts, serialize). Browser-verified (K6 + all 15 edges incl. centre diagonals render, edge 0-1 → red, "Red 0-1", turn→Blue) | **done → main** |
| Shako | build→probe→browser | Jean-Louis Cazaux 1990, 10×10 chess on agp.chesslike. Full FIDE army + **Cannon "C"** (Xiangqi cannon: rook-slide on empty lines, captures ONLY by jumping exactly one screen — custom _cannon_targets + attacked() override, modeled on xiangqi/grasshopper, so cannon checks detected) + **Elephant "E"** (Ferz+Alfil: 1 or 2 diagonal, the 2-step leaping the intermediate; pure leaper ("E":([],DIAG+ALFIL))). Setup: Cannons in rank-1 corners, rank 2 = E R N B Q K B N R E (Q on e, K on f), pawns rank 3. Promote to Q/R/B/N/C/E; castling YES (f-file king, targets confirmed vs Fairy-Stockfish); insufficient-material draw off while a C/E is on the board; 800-ply cap. ANCHOR (no published perft) opening = 58 (hand-decomposed P20 C16 E4 N6 R2 B4 Q3 K3), perft 58/3364/185938 frozen in selftest (~17s). Independently probed (Cannon one-screen capture / not-adjacent / not-two-screens / check; Elephant exact Ferz+Alfil 8 leaping an occupied intermediate). Browser-verified (10×10, 4 corner Cannons + E·R·N·B·Q·K·B·N·R·E + 10 pawns render; Cannon back-rank slide Ca1-e1 applies, turn advances). On agp.chesslike | **done → main** |

## Batch 39 — gating chess + an asymmetric hunt (2026-06-24) · 173 games
_Same session. Deduped every candidate up front (post-Pente lesson)._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Three Musketeers | build→probe→browser | Haar Hoolim asymmetric 5×5 hunt, all 25 squares filled. Seat 0 = 3 MUSKETEERS "M" on two opposite corners + centre (0,0/2,2/4,4); seat 1 = 22 ENEMY filling the rest; Musketeers move first. A Musketeer MUST capture an orthogonally-adjacent enemy (relocate onto it); an enemy steps to an adjacent EMPTY square (no capture). ENEMY wins the instant the 3 Musketeers share a row/column (a line only forms on a Musketeer's own forced capture, checked after every move); MUSKETEERS win if on their turn no capture is available (and not lined up). Non-chess (Hunt category), agp.game.Game directly; move = "c,r>c,r" click-to-move; M tinted. 400-ply cap draws the (never-seen) enemy-shuffle; win-as-event. ANCHOR opening = 8. Pure-stdlib selftest (forced-line→enemy-win, stuck→Musketeers-win, capture-relocate, enemy-empty-only, 200/200 decisive, serialize). Probe-verified both win conditions. Browser-verified (5×5 fills, 3 M on corners+centre, centre M's 4 adjacent enemies highlight, capture M c3xc4 relocates + removes + vacates, turn→enemy) | **done → main** |
| Seirawan Chess | build→probe→browser | Seirawan & Harper 2007 gating/reserve variant on agp.chesslike. FIDE chess + Hawk "H"=B+N and Elephant "E"=R+N held in reserve. GATING: the first move of an original back-rank piece (or a castle) MAY place a reserve piece onto the vacated square (optional, each enters once); leaving a home square without gating forfeits that square's right; castling may gate onto the king's OR rook's vacated square; no gating while in check; promote to H/E only from reserve. **Move encoding drives the EXISTING =CHOICE picker with NO server/Board.jsx change** — a gating move is a back-rank move/castle with a "=" suffix sharing the cell path (=H/=E king square, =Hr/=Er rook square), so Board.jsx pops the promotion-picker widget; spec.reserve trays + choiceNames/choiceTitle. Reserve in CState.hands + a `gates` frozenset (folded into the rep poskey). INTERPRETATION (documented): gated variants are a subset of plain-legal moves → the ultra-rare gate-to-reblock-a-self-pin move isn't generated (never yields an illegal move; perft unaffected). ANCHOR opening = 28 (16 pawn + 4 knight + 8 knight-gating), perft 28/784/24830 frozen. Probe-verified (gate-on-knight-move places piece + consumes reserve + clears right; no-gate forfeits right; castle gates onto king/rook square — O-O=Hr→Hawk on h1; promo-to-H/E only from reserve). Browser-verified the SIGNATURE end-to-end (reserve trays show E+H; knight move popped the gating picker; "Gate Hawk" placed the Hawk on b1, logged "Nb1-c3/Hb1", reserve E·H→E, turn advanced). On agp.chesslike | **done → main** |

## Batch 40 — two non-chess classics (lobby rebalance) (2026-06-24) · 175 games
_Lobby was chess-heavy (~38 variants) → deliberately did two distinct non-chess games this round. Both deduped up front._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Qubic | build→probe→browser | Parker Bros 1953 4×4×4 3D tic-tac-toe (solved first-player win, Patashnik 1980). 64 cells (x,y,z); place on any empty cell (no gravity); FOUR-in-a-line wins; full board no-line = draw. Non-chess (N-in-a-row). The **76 winning lines** enumerated programmatically (every cell × 26 dirs, dedup as frozensets) + asserted = 48 axis + 24 face + 4 space; _lines_through for fast win-check. Render: four z-layers as side-by-side 4×4 polygons grids (x-offset z*(4+1.5), per-layer tint), each cell id = move string "x,y,z" → the labelled-id click-to-place handles 3-component ids. ANCHOR 76 lines + opening 64. Pure-stdlib selftest (line count+breakdown, axis/face/space wins, three≠win, constructed full-board draw 32X/32O, serialize). Browser-verified (4 tinted layers render, 3-comp ids clickable, X (0,0,0)→(3,0,0) layer-0 row → "X wins") | **done → main** |
| Pallanguzhi | build→probe→browser | South Indian/Tamil 2×7 lap-sowing mancala. Implemented the documented single-round "cow/kashi" variant (6 seeds/pit = 84). CCW sowing; lap/relay (last seed → next pit non-empty → scoop + continue); capture-at-4 ("kashi", immediate) + empty-pit ending (capture the pit BEYOND an empty next-pit); round ends when mover has no non-empty own pit, loose seeds swept to row owner, most seeds wins (42–42 draw). Agent flagged + documented the capture-threshold ambiguity (chose 4 over Wikipedia's 148-counter capture-at-6 "pasu" multi-round game; "facing pit" capture noted unimplemented). Reuses the toguz_kumalak/oware pit render (seed-count labels + stores in caption); move = own pit cell id. Termination: capture drains seeds + laps stop at empty next-pit + 100k lap bound + 2000-ply cap (random max ~188). ANCHOR seed-conservation==84 every step + opening 7. Pure-stdlib selftest (conservation 300 games, kashi, empty-pit-beyond, lap, mid-lap kashi, sweep, win/draw). Browser-verified (7×2 pits all "6"; sow from Bottom pit 3 relayed a lap + captured 7 via empty-pit rule, store Bottom 7, 84 conserved, turn passed) | **done → main** |

## Batch 41 — exotic-capture chess + a cross-board hunt (2026-06-24) · 177 games
_Same session. Deduped up front._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Fox and Geese | build→probe→browser | The classic 33-point cross-board hunt (1 Fox vs 15 Geese), distinct from the existing fox_and_hounds. 7×7 minus the four 2×2 corners; ortho lines + alquerque diagonals at strong (col+row even) points. Geese (seat 0, move first) step forward/sideways/diag-forward only (no backward), never capture; Fox steps any dir or draughts-jumps a goose (multi-jump chains, not mandatory). GEESE win by trapping the fox (no move); FOX wins by reducing geese to ≤2. Non-chess (Hunt), polygons cross board (33 cells + 72 lines). Documented choices (Masters of Games/Cyningstan): 15 geese (vs fox-favouring historical 13), alquerque diagonals (ortho-only = noted variant), geese-first, fox-win-at-2. Minor note: the no-progress draw is checked before the trap-win (rare slow-trap edge). ANCHOR 33 pts/centre-deg-8/opening 12. Pure-stdlib selftest (adjacency, no-backward, fox single+multi jump, geese-trap win, reduce-to-2 fox win, serialize). Browser-verified (cross board renders, goose move-gen highlights, G 0,3-0,2 applies, turn→Fox) | **done → main** |
| Ultima (Baroque Chess) | build→probe(all-7-methods)→browser | Robert Abbott 1962 — every piece moves like a queen (King 1-step, Pincer Pawn=rook) but CAPTURES by a UNIQUE method (capture = side effect of where you move; one move removes 0/1/several). I=Immobilizer (freezes adjacent enemies, never captures), L=Long Leaper (leap-capture, multi-chain), M=Chameleon (captures each enemy by THAT enemy's own method, can't take a Chameleon), C=Coordinator (rook-cross with own King), W=Withdrawer (move away from an adjacent enemy), K=King (displacement), P=Pincer Pawn (custodial). Back rank I L M K W M L C. Implements agp.game.Game directly. The immobilizer/chameleon FREEZE PARADOX (the ambiguous corner) follows MacKay "pure rules": Chameleon↔Immobilizer + Immobilizer↔Immobilizer mutually freeze; a friendly M/I beside an enemy Immobilizer neutralizes it — DOCUMENTED cited interpretation (auto-merged, not queued: faithful to a published ruleset, near-never arises in play). Win = capture enemy King (no check enforcement, documented). ANCHOR opening 32. Pure-stdlib selftest hits EACH capture type + negatives via apply_move. **I independently probed all 7 capture methods + freeze + mutual-freeze + king-capture-win — all correct.** Browser-verified (all 7 piece types render, Pincer Pawn P 4,1-4,4, turn advanced) | **done → main** |

## Batch 42 — bird shogi + the first dice-race (2026-06-24) · 179 games
_Same session. Deduped up front. Royal Game of Ur adds the dice-race genre (only EinStein had dice before)._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Tori Shogi (Bird Shogi) | build→probe→browser | 1828 7×7 all-birds Shogi variant on agp.shogilike (inherits drops/reserve, zone promotion). Pieces: Phoenix (royal king), Swallow (→Goose), Falcon (→Eagle), Crane, Pheasant (jumps 2 fwd + 1 diag back), and the **ASYMMETRIC** Left/Right Quails. KEY: shogilike flips only the rank axis between colours (fine for symmetric pieces) but the Quails are L/R asymmetric → the subclass supplies its own bird tables + applies a full **180° rotation** (both axes) for White; I verified White's Left Quail is the exact point-reflection, not a row-flip. Tori nifu = up to TWO unpromoted swallows/file (vs Shogi's one). ANCHOR opening 17, perft 17/288/5445 frozen (no external oracle). Independently probed perft + both quails + 180° + pheasant-jump. Browser-verified (all birds render 180°-mirrored, swallow capture Sw2,3x2,4 banked into the reserve tray, turn advanced). On agp.shogilike | **done → main** |
| Royal Game of Ur | build(report-truncated→orchestrator-verified)→probe→browser | Finkel's (British Museum) reconstruction of the ~4500-yr-old Mesopotamian race game. 20-square H-board (3×8 minus 4 bridge cells), shared central lane; 7 pieces each race a 14-square path. **First dice-race in the library** — four tetrahedral dice → 0..4 binomial(4,½), modelled WITHOUT a chance node (EinStein pattern: the roll is stored in state, rolled in initial_state/apply_move; has_randomness). 5 rosettes (path sq 4/8/14): SAFE + EXTRA TURN (re-roll, chainable, reuses the Dots-and-Boxes same-player-again idea). Capture on a shared square sends an enemy home; exact bear-off; win at 7 off. Move encoding: on-board "c,r>c,r", off-board entry single-cell "c,r", bear-off "c,r>off", "pass" — all drive the generic UI, die shown in the caption. Render polygons H-board + gold rosettes. **Build agent's report was truncated (ended mid-wait) → I orchestrator-verified the package directly** (validate OK, selftest OK, suite green) + independently probed rosette-extra-turn/capture/rosette-safety/exact-bear-off/win/dice-distribution. Browser-verified ("White rolled 2" in caption, entry to (2,0), waiting 7→6, turn→Black with fresh roll). ANCHOR path-14/5-rosettes/binomial dice | **done → main** |

## Batch 43 — shape-logic + Burmese chess (2026-06-24) · 181 games
_Same session. Deduped up front. Both build agents' reports were truncated mid-wait → I orchestrator-verified both packages directly + independently probed (a recurring pattern now — verify the package, don't trust a missing report)._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Quantik | build(report-truncated→orchestrator-verified)→probe→browser | Gigamic 2019 4×4 shape-placement logic duel. Four 2×2 zones; each player has 8 pieces = 2 each of 4 shapes (A/B/C/D). Placement restriction (the crux): may NOT place a shape in a row/col/zone where the OPPONENT already has that shape (your OWN same shape is fine). WIN = complete any row/col/zone with all 4 DISTINCT shapes (colours irrelevant). LOSS = no legal placement. Non-chess (Positional). Move = reserve-tray drop "<shape>@c,r"; shapes as owner-coloured glyphs ■●▮▲; zones via tints + board.lines dividers (the 3rd-element colour string IS supported by decorPath — confirmed). ANCHOR opening 64. Pure-stdlib selftest (9 cases). Independently probed opponent-restriction / own-allowed / all-4-win. Browser-verified (armed shape A from the tray, dropped "cube (A) @ 2,2", glyph + reserve decrement + turn) | **done → main** |
| Sittuyin (Burmese Chess) | build→probe→browser | Traditional chess of Myanmar on agp.chesslike, anchored on the Fairy-Stockfish `sittuyin` variant def (start FEN, deployment rule, 8 promo squares). Pieces: K(king), G(ferz general), E/e(elephant=4diag+fwd), N(knight), R(rook), P(1-step pawn, no double). Two signatures: **DEPLOYMENT phase** (only pawns start in the staggered split formation; players alternately place their 8 reserve pieces in their own 3 ranks, R on back rank only, White first; play begins when reserves empty — modelled via CState.hands + region-restricted "L@c,r" drops) + **SIT-TU promotion** (a pawn on a long-diagonal enemy-half square may become a General, in-place or to an adjacent diagonal, ONLY when the player has no General). Documented interpretations: sequential-open deployment (vs OTB curtain), omitted "no aggressive promotion" + Burmese counting (Makruk-style draws). ANCHOR conformance (40 full games avg 369) + rule positions (no meaningful perft w/ deployment). Pure-stdlib selftest. Independently probed setup-restriction + 16-drop transition + Elephant(4diag+fwd) + promotion-needs-no-General. Browser-verified the DEPLOYMENT signature (staggered pawns + reserve trays + region tint, deployed E@e1, reserve E×2→×1, region tint switched sides). On agp.chesslike | **done → main** |

## Batch 44 — animal shogi + a dice-race war game (2026-06-24) · 183 games
_Same session. Deduped up front._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Dobutsu Shogi (Animal Shogi) | build→probe→browser | Madoka Kitao 2008, the famous solved 3×4 kids' shogi on agp.shogilike. Animals: L=Lion (royal 8-way), G=Giraffe (wazir), E=Elephant (ferz), C=Chick (1 fwd → Hen), H=Hen (gold-general 6-dir). Setup E·L·G + Chick-in-front (180° mirror). Drops (no nifu, Chick drops plain, captured Hen → Chick). Two win conditions (win-as-event): CATCH (take the Lion) + TRY (Lion safely reaches enemy home rank — detected statically since move-gen never lets a Lion move into check). ANCHOR opening 4, perft 4/13/67/398 frozen (d2=13 hand-verified, no published per-depth Dobutsu perft). Pure-stdlib selftest. Independently probed perft + setup + both win conditions. Browser-verified (3×4 animals render, Chick capture C1,1x1,2, turn advanced). On agp.shogilike | **done → main** |
| Daldøs | build→probe→browser | Traditional Scandinavian "running-fight" dice-war (Denmark/Norway). **Second dice-race** (reuses the Ur dice-in-state pattern). Boat board, 3 rows of holes (private home rows + shared middle w/ prow hole), Norwegian 12+13+12/12-pieces default + Danish 16+17+16 option. TWO four-sided dice (1=the "dal"), stored in state, played one-at-a-time. Signature **dal mechanic**: un-dalled pieces are dead-in-hole, dalled only by rolling a 1 (stern→prow order), only a dalled moving piece captures (land exactly → permanent removal); win = remove ALL enemy pieces. Path: home→shared-middle→enemy-home→repeat, never back to own home. Agent corrected my brief (2 dice + 12/16 pieces, not 1 die/4). Path geometry = documented internally-consistent reconstruction; 6000-ply cap. Pure-stdlib seeded selftest. Independently probed stern-only dal-activation + pass-when-no-1 + dalled-capture→win. Browser-verified the signature (dice [3,2] {no usable die}→Pass; dice [2,1]→"Red dals a piece → 12,1" home→middle, same player continues with the 2). Non-chess (Race) | **done → main** |

## Batch 45 — flip-piece shogi + a 4-player dice-race (2026-06-24) · 185 games
_Same session. Deduped up front. The marquee distinct pool is now nearly drained — flagging for Erik below that the remaining seam is focused-builds + new-render-primitive games._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Kyoto Shogi | build→**brief-corrected**→probe→browser | Tamaki Akira 1976 flip-piece 5×5 shogi on agp.shogilike. **Build agent corrected my brief on the pairs:** T↔L (Tokin=gold/Lance), S↔B (Silver/Bishop), G↔N (Gold/Knight), P↔R (Pawn/Rook); K=King never flips. SIGNATURE: every move flips the moving token to its OTHER face (alternating roles); timing = move as the pre-flip face, then flip, so check is judged on the post-flip board (overrode _board_after+apply_move). No promotion zone (flip replaces it). DROP face-choice = render() emits BOTH faces as reserve chips, "S@c,r"/"B@c,r" drops decrement the shared pair. ANCHOR opening 12, perft 12/137/1636. Pure-stdlib selftest. Independently probed opening+perft+flip (Tokin→Lance). Browser-verified (5×5 T·S·K·G·P, Tokin moved + flipped "T0,0-0,1=L"). On agp.shogilike | **done → main** |
| Pachisi | build→probe→browser | The classic 4-player Indian cross-and-circle race (ancestor of Ludo). **num_players=4** free-for-all (partnerships omitted), third dice game. Cruciform cross board (4 arms 3×8 + Charkoni), private safe home columns + shared main track. 6 cowrie shells → 0→25/1→10/2→2/3→3/4→4/5→5/6→6 (binomial(6,½), verified); stored in state (no chance node, Ur/Daldøs pattern); GRACE throws (6/10/25) = extra turn + only-way-to-enter. 12 castle safe squares; capture sends an enemy back to Charkoni; exact-count finish. Returns = 4-vector (+1 winner / −1 others, like Rolit). Render polygons cross (105 cells, tinted home cols + gold castles, 4 seat colours). PLY_CAP 1500 leader-wins (long random-play tail; MCTS bot slowish — perf trait). Pure-stdlib seeded selftest. Independently probed cowrie distribution + 4-player returns. Browser-verified (cross + 4 seats render, "Red threw 4 — pass", "Green threw 10 (grace!)", entry applied + waiting 4→3 + grace extra-turn). Non-chess (Race) | **done → main** |

## Batch 46 — THE MARQUEE: Backgammon + Maura's Modern Chess (2026-06-24) · 187 games
_Same session. Deduped up front. Backgammon = the most-famous game still missing; rules 100% standard (cube omitted as the documented default), so done unattended with deep QA._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Backgammon | build→**deep-probe(all mechanics)**→browser | Standard single-game Backgammon (bear off all 15 to win), the marquee missing game. 4th dice game, reuses the Ur/Daldøs/Pachisi dice-in-state + sub-move-sequencing. 24 absolute points + bar + off; White 24→1 / Black 1→24 (25−p mirror); two d6, doublets→4 moves; hit a blot→bar; bar must enter first; bear off (exact or overshoot-from-highest-only). **MUST-USE-BOTH-DICE** via `_max_usable` recursive look-ahead — legal_moves offers only sub-moves preserving the max dice usage (official "maximal usage" rule, auto-handles play-the-larger). Bear-off overshoot consumes the smallest valid die. Move = "F>T"/"bar>P"/"F>off"/"pass". Render polygons 24-point + bar + off + piece.stack towers + dice-in-caption. Simplifications: NO doubling cube (win +1/−1), opening White-first; 4000-ply pip-leader cap. Pure-stdlib seeded selftest. **I independently probed EVERY mechanic** (setup, hit→bar, bar-enter-only, exact+overshoot bear-off, win-at-15, must-use-both) — all correct. Browser-verified (24-point board + bar + off + stacks + dice render, move White 13→8, stacks updated, same player continued with die [1]). Non-chess (Race) | **done → main** |
| Modern Chess | build→probe→browser | Gabriel Maura 1968 (Ajedrez Moderno), 9×9 on agp.chesslike. Full army + one Prime Minister "M" (=Bishop+Knight, Capablanca-Archbishop compound) + a 9th pawn. Back rank R N B M K Q B N R (King centre-file e, Queen f, Minister d). ModernCastling (9-wide: ministerside K e1→g1/R i1→h1, queenside K e1→c1/R a1→d1, full safety). Promote Q/R/B/N/M; standard double-step + ep. Maura's optional "bishop adjustment" omitted (documented). ANCHOR opening 24, perft 24/576/15832 frozen. Pure-stdlib selftest. Independently probed opening+perft+setup+Minister(B∪N). Browser-verified (9×9 R·N·B·M·K·Q·B·N·R, Pe2-e4). On agp.chesslike | **done → main** |

## Batch 47 — Alfonso X's great chess + a DECLINED CLONE (2026-06-24) · 188 games
_Same session. Grand Acedrex shipped; Sungka built but DISCARDED as a Congkak clone (the gate working)._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Grand Acedrex | build→probe→browser | Alfonso X's Libro de los Juegos (1283) 12×12 "Great Chess", Cazaux–Musser reconstruction, on agp.chesslike. Setup R L U G C A K C G U L R (both colours; NOT mirrored — both Kings on file g facing each other, Aanca on f). Pieces: K (king + one-time first-move 2-sq leap), R (rook), C=Crocodile (bishop), A=Aanca (griffon: 1 diagonal step then orthogonal slide outward, lame), U=Unicorn (rhino: knight hop then diagonal slide outward, lame), L=Lion ((3,0)+(3,1) leaper), G=Giraffe ((3,2) zebra), P (1-step pawn, no double, file-based promotion → g-pawn becomes Aanca). No castling, dice omitted (documented). Aanca/Unicorn = custom _pseudo+attacked. ANCHOR opening 59, perft 59/3481 (d3=206209). Pure-stdlib selftest. Independently probed opening+perft+setup+all exotic pieces + termination (800-ply cap, big slow board → mostly draws under random play). Browser-verified (12×12 renders, both kings file g, Pg4-g5). On agp.chesslike. Also removed a stray `engine/games/shako.zip` pack artifact | **done → main** |
| ~~Sungka~~ | build→**DISCARDED (clone)** | Philippine mancala — built fine (validate+selftest pass) but turned out byte-mechanically identical to the existing **Congkak** (both 7 houses / 7 seeds / 98 / relay / own-head-extra-turn / capture-opposite / end-sweep; congkak's own rules.md already says "the Filipino version is Sungka"). Discarded per "decline clones". **LESSON: screen traditionals with regional cousins (mancala/tafl/morris/race) for MECHANICAL clones — read the closest existing game's rules.md — not just name collisions** | **DISCARDED — not shipped** |

## Batch 48 — Janus Chess + Kensington (2026-06-24) · 190 games
_Same session. Both genuinely distinct (not clones); Kensington's intricate tessellation render came through cleanly._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Janus Chess | build→probe→browser | Werner Schöndorf 1978, 10×8 on agp.chesslike. Standard army + TWO Januses "J" (=Bishop+Knight Archbishop compound) flanking the knights on b/i. Back rank R J N B K Q B N J R (King on e / Queen on f — SWAPPED, a Janus signature). Asymmetric castling (JanusCastling): O-O-O K e→b/R a→c (king 3 sq), O-O K e→i/R j→h (king 4 sq). Promote Q/R/B/N/J. Distinct from Capablanca(10×8 Arch+Chanc)/Modern(9×9 1 Minister)/Grand(10×10). ANCHOR opening 28, perft 28/782/24747. Pure-stdlib selftest. Independently probed opening+perft+setup+Janus(B∪N). Browser-verified (10×8 R·J·N·B·K·Q·B·N·J·R, Pe2-e4). On agp.chesslike | **done → main** |
| Kensington | build→**brief-corrected**→probe→browser | Taylor & Forbes 1979 place-then-move territory game on a rhombitrihexagonal (3.4.6.4) tiling. **Build agent corrected my brief heavily**: 72 VERTICES (not 29), 7 hexagons (3 white centre / 2 red / 2 blue), 30 squares, 24 triangles, 132 edges; geometry generated + verified cell-for-cell vs the published board. 15 counters each, Red first; placement then slide-along-edges. MILLS (both phases): own triangle → relocate 1 enemy, own square → relocate 2 (max 2/turn; counters MOVED not removed). WIN = occupy all 6 verts of any WHITE hex OR a hex of YOUR OWN colour (opponent-colour doesn't win for you). Render polygons (72 vertex markers + 132 lines + 7 coloured hex outlines via N-pt polyline + trailing colour). Non-chess (Territory). Pure-stdlib selftest. Independently probed geometry + render + all 3 win cases (white/own→win, opp-colour→no-win). Browser-verified the intricate tessellation renders cleanly (7 coloured hexes) + placement @v35. **The render-risk paid off — a genuinely novel distinct game** | **done → main** |

## Batch 49 — two distinct shogi variants (2026-06-24) · 192 games
_Same session. Both genuinely distinct from our existing shogi (standard/mini/Tori/Kyoto/Hasami)._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Yari Shogi | build→probe→browser | Christian Freeling 1981 "Spear Shogi", 7×9 on agp.shogilike. Pieces range straight forward + a small step, promoting to forms that also range straight back. G=General(king), P=Pawn, N=Yari Knight (fwd-slide + (±1,+2) jump), B=Yari Bishop (fwd-slide + 1 diag-fwd), R=Yari Rook (fwd-slide + sideways, no back). Promote (far 3 ranks): Pawn→Yari Silver, Bishop/Knight→Yari Gold (straight-back range + forward steps), Rook→Rook. Setup yR yB yB G yN yN yR + 7 pawns (White 180°). ANCHOR opening 20, perft 20/400/7960. Pure-stdlib selftest. Independently probed opening+perft+setup+Yari-Rook(fwd+side,no-back). Browser-verified (7×9 renders, P3,2-3,3). On agp.shogilike | **done → main** |
| Cannon Shogi | build→**probe(cannons)**→browser | Peter Michaelsen 1998, 9×9 standard shogi + 4 cannon types + Janggi soldiers, on agp.shogilike (anchored on pychess's cannonshogi engine). C=Gold cannon (orthogonal Xiangqi: rook-slide, capture over 1 screen), D=Copper (diagonal Xiangqi), E=Silver (orthogonal JANGGI: jump 1 screen to move AND capture), F=Iron (diagonal Janggi); cannons can use another cannon as a screen. P=Soldier (Janggi: 1 step fwd OR sideways, →Gold). Cannons promote to "flying" cannons. Setup L N S G K G S N L / B + cannons (E·C flank Bishop, F·D flank Rook) + R / 5 soldiers on files 0,2,4,6,8. Cannon+soldier check-detection grafted on (xiangqi-modeled). **Build agent found+fixed 2 real bugs** (sideways-soldier check; drop-becomes-cannon-screen self-check). Source conflict resolved per pychess (gold/copper=free-slide Xiangqi, silver/iron=jump-to-move Janggi; documented). ANCHOR opening 51, perft 51/2532/137275. Pure-stdlib selftest. Independently probed opening+perft+setup+gold-cannon one-screen-capture (not zero/two). 400-game sweep = 0 illegal king-captures. Browser-verified (all 4 cannon labels render, Janggi-soldier sideways P0,2-1,2). On agp.shogilike | **done → main** |

## Batch 50 — RENDER-PRIMITIVE phase (option 2): Tsuro + the 9th primitive (2026-06-24) · 193 games
_Erik picked "option 2 — render-primitive games." I own the shared Board.jsx renderer half (heavy regression-checks); a build agent does the engine against my exact spec contract._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| **(primitive) board.tiles + board.tokens** | me (Board.jsx + SPEC) | the **9th render primitive** — path-tiles: `board.tiles={cellId:[[a,b]×4]}` draws 4 path-arcs joining a cell's 8 edge-notches; `board.tokens=[{cell,notch,owner}]` are markers on notches. Notch numbering clockwise-from-top-left (0,1 top / 2,3 right / 4,5 bottom / 6,7 left); cross-cell mapping top↔bottom 0↔5,1↔4 / right↔left 2↔7,3↔6. cardStrip() also renders `paths` cards (mini path-tiles) next to Onitama `offsets` cards. Opt-in, backward-compatible — **regression-verified Quixo (square) + Onitama (cards) unchanged**. Documented in SPEC.md | **done → main** |
| Tsuro | renderer(me)→engine(agent)→**render-fix**→browser | Tom McMurchie path-tile game, 6×6, agp.game.Game, has_randomness, num_players=2 (last-standing). 35 distinct tiles (105 matchings of {0..7} collapsed under 90° rotation); deck+hands dealt via rng + stored (no chance node). Place a hand tile in 1 of 4 rotations (=CHOICE picker) on the forced cell the marker enters → marker rides the path across placed tiles until it rests on an empty notch or goes off-board (eliminated); no-suicide-unless-forced; collision→both eliminated; last-standing wins, simultaneous→draw. Agent found+fixed a deck-exhaustion empty-hand crash. **RENDER BUG caught in-browser** (white-screen): the engine emitted board.cards with `paths`, but cardStrip read Onitama's `card.offsets` → crash; fixed cardStrip to branch on `paths`. ANCHOR deck=35, opening≈10. Pure-stdlib selftest. Browser-verified the WHOLE primitive (tiles draw path-arcs, token rides the path P1 tile1 rot90 @ 0,1, hand path-cards, tile+rotation picker). Move = "cell=<handIdx>.<rot>" | **done → main** |

| Hive | renderer-compose→engine(agent)→deep-probe→browser | The marquee boardless hex-tile game (John Yianni/Gen42). NO new Board.jsx primitive — COMPOSES existing ones (polygons hex-cluster of occupied+legal-target cells + reserve-tray/drops for the bug hand + piece.stack for beetles + labels). 1Q/2S/2B/3G/3A per side; place-by-touching-own-colour + queen-by-4th; per-bug moves (Queen 1 / Ant perimeter / Spider exactly-3 / Grasshopper line-jump / Beetle climb+stack); ONE-HIVE (articulation) + FREEDOM-TO-MOVE (gap rule); win = surround a Queen 6/6 (both→draw); forced pass. Place = drop "<bug>@q,r", move = "q,r>q,r". 300-ply+60-no-progress draw safeties. ANCHOR reserves 1Q/2S/2B/3G/3A, opening 5. Pure-stdlib selftest (15 sections). **I deep-probed one-hive, grasshopper, spider-exactly-3, ant, beetle-climb, surround — all correct** (my first grasshopper "fail" was my own test bug: an articulation-point piece). Browser-verified the boardless growing cluster (placed both Queens red+blue, cluster grows, reserve trays decrement). agp.game.Game | **done → main** |

| Trax | renderer(me, board.tracks)→engine(agent)→geom-fix→browser | David Smith 1980 loops-and-lines tile game on a GROWING board. **The 10th render primitive: `board.tracks`** = {cellId:[[a,b,colour]]} — colour-track segments joining the cell's 4 edge-midpoints (straight/curve), red `#d9534f` / white `#e8e8e8`. Also added cell `hw`/`hh` bounding half-extents so tile/track edge-glyphs sit on the border (fixes path/track tiles on POLYGONS boards where inscribed-radius≠half-width — tracks were falling short + not connecting). 2 tiles→6 orientations (2W/2R edges); matching rule; the FORCED-MOVE auto-fill resolution loop (the crux); win = loop OR ≥8-span line of your colour. Growing board rendered as polygons (negative ids, bbox+margin) so move ids stay absolute. Move = "c,r=<orient>" via =CHOICE picker. ANCHOR opening 1 (then 12); pure-stdlib selftest (11 tests incl. forced-move + loop/line win). Browser-verified the WHOLE primitive: colour tracks render + CONNECT across tiles (red S-curve), board grows, orientation picker + matching work. agp.game.Game | **done → main** |

| Pylos | renderer-compose→engine(agent)→probe→browser | Gigamic offset-pyramid sphere-stacking (David Royffe). NO new primitive — COMPOSES polygons (4 levels at half-offset positions, cells "L,c,r" ordered 0→3 so higher tiers draw on top) + board.tints + discs. 4×4 base, 30 spheres/15-side; place-from-reserve OR raise-a-free-own-sphere-up; level L≥1 needs its 2×2 supporters; SQUARE (2×2 same-colour) → take back 1-2 free own spheres (multi-action turn, same player); WIN = sphere on the apex (place or raise); no-move = loss. Move = "L,c,r"/"from>to"/"take:L,c,r"+"done". ANCHOR 16+9+4+1 positions, opening 16. Pure-stdlib selftest (support, square take-back variants, raise, apex win, supply=30). Browser-verified the offset pyramid (4 nested levels render, balls as discs, reserves decrement, level-1 unlocks above a filled 2×2). agp.game.Game | **done → main** |

| Octi | renderer(me, piece.prongs)→engine(agent)→naming-fix→browser | Don Green MENSA-Select pod-and-prong game (6×7 basic). **The 11th render primitive: `piece.prongs`** = [dirs 0..7] directional arrows radiating from a pod (0=N up, clockwise). 4 pods/12 prongs/side, 0 starting prongs; turn = add-prong / move-pronged-dir / jump (chain + optional enemy capture, captured prongs recycle); win = enemy-base-reach OR capture-all. Dir 0=+row matches renderer PRONG_DIR. Move = "from>to"(+=CAP/=KEEP) / "c,r=DIR" add-prong. I renamed players Green/Red→Red/Blue + retinted bases faint red/blue to match seat colours. ANCHOR opening 32. Pure-stdlib selftest (add-prong, pronged step/reject, jump+CAP/KEEP, both wins). Browser-verified both seats' prong arrows render in the right directions. agp.game.Game | **done → main** |

## Batch 51 — overnight QUANTITY run (2026-06-24 PM→AM): distinct games, mine deep wells
_Erik away overnight: "add quantity, distinct-enough is fine (not just famous), mine Zillions/chessvariants/traditionals." Full gate, batched browser smoke-checks, fast-path perft-anchored chess/shogi (low render risk). ~3 builds in parallel._
**PAUSED 1:50am (session limit) after 8 games (#198–205), suite green. NEXT-WAVE QUEUE (dedup-verified free, ready to launch on resume):** hexapawn (retry — launch failed at limit), whale_shogi, wa_shogi, marseillais_chess, progressive_chess, monster_chess, lasker_morris, omweso, cheskers, picaria, latrunculi, nard, jul_gonu, yonin_shogi, micro_shogi. AVOID clone-adjacent hunt/race variants (rimau/len_choa/komikan/adugo = bagh_chal clones; the library is so comprehensive nearly every famous distinct abstract already exists — picks are now Zillions/CVP/traditional deep cuts, dedup EVERY one).
| Game | Anchor | Status |
|---|---|---|
| Arimaa #198 | Omar Syed 2002 anti-AI abstract; 8×8 + 4 traps + push/pull/freeze + free-deploy setup (reserve+drop); win = rabbit-home/all-rabbits/immobilize. Opening 96. Standard square render. | **done → main** (browser-verified) |
| Shobu #199 | Vega/Sajdak 2019; 4 boards 4×4 (polygons 2×2), passive+aggressive paired move (opp-colour, push≤1 off-board), win = clear a board. Opening 36. | **done → main** (browser-verified 4-board layout) |
| Judkins Shogi #200 | 6×6 ShogiLike, 7 pieces/side (K R B N G S P) + drops, ZONE=2; agent overrode my brief vs Wikipedia (back rank K G S N B R, corner kings). perft 20/336/6183. Standard ShogiLike render (proven). | **done → main** (anchored; render-shape proven) |
| Senet #201 | Egyptian dice-race (Kendall reconstruction); 3×10 boustrophedon, 5 pawns, throw-sticks 1–5 w/ bonus, swap/block, special houses, exact bear-off. Square+tints render. | **done → main** (low-risk square render) |
| Gardner's Minichess #202 | Classic 5×5 minichess (Gardner 1969), ChessLike; R N B Q K + 5 pawns, no castle/double-step. **Canonical perft 7/53/506/4775.** | **done → main** (perft-anchored; standard render) |
| Goro Goro Shogi #203 | 5×6 ShogiLike, 8 pieces/side (K G×2 S×2 P×3), drops, furthest-zone promotion. Opening 7. | **done → main** (standard ShogiLike render) |
| Six Men's Morris #204 | Smaller morris (mirrors nine_mens_morris): 16 points (2 concentric squares + 4 spokes), 8 mills, NO flying. | **done → main** (browser-verified morris board) |
| Alice Chess #205 | Parton 1953 two-board "looking glass" — move on your board, transfer to the mirror (must be vacant); check on current board. Polygons 2-board (Shobu pattern). Opening 20. | **done → main** (browser-verified 2-board layout) |

## Batch 52 — resume the next-wave queue (2026-06-30): hexapawn + two small shogi
_Resumed the loop. 3 parallel builds, full gate, fast-path standard renders, batched browser smoke-check. Each rules-verified vs Wikipedia; agents overrode nothing this batch (briefs were accurate) but the micro/whale signature rules were independently web-checked by the orchestrator._
| Game | Anchor | Status |
|---|---|---|
| Hexapawn #206 | Martin Gardner 1962 3×3 pawns (AI/matchbox teaching game); chess-pawn moves, capture-only diagonals, win = reach far rank OR opponent has no move. agp.game.Game, "win as event". **Anchor: full-tree minimax = 2nd player (Black) wins** (known result). Standard square render (Breakthrough shape). | **done → main** (browser-verified 3×3, 6 pawns) |
| Micro Shogi #207 | 4×5 five-piece shogi; signature **flip-on-CAPTURE** promotion (no zone). Pairs verified vs Wikipedia: S↔L, G↔R, B↔T, P↔N; setup S G B K + king-file pawn, corner kings; either-face drops. Opening 9, perft 9/80/767 (self-computed). Live S→L flip confirmed. Distinct from judkins/kyoto/mini/dobutsu/goro. agp.shogilike + reserve. | **done → main** (render path = whale, verified) |
| Whale Shogi #208 | Schmittberger 1981 Kujira Shogi, 6×6 whale-themed; capture opponent's **White Whale** (royal) to win. Setup H G W P N B + 6 Dolphins; geometries verified vs Wikipedia (Grey=fwd-slide+diag-back, Narwhal=jump-2, Killer Whale=dragon-king, etc.). Signature: ONLY Porpoise promotes, ONLY when **captured** → banked as Killer Whale. Shogi drops w/ 3 Dolphin-only restrictions. Opening 7, perft 7/49/398. Distinct from judkins (also 6×6). agp.shogilike + reserve. | **done → main** (browser-verified 6×6 + dolphin-move highlight) |

## Batch 53 — Lasker Morris + Cheskers (wa_shogi deferred) (2026-06-30/07-01)
_Same session, 3 parallel builds. Two shipped; wa_shogi's build agent hit a session limit after writing only game.py (no manifest/selftest) → partial package REMOVED, deferred to a fresh full build. **Browser-check gotcha logged:** searching "Lasker" in QuickPlay surfaces **Lasca** (Emanuel Lasker's stacking game — its description contains "Lasker"), so the card-select launched Lasca; search the FULL distinct name ("Lasker Morris") to disambiguate._
| Game | Anchor | Status |
|---|---|---|
| Lasker Morris #209 | Emanuel Lasker's Ten Men's Morris. Same 24-pt board as nine_mens_morris (proven polygons render), 10 pieces/side, signature = interleaved place-OR-slide from move 1 (verified: slide legal while men in hand). Mill→removal; win = opp<3 or no move; 3-piece flying toggle; no-progress+threefold draw. | **done → main** (browser-verified empty morris board + placement) |
| Cheskers #210 | Solomon Golomb 1948 chess/checkers hybrid on 32 dark squares of 8×8 (standard square render). 2K/1B/1Camel/8 pawns per side; pawns+kings = checkers jumps (multi-jump, mandatory when a jump exists), bishop=chess slider, camel=(1,3) leaper (replacement capture); pawn promotes to K/B/C (=CHOICE). Win = capture all enemy Kings or stalemate. Verified vs 3 sources. | **done → main** (browser-verified 8×8 dark-square setup + selection) |
| Wa Shogi #211 | 11×11 traditional animal shogi, 27 pieces/side, **drop-less classic**. Crane King royal; rules verified vs Wikipedia wikitext + CVP. Added a (slides, leaps, ranged) movement model to the subclass for bounded slides (Cloud Eagle 1–3 diag-fwd, Liberated Horse 1–2 back) + Treacherous-Fox 2nd-square leap. Promotion zone = far 3 ranks. Standard shogi square render, 2-char labels (verified fit at 11×11). Opening 51, perft 51/2601. First attempt's agent hit a session limit after only game.py → retried fresh, completed. | **done → main** (browser-verified 11×11 + labels + selection) |

## Batch 54 — Omweso (2026-07-01): first 4-row mancala
| Game | Anchor | Status |
|---|---|---|
| Omweso #212 | Ugandan Baganda four-row mancala — the FIRST 4-row mancala (distinct from 2-row oware/kalah/congkak/pallanguzhi). 8×4, 32 pits, no stores (64 seeds conserved). Sow CCW around own two rows only; relay/lap sowing; capture = last seed in own inner row w/ both opposing pits occupied → take both + re-sow from lap start (chains); loss = to-move has no pit ≥2. Verified vs Wikipedia+UltraBoardGames+Grokipedia. Documented simplifications: free-opening (okwakya), reverse-capture (emitwe), alternate wins omitted. Standard square 8×4 render (oware's proven mancala render). Opening 8. | **done → main** (browser-verified 8×4 pit grid + setup) |

## Batch 55 — Nard (2026-07-01): Persian no-hitting backgammon
| Game | Anchor | Status |
|---|---|---|
| Nard #213 | Persian tables/race (Long Nardy). Backgammon FAMILY but mechanically DISTINCT (verified vs Wikipedia+Long-Narde+bkgm.com, gate passed): NO hitting/blots/bar (a point with ANY opponent checker is blocked, count≥1; nothing ever sent back — pure race), all-15-on-the-head start (pts 24/12 opposite corners), same rotational direction, one-off-head-per-turn (2 on first turn). Reuses backgammon's dice-in-state + sub-move + must-use-both + bear-off + polygons/stack/dice render. Six-prime block rule omitted+documented. Orchestrator independently confirmed the crux: landing on a single opponent blot is illegal (unlike backgammon). | **done → main** (browser-verified all-on-head board + dice + head-allowance caption) |

## Batch 56 — MULTI-MOVE CHESS variants (2026-07-01, Erik-directed)
_Erik picked "multi-move chess variants." KEY FINDING: the multi-move turn = the backgammon pattern (apply_move keeps to_move the same until the sub-move budget is spent) → **NO UI change** (generic UI already handles same-player-moves-again; browser-confirmed on Monster: after White's 1st move the caption reads "White to move (1 move left)"). Each variant = a self-contained ChessLike subclass with an MState(CState) adding moves_left, reusing _pseudo/attacked/in_check — the other ~40 chess variants untouched. Standard 8×8 chess render for all three._
| Game | Anchor | Status |
|---|---|---|
| Monster Chess #214 | White = K + 4 pawns (c2-f2) moves TWICE/turn vs Black's full army once; win by KING CAPTURE (win-as-event). Crux (independently verified): White may move through check (no self-check filter); Black moves filtered so its king isn't capturable-in-2 by White (_white_can_capture_bk_in_2). Verified vs Wikipedia+playstrategy. | **done → main** (browser-verified setup + 2-move flow) |
| Progressive Chess #215 | Italian scacchi progressivi — turn N has N moves (W1/B2/W3/...). Check allowed ONLY on the series' last move; escape-on-first; progressive mate falls out. PState adds moves_left+turn_no. Insufficient-material draw disabled. Verified vs Wikipedia+chessvariants; turn structure 1/2/3 confirmed. | **done → main** (standard render; multi-move flow = Monster's, verified) |
| Marseillais Chess #216 | Balanced (Bruce/Fischer) — 2 moves/turn, White's first turn = 1. Giving check ENDS the turn (forfeits 2nd move); own king safe after every sub-move; escape-on-first. MState adds moves_left + ep-across-turn lists. Verified vs Wikipedia; turn structure 1/2/2 confirmed. | **done → main** (standard render; multi-move flow verified) |

## Batch 57 — coverage vs playabstractgames.com + Reddit requests (2026-07-01, Erik-directed)
_Erik: a Reddit post highlighted playabstractgames.com (19 games) + comments requesting Tak & Ponte del Diavolo. Coverage check: we already covered 18/19; **Tak already exists** (the Reddit gripe was their site's, not ours — but it exposed OUR search bug, fixed below). Only gap was King's Valley. Built both requested/gap games. Also fixed the game-search ranking._
| Item | Detail | Status |
|---|---|---|
| GamePicker search ranking | Search did a flat substring match over name+category+desc+tags, no ranking → exact name ("Tak") buried under "s-tak-ing"/"at-tak". Added relevance() (exact name 1000 > prefix 900 > word-prefix 800 > substring 700 > tag 600/500/400 > category 250 > desc 100); searching now shows a flat best-first list, browse mode keeps category groups. Browser-verified ("Tak"→Tak first, "Hex"→Hex first). | **done → main + deployed** |
| King's Valley #217 | Kanare Kato 5×5 (closes the last playabstractgames gap). 1 King + 4 Soldiers/side, maximal-slide movement (must go to obstacle, no mid-stops), win = King to center; only King may stop on center (slides through otherwise, per Ludii/logygames); opening move must be a Soldier; trapped-King loss. Distinct from jeson_mor. Square 5×5 + center tint. | **done → main** (browser-verified) |
| Ponte del Diavolo #218 | Martin Ebel 10×10 island/bridge territory (Reddit-requested). Place 2 tiles OR 1 bridge; island = exactly 4 orthog-connected (never 5+, never same-colour diagonal touch); bridges (orth/diag 1-gap or knight 2-gap, no crossing, ≤1/tile) connect islands into groups scoring triangular numbers (1/3/6/10...). Two-tile turn = 2 same-player sub-moves. Bridges via board.overlay (TwixT format), islands via tints. Pie-rule omitted (documented). Verified vs official rulebook. | **done → main** (browser-verified board+tiles; bridge overlay = proven TwixT primitive) |

**Next-wave queue remaining (dedup-verified free):** picaria (CLONE RISK — 3-men version = existing Tapatan; only build a distinct 13-point Zuni variant), latrunculi, nard, jul_gonu, yonin_shogi (4-player, >2-seat render risk). NOTE: progressive/marseillais/monster chess need multi-move-per-turn — the engine CAN keep to_move across sub-moves (Backgammon does this), so verify the ChessLike check interaction before assigning. NOTE: progressive/marseillais/monster chess need multi-move-per-turn handling (verify the engine supports it before assigning); latrunculi/picaria have custom-render or clone-adjacency risk (dedup + browser-verify); yonin_shogi is 4-player (>2-seat render risk). AVOID clone-adjacent hunt/race variants.

## Needs human (escalations)

_(none blocking — the unattended distinct-pool is drained (25 distinct games shipped earlier this session). **Render-primitive phase (option 2) — 5 games shipped:** Tsuro (9th primitive path-tiles) + Hive (boardless cluster, composed) + Trax (10th primitive colour-track-tiles + growing board) + Pylos (offset pyramid, composed) + Octi (11th primitive directional-prongs) — all 4 render-special games Erik named done PLUS Octi; **3 new primitives added** (path-tiles #9, track-tiles #10, prongs #11), 2 composed existing ones. The render-primitive seam is now THIN — most remaining famous abstracts reuse already-shipped primitives. Candidates if continuing option 2: Tantrix (hex track-tiles, ~Trax-on-hex w/ 3 colours — would extend board.tracks to hex), Continuo, Metro (path-tiles). Otherwise the richer remaining seam is FOCUSED BUILDS warranting Erik's input — **Bao** (the marquee mancala, complex namua/mtaji), **Tamerlane** (huge medieval), **Chu Shogi** (12×12). Recommend Erik pick a direction (more option-2 tile games, a focused build, or call it). The two earlier non-blocking FYIs still stand: Two earlier non-blocking FYIs also stand: (1) the existing committed `pente` lacks a selftest and defaults to FREE opening rather than the standard centre-opening (a future upgrade could add the authentic `opening` option + a selftest, KEEPING the hard ply-cap since Pente can loop via captures); (2) Ultima's immobilizer/chameleon freeze-paradox resolution is a documented MacKay-cited interpretation — if you prefer a different convention for that deep edge case, it's a small tweak.)_

## Blocked on a capability
_(tracked in `GAME_BACKLOG.md` — drops, stacking, territory scoring, point-and-line, >2-seat)_
