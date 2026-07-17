# Ludus Latrunculorum

The Roman "game of little soldiers" (latrunculi). **Rules as reconstructed by
Ulrich Schädler (1994/2001), in the playable form published by the Locus Ludi
project (University of Fribourg, ERC #741520)** — this module implements the
Locus Ludi rules leaflet (its "Seneca" and "Piso" variants) verbatim, with the
interpretations listed at the end.

Two players, **8×8 board**, empty at the start. **20 counters each** (leaflet;
16 or 24 may be agreed instead per Schädler 2001 — the *Counters per player*
option). White (the first player) plays first.

## Phase 1 — Placement ("vagi")

Players take turns placing **one counter** on any vacant square until all
counters are placed. **No captures are made in this phase** — sandwiches formed
by placement do not trap anything. (That the game opens with free placement on
an empty board is the leaflet's reading of the *Laus Pisonis*.)

## Phase 2 — Movement ("ordinarii")

### Seneca variant (default)

On your turn:

1. **Forced removal.** If any enemy counters you trapped earlier are still
   trapped, you **must first remove exactly one of them** (your choice which)
   — click the trapped counter. Only one removal per turn; further trapped
   counters wait for your following turns.
2. **Move one free counter**, either
   - one step orthogonally to an adjacent vacant square, or
   - a draughts-style **leap**: jump a single orthogonally adjacent counter
     **of your own colour**, landing on the vacant square directly beyond.
     Multiple leaps may be chained in one move (`a>b>c`); a leap path never
     revisits a square. Leaps never capture by themselves.

**Trapping (custodial).** If your move ends with an enemy counter enclosed
between two of your free counters on opposite orthogonal sides — or, for a
counter on a corner square, on the two squares orthogonally adjacent to the
corner — that counter becomes ***incitus***: trapped ("flipped"), but still on
the board. An incitus is completely passive: it **cannot move and cannot serve
as a trapping guard**. One move may trap several counters at once; you then
remove one per turn (rule 1 above).

**Freeing (Seneca, *Letters* 117.30).** A trapped counter is **immediately set
free** if either of its two guards is itself trapped — and likewise if a guard
leaves its square. A freed counter moves and traps normally again.

**No suicide.** You may freely move a counter between two enemy counters; it
is not trapped by your own move.

**No shuttling.** You may not move the same counter straight back — i.e. a
move that exactly reverses your own previous move is illegal.

### Piso variant (option)

As above, except: **no leaps** (counters only step one square orthogonally),
and enclosure captures **immediately** — the trapped counter (or counters; all
trapped by one move are removed together) leaves the board at once. There is
no incitus state and no removal step.

## End of the game

The game ends when a player is **reduced to one counter**, or when the player
to move is **blockaded** (no legal move at all). **The player who captured the
most counters wins**; equal captures is a draw. (Backstop for online play: 120
consecutive movement plies without a trap or capture, or 600 movement plies in
total, end the game with the same most-captures scoring.)

## Interpretations documented (this implementation)

The leaflet is the source of truth. Where it is silent or another encoding
differs, this module does the following:

- **Leaps jump own-colour counters only** (leaflet: "leap over a single
  counter of his own colour"). Ludii's Locus Ludi Seneca encoding additionally
  allows leaping a *trapped enemy* counter, and its Schädler 1994/2001
  encodings allow leaping *any* occupied square — the leaflet wins; noted here
  for the record.
- A leap may jump your own counter whether it is free **or trapped** (the
  leaflet does not qualify "of his own colour"; Ludii agrees). Being jumped is
  not "helping to capture".
- Trapping and freeing are evaluated **at the final landing square** of a move
  (a multi-leap traps/frees only where it ends), per the leaflet's worked
  figure C (a leap whose landing traps a counter).
- **Freeing on guard departure**: the leaflet states freeing when a guard is
  trapped and conditions removal on "his two surrounding stones themselves
  [being] still free"; we also free the victim if a guard leaves its square
  (Ludii's Locus Ludi encoding does the same). Consequently every surviving
  incitus always has both guards standing free, so the removal proviso is
  automatically satisfied.
- **No shuttling** ("multiple moves back and forth of the same counter are not
  allowed") is implemented as *no immediate undo*: you may not exactly reverse
  your own previous move. Ludii uses full positional no-repetition instead.
- **Turn order** is unspecified in the leaflet: White places first and also
  makes the first move of phase 2 (placement alternates strictly, so Black
  places last).
- **Ties**: the leaflet says "the player who captured most counters is the
  winner" and is silent on equal captures; a blockade or cap with equal
  captures is an honest **draw**. (Ludii's encoding awards ties to Player 2 —
  an encoding artifact we do not follow.)
- **Piso and leaps**: the Piso sheet's movement rule is step-only (no leap
  sentence); its figure caption C still mentions a leap because the figure
  strip is carried over from the Seneca sheet. Ludii's Piso encoding likewise
  has no leap. This module's Piso variant has no leaps.
- **No "dux"/officer piece.** Reconstructions with a distinguished piece
  (Kowalski, Bell) rest on thin evidence and are not part of the Schädler /
  Locus Ludi ruleset; deliberately not implemented.
- The Greek *petteia/polis* under its common reading (step movement, custodial
  capture, no placement phase peculiarities) is mechanically a subset of this
  game; we deliberately do not ship it as a separate package.

## Sources

- Locus Ludi rules leaflet: *LUDUS LATRUNCULORUM — The game of little
  soldiers* (Seneca and Piso variants),
  [locusludi.ch](https://locusludi.ch/wp-content/uploads/2022/08/LUDUS-LATRUNCULORUM_rules_GB.pdf).
  Its evidence: Varro *De lingua Latina* X 22 (the grid); *Laus Pisonis*
  (open-board placement); Isidore of Seville, *Etymologies* XVIII 67 (the
  terms *vagus*, *ordinarius*, *incitus*); Martial *Epigrams* XIV 17 and Ovid
  *Tristia* II 478, *Art of Love* III 358 (capture by two-sided enclosure);
  Seneca, *Letters* 117.30 (a captured counter can be set free).
- Ulrich Schädler, "Latrunculi — ein verlorenes strategisches Brettspiel der
  Römer", in *Homo Ludens IV*, Salzburg 1994, p. 47–67.
- Ulrich Schädler, "Latrunculi — a forgotten Roman game of strategy
  reconstructed", *Abstract Games Magazine* 7, 2001, p. 10–11.
- Ludii's *Ludus Latrunculorum* encodings (Schädler 1994/2001, Locus Ludi
  Seneca/Piso) were used as a cross-check only; divergences noted above.
