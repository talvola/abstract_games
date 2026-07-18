"""Dragonchess — Gary Gygax, Dragon Magazine #100 (August 1985).

A three-dimensional chess variant played on THREE stacked 8x12 boards
(12 files a-l, 8 ranks 1-8). The pieces are characters and monsters from the
Dungeons & Dragons setting. A Recognized Chess Variant.

Rules transcribed from the standard reference:
  chessvariants.com/3d.dir/dragonchess.html
    (Edward Jackman's description, edited by Hans Bodlaender; it resolves the
     ambiguities/typos in Gygax's original) + Wikipedia "Dragonchess".
See rules.md for the full writeup and every documented interpretation.

COORDINATES / IDS
  A cell is (level, file, rank):
    * level: 1 = SKY (top board), 2 = GROUND (middle), 3 = UNDERWORLD (bottom).
    * file : 0..11  (a..l)
    * rank : 0..7   (1..8)
  The cell-id STRING is "level,col,row"  ==  f"{level},{file},{rank}"
  (3-component, mirroring raumschach/alice_chess so the generic click-to-move
  UI works). A move string is "l,c,r>l2,c2,r2", plus "=H" for the Warrior's
  forced promotion to Hero.

  "directly above" (l,c,r) = (l-1,c,r);  "directly below" = (l+1,c,r).
  Sky is above Ground is above Underworld, so up = smaller level number.

PLAYERS
  Gold (UPPERCASE, player 0) moves first; home ranks 1-2.
  Scarlet (lowercase, player 1) moves second; home ranks 7-8.
  "Forward" = +rank for Gold, -rank for Scarlet.

PIECE LETTERS (Dragon = R to distinguish it from the Dwarf = D):
  Sky:        S Sylph   G Griffin   R Dragon
  Ground:     O Oliphant U Unicorn  H Hero  T Thief  C Cleric
              M Mage     K King      P Paladin  W Warrior
  Underworld: B Basilisk E Elemental D Dwarf

See rules.md for each piece's exact move on its home level and between levels,
the Dragon's "capture from afar", the Basilisk's freezing, the Sylph's
return-home, and promotion/check/draw rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

GOLD, SCARLET = 0, 1
NFILE, NRANK = 12, 8
PLY_CAP = 400
NOPROGRESS_CAP = 100          # plies without a capture / Warrior move -> draw

# Gygax's published relative values (King = 0 / royal).
VALUE = {"K": 0.0, "M": 11.0, "P": 10.0, "C": 9.0, "R": 8.0, "G": 5.0,
         "O": 5.0, "H": 4.5, "T": 4.0, "E": 4.0, "B": 3.0, "U": 2.5,
         "D": 2.0, "S": 1.0, "W": 1.0}

# ---------------------------------------------------------------- geometry ----
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
KING8 = ORTHO + DIAG
KNIGHT = [(1, 2), (1, -2), (-1, 2), (-1, -2),
          (2, 1), (2, -1), (-2, 1), (-2, -1)]
ZEBRA = [(2, 3), (2, -3), (-2, 3), (-2, -3),
         (3, 2), (3, -2), (-3, 2), (-3, -2)]

# Paladin's board-to-board 3-D knight: |components| are a permutation of (2,1,0)
# with a non-zero level change.
PALADIN_3D = ([(dl, dc, dr) for dl in (-1, 1)
               for (dc, dr) in ((2, 0), (-2, 0), (0, 2), (0, -2))]
              + [(dl, dc, dr) for dl in (-2, 2)
                 for (dc, dr) in ((1, 0), (-1, 0), (0, 1), (0, -1))])

# The six home cells a friendly Sylph occupied at the start (level 1).
GOLD_HOME = frozenset((1, f, 1) for f in (0, 2, 4, 6, 8, 10))     # rank 2
SCAR_HOME = frozenset((1, f, 6) for f in (0, 2, 4, 6, 8, 10))     # rank 7


def _inb(l, c, r):
    return 1 <= l <= 3 and 0 <= c < NFILE and 0 <= r < NRANK


def _fwd(owner):
    return 1 if owner == GOLD else -1


def _home(owner):
    return GOLD_HOME if owner == GOLD else SCAR_HOME


def _promo_row(owner):
    return NRANK - 1 if owner == GOLD else 0


def _enemy(p):
    return 1 - p


# ------------------------------------------------------------------- setup ----
def _setup():
    p = {}

    def put(owner, level, file, rank, letter):
        p[(level, file, rank)] = (owner, letter)

    for owner in (GOLD, SCARLET):
        # For Gold: back rank = 0 (rank 1), forward pawn rank = 1 (rank 2).
        # For Scarlet: mirror to ranks 7 (=6) / 8 (=7) -> pawn rank 6, back 7.
        if owner == GOLD:
            back, paw = 0, 1
        else:
            back, paw = 7, 6

        # --- SKY (level 1) ---
        for f in (0, 2, 4, 6, 8, 10):          # Sylphs on the pawn rank
            put(owner, 1, f, paw, "S")
        put(owner, 1, 2, back, "G")            # Griffins c / k
        put(owner, 1, 10, back, "G")
        put(owner, 1, 6, back, "R")            # Dragon g

        # --- GROUND (level 2) ---
        ground_back = ["O", "U", "H", "T", "C", "M",
                       "K", "P", "T", "H", "U", "O"]
        for f in range(NFILE):
            put(owner, 2, f, back, ground_back[f])
            put(owner, 2, f, paw, "W")         # Warriors on the pawn rank

        # --- UNDERWORLD (level 3) ---
        for f in (1, 3, 5, 7, 9, 11):          # Dwarves on the pawn rank
            put(owner, 3, f, paw, "D")
        put(owner, 3, 2, back, "B")            # Basilisks c / k
        put(owner, 3, 10, back, "B")
        put(owner, 3, 6, back, "E")            # Elemental g
    return p


# ------------------------------------------------------------------ freeze ----
def _frozen(pieces):
    """Cells on the ground board holding a piece frozen by an ENEMY Basilisk
    directly below it (underworld).  Frozen pieces cannot move and exert no
    power (see rules.md)."""
    fr = set()
    for (l, c, r), (o, let) in pieces.items():
        if l == 2:
            below = pieces.get((3, c, r))
            if below is not None and below[1] == "B" and below[0] != o:
                fr.add((l, c, r))
    return fr


# ------------------------------------------------------ pseudo-move helpers ---
def _slide(pieces, level, c, r, dirs, owner, maxstep=None):
    """Yield reachable cells (empty + first enemy) for a same-level slider."""
    for dc, dr in dirs:
        nc, nr, step = c + dc, r + dr, 1
        while _inb(level, nc, nr) and (maxstep is None or step <= maxstep):
            occ = pieces.get((level, nc, nr))
            if occ is None:
                yield (level, nc, nr)
            else:
                if occ[0] != owner:
                    yield (level, nc, nr)
                break
            nc += dc
            nr += dr
            step += 1


def _piece_moves(pieces, frozen, fpos, owner, letter):
    """Yield (to_level, to_col, to_row, promo, remote) pseudo-moves.

    remote=True is the Dragon's capture-from-afar (it does NOT leave fpos).
    Does not filter for leaving one's own King in check."""
    fl, fc, fr = fpos
    fwd = _fwd(owner)

    def land(l, c, r):
        """move-or-capture onto (l,c,r)? (empty or enemy, in-board)."""
        if not _inb(l, c, r):
            return False
        occ = pieces.get((l, c, r))
        return occ is None or occ[0] != owner

    def empty(l, c, r):
        return _inb(l, c, r) and pieces.get((l, c, r)) is None

    def enemy(l, c, r):
        occ = pieces.get((l, c, r))
        return _inb(l, c, r) and occ is not None and occ[0] != owner

    if letter == "S":                                   # Sylph
        if fl == 1:
            for dc in (-1, 1):                          # quiet diagonal fwd
                if empty(1, fc + dc, fr + fwd):
                    yield (1, fc + dc, fr + fwd, None, False)
            if enemy(1, fc, fr + fwd):                  # capture ahead
                yield (1, fc, fr + fwd, None, False)
            if enemy(2, fc, fr):                        # capture straight down
                yield (2, fc, fr, None, False)
        elif fl == 2:                                   # only non-cap return up
            if empty(1, fc, fr):
                yield (1, fc, fr, None, False)
            for hc in _home(owner):
                if hc != (1, fc, fr) and pieces.get(hc) is None:
                    yield (hc[0], hc[1], hc[2], None, False)

    elif letter == "G":                                 # Griffin
        if fl == 1:
            for dc, dr in ZEBRA:
                if land(1, fc + dc, fr + dr):
                    yield (1, fc + dc, fr + dr, None, False)
            for dc, dr in DIAG:                         # top -> ground
                if land(2, fc + dc, fr + dr):
                    yield (2, fc + dc, fr + dr, None, False)
        elif fl == 2:
            for dc, dr in DIAG:                         # 1 diagonal on ground
                if land(2, fc + dc, fr + dr):
                    yield (2, fc + dc, fr + dr, None, False)
            for dc, dr in DIAG:                         # ground -> top
                if land(1, fc + dc, fr + dr):
                    yield (1, fc + dc, fr + dr, None, False)

    elif letter == "R":                                 # Dragon (sky only)
        for cell in _slide(pieces, 1, fc, fr, DIAG, owner):   # Bishop
            yield (cell[0], cell[1], cell[2], None, False)
        for dc, dr in ORTHO:                            # + King orthogonal step
            if land(1, fc + dc, fr + dr):
                yield (1, fc + dc, fr + dr, None, False)
        for dc, dr in [(0, 0)] + ORTHO:                 # capture from afar
            if enemy(2, fc + dc, fr + dr):
                yield (2, fc + dc, fr + dr, None, True)

    elif letter == "O":                                 # Oliphant = Rook
        for cell in _slide(pieces, 2, fc, fr, ORTHO, owner):
            yield (cell[0], cell[1], cell[2], None, False)

    elif letter == "U":                                 # Unicorn = Knight
        for dc, dr in KNIGHT:
            if land(2, fc + dc, fr + dr):
                yield (2, fc + dc, fr + dr, None, False)

    elif letter == "H":                                 # Hero
        if fl == 2:
            for dc, dr in DIAG:                         # 1 diagonal
                if land(2, fc + dc, fr + dr):
                    yield (2, fc + dc, fr + dr, None, False)
            for dc, dr in DIAG:                         # 2 diagonal (jumps)
                if land(2, fc + 2 * dc, fr + 2 * dr):
                    yield (2, fc + 2 * dc, fr + 2 * dr, None, False)
            for dc, dr in DIAG:                         # to top / bottom
                if land(1, fc + dc, fr + dr):
                    yield (1, fc + dc, fr + dr, None, False)
                if land(3, fc + dc, fr + dr):
                    yield (3, fc + dc, fr + dr, None, False)
        else:                                           # on top or bottom
            for dc, dr in DIAG:                         # return to ground
                if land(2, fc + dc, fr + dr):
                    yield (2, fc + dc, fr + dr, None, False)

    elif letter == "T":                                 # Thief = Bishop
        for cell in _slide(pieces, 2, fc, fr, DIAG, owner):
            yield (cell[0], cell[1], cell[2], None, False)

    elif letter == "C":                                 # Cleric
        for dc, dr in KING8:
            if land(fl, fc + dc, fr + dr):
                yield (fl, fc + dc, fr + dr, None, False)
        if fl > 1 and land(fl - 1, fc, fr):
            yield (fl - 1, fc, fr, None, False)
        if fl < 3 and land(fl + 1, fc, fr):
            yield (fl + 1, fc, fr, None, False)

    elif letter == "M":                                 # Mage
        if fl == 2:
            for cell in _slide(pieces, 2, fc, fr, KING8, owner):   # Queen
                yield (cell[0], cell[1], cell[2], None, False)
            if land(1, fc, fr):
                yield (1, fc, fr, None, False)
            if land(3, fc, fr):
                yield (3, fc, fr, None, False)
        else:                                           # top or bottom
            for dc, dr in ORTHO:
                if land(fl, fc + dc, fr + dr):
                    yield (fl, fc + dc, fr + dr, None, False)
            if fl == 1:
                if land(2, fc, fr):
                    yield (2, fc, fr, None, False)
                if empty(2, fc, fr) and land(3, fc, fr):
                    yield (3, fc, fr, None, False)
            else:                                       # fl == 3
                if land(2, fc, fr):
                    yield (2, fc, fr, None, False)
                if empty(2, fc, fr) and land(1, fc, fr):
                    yield (1, fc, fr, None, False)

    elif letter == "K":                                 # King
        if fl == 2:
            for dc, dr in KING8:
                if land(2, fc + dc, fr + dr):
                    yield (2, fc + dc, fr + dr, None, False)
            if land(1, fc, fr):
                yield (1, fc, fr, None, False)
            if land(3, fc, fr):
                yield (3, fc, fr, None, False)
        else:                                           # sitting duck
            if land(2, fc, fr):
                yield (2, fc, fr, None, False)

    elif letter == "P":                                 # Paladin
        if fl == 2:
            for dc, dr in KING8:
                if land(2, fc + dc, fr + dr):
                    yield (2, fc + dc, fr + dr, None, False)
            for dc, dr in KNIGHT:
                if land(2, fc + dc, fr + dr):
                    yield (2, fc + dc, fr + dr, None, False)
        else:
            for dc, dr in KING8:
                if land(fl, fc + dc, fr + dr):
                    yield (fl, fc + dc, fr + dr, None, False)
        for dl, dc, dr in PALADIN_3D:                   # board-to-board
            if land(fl + dl, fc + dc, fr + dr):
                yield (fl + dl, fc + dc, fr + dr, None, False)

    elif letter == "W":                                 # Warrior (ground only)
        pr = _promo_row(owner)
        if empty(2, fc, fr + fwd):                      # quiet forward
            promo = "H" if fr + fwd == pr else None
            yield (2, fc, fr + fwd, promo, False)
        for dc in (-1, 1):                              # capture diagonal fwd
            if enemy(2, fc + dc, fr + fwd):
                promo = "H" if fr + fwd == pr else None
                yield (2, fc + dc, fr + fwd, promo, False)

    elif letter == "B":                                 # Basilisk (bottom only)
        for dc in (-1, 0, 1):                           # forward move/capture
            if land(3, fc + dc, fr + fwd):
                yield (3, fc + dc, fr + fwd, None, False)
        if empty(3, fc, fr - fwd):                      # straight back (quiet)
            yield (3, fc, fr - fwd, None, False)

    elif letter == "E":                                 # Elemental
        if fl == 3:
            for cell in _slide(pieces, 3, fc, fr, ORTHO, owner, maxstep=2):
                yield (cell[0], cell[1], cell[2], None, False)
            for dc, dr in DIAG:                         # 1 diagonal (quiet)
                if empty(3, fc + dc, fr + dr):
                    yield (3, fc + dc, fr + dr, None, False)
            for dc, dr in ORTHO:                        # bottom -> ground
                if empty(3, fc + dc, fr + dr) and land(2, fc + dc, fr + dr):
                    yield (2, fc + dc, fr + dr, None, False)
        elif fl == 2:                                   # ground -> bottom
            if empty(3, fc, fr):
                for dc, dr in ORTHO:
                    if land(3, fc + dc, fr + dr):
                        yield (3, fc + dc, fr + dr, None, False)

    elif letter == "D":                                 # Dwarf (bottom/ground)
        for dc in (-1, 1):                              # capture diagonal fwd
            if enemy(fl, fc + dc, fr + fwd):
                yield (fl, fc + dc, fr + fwd, None, False)
        if empty(fl, fc, fr + fwd):                     # quiet forward
            yield (fl, fc, fr + fwd, None, False)
        for dc in (-1, 1):                              # quiet lateral
            if empty(fl, fc + dc, fr):
                yield (fl, fc + dc, fr, None, False)
        if fl == 3:                                     # up-capture to ground
            if enemy(2, fc, fr):
                yield (2, fc, fr, None, False)
        elif fl == 2:                                   # non-cap down to bottom
            if empty(3, fc, fr):
                yield (3, fc, fr, None, False)


# --------------------------------------------------------------- attacks -----
def _control(pieces, fpos, owner, letter):
    """Yield cells this piece ATTACKS (could capture on).  Used for check."""
    fl, fc, fr = fpos
    fwd = _fwd(owner)

    def onb(l, c, r):
        return _inb(l, c, r)

    def empty(l, c, r):
        return _inb(l, c, r) and pieces.get((l, c, r)) is None

    if letter == "S":
        if fl == 1:
            if onb(1, fc, fr + fwd):
                yield (1, fc, fr + fwd)
            if onb(2, fc, fr):
                yield (2, fc, fr)
        # sylph on ground has no capture

    elif letter == "G":
        if fl == 1:
            for dc, dr in ZEBRA:
                if onb(1, fc + dc, fr + dr):
                    yield (1, fc + dc, fr + dr)
            for dc, dr in DIAG:
                if onb(2, fc + dc, fr + dr):
                    yield (2, fc + dc, fr + dr)
        elif fl == 2:
            for dc, dr in DIAG:
                if onb(2, fc + dc, fr + dr):
                    yield (2, fc + dc, fr + dr)
                if onb(1, fc + dc, fr + dr):
                    yield (1, fc + dc, fr + dr)

    elif letter == "R":
        for dc, dr in DIAG:                             # Bishop control
            nc, nr = fc + dc, fr + dr
            while _inb(1, nc, nr):
                yield (1, nc, nr)
                if pieces.get((1, nc, nr)) is not None:
                    break
                nc += dc
                nr += dr
        for dc, dr in ORTHO:
            if onb(1, fc + dc, fr + dr):
                yield (1, fc + dc, fr + dr)
        for dc, dr in [(0, 0)] + ORTHO:                 # capture-from-afar zone
            if onb(2, fc + dc, fr + dr):
                yield (2, fc + dc, fr + dr)

    elif letter == "O":
        for dc, dr in ORTHO:
            nc, nr = fc + dc, fr + dr
            while _inb(2, nc, nr):
                yield (2, nc, nr)
                if pieces.get((2, nc, nr)) is not None:
                    break
                nc += dc
                nr += dr

    elif letter == "U":
        for dc, dr in KNIGHT:
            if onb(2, fc + dc, fr + dr):
                yield (2, fc + dc, fr + dr)

    elif letter == "H":
        if fl == 2:
            for dc, dr in DIAG:
                if onb(2, fc + dc, fr + dr):
                    yield (2, fc + dc, fr + dr)
                if onb(2, fc + 2 * dc, fr + 2 * dr):
                    yield (2, fc + 2 * dc, fr + 2 * dr)
                if onb(1, fc + dc, fr + dr):
                    yield (1, fc + dc, fr + dr)
                if onb(3, fc + dc, fr + dr):
                    yield (3, fc + dc, fr + dr)
        else:
            for dc, dr in DIAG:
                if onb(2, fc + dc, fr + dr):
                    yield (2, fc + dc, fr + dr)

    elif letter == "T":
        for dc, dr in DIAG:
            nc, nr = fc + dc, fr + dr
            while _inb(2, nc, nr):
                yield (2, nc, nr)
                if pieces.get((2, nc, nr)) is not None:
                    break
                nc += dc
                nr += dr

    elif letter == "C":
        for dc, dr in KING8:
            if onb(fl, fc + dc, fr + dr):
                yield (fl, fc + dc, fr + dr)
        if fl > 1:
            yield (fl - 1, fc, fr)
        if fl < 3:
            yield (fl + 1, fc, fr)

    elif letter == "M":
        if fl == 2:
            for dc, dr in KING8:
                nc, nr = fc + dc, fr + dr
                while _inb(2, nc, nr):
                    yield (2, nc, nr)
                    if pieces.get((2, nc, nr)) is not None:
                        break
                    nc += dc
                    nr += dr
            yield (1, fc, fr)
            yield (3, fc, fr)
        else:
            for dc, dr in ORTHO:
                if onb(fl, fc + dc, fr + dr):
                    yield (fl, fc + dc, fr + dr)
            if fl == 1:
                yield (2, fc, fr)
                if empty(2, fc, fr):
                    yield (3, fc, fr)
            else:
                yield (2, fc, fr)
                if empty(2, fc, fr):
                    yield (1, fc, fr)

    elif letter == "K":
        if fl == 2:
            for dc, dr in KING8:
                if onb(2, fc + dc, fr + dr):
                    yield (2, fc + dc, fr + dr)
            yield (1, fc, fr)
            yield (3, fc, fr)
        else:
            yield (2, fc, fr)

    elif letter == "P":
        if fl == 2:
            for dc, dr in KING8 + KNIGHT:
                if onb(2, fc + dc, fr + dr):
                    yield (2, fc + dc, fr + dr)
        else:
            for dc, dr in KING8:
                if onb(fl, fc + dc, fr + dr):
                    yield (fl, fc + dc, fr + dr)
        for dl, dc, dr in PALADIN_3D:
            if onb(fl + dl, fc + dc, fr + dr):
                yield (fl + dl, fc + dc, fr + dr)

    elif letter == "W":
        for dc in (-1, 1):
            if onb(2, fc + dc, fr + fwd):
                yield (2, fc + dc, fr + fwd)

    elif letter == "B":
        for dc in (-1, 0, 1):
            if onb(3, fc + dc, fr + fwd):
                yield (3, fc + dc, fr + fwd)

    elif letter == "E":
        if fl == 3:
            for dc, dr in ORTHO:
                nc, nr, step = fc + dc, fr + dr, 1
                while _inb(3, nc, nr) and step <= 2:
                    yield (3, nc, nr)
                    if pieces.get((3, nc, nr)) is not None:
                        break
                    nc += dc
                    nr += dr
                    step += 1
            for dc, dr in ORTHO:
                if empty(3, fc + dc, fr + dr) and onb(2, fc + dc, fr + dr):
                    yield (2, fc + dc, fr + dr)
        elif fl == 2:
            if empty(3, fc, fr):
                for dc, dr in ORTHO:
                    if onb(3, fc + dc, fr + dr):
                        yield (3, fc + dc, fr + dr)

    elif letter == "D":
        for dc in (-1, 1):
            if onb(fl, fc + dc, fr + fwd):
                yield (fl, fc + dc, fr + fwd)
        if fl == 3:
            yield (2, fc, fr)


def _attacked_slow(pieces, target, by, frozen=None):
    """Forward reference implementation: is `target` attacked by side `by`?
    Frozen pieces exert no power.  Kept as the cross-check oracle for the fast
    reverse scan below (see selftest)."""
    if frozen is None:
        frozen = _frozen(pieces)
    for pos, (o, let) in pieces.items():
        if o != by or pos in frozen:
            continue
        for cell in _control(pieces, pos, o, let):
            if cell == target:
                return True
    return False


def _attacked(pieces, target, by, frozen=None):
    """Fast reverse-attack scan: is `target` attacked by side `by`?

    Looks OUTWARD from `target` for an attacker of each type, instead of
    enumerating every enemy piece's full control set.  A frozen piece exerts no
    power but still BLOCKS sliders.  Verified identical to ``_attacked_slow``
    over random positions in the selftest."""
    if frozen is None:
        frozen = _frozen(pieces)
    pget = pieces.get
    tl, tc, tr = target
    fwd = _fwd(by)

    def hit(l, c, r, let):
        occ = pget((l, c, r))
        return (occ is not None and occ[0] == by and occ[1] == let
                and (l, c, r) not in frozen)

    def ray(level, dirs, let, maxstep=None):
        for dc, dr in dirs:
            nc, nr, step = tc + dc, tr + dr, 1
            while _inb(level, nc, nr) and (maxstep is None or step <= maxstep):
                occ = pget((level, nc, nr))
                if occ is not None:
                    if (occ[0] == by and occ[1] == let
                            and (level, nc, nr) not in frozen):
                        return True
                    break
                nc += dc
                nr += dr
                step += 1
        return False

    # --- Sylph ---
    if tl == 1 and hit(1, tc, tr - fwd, "S"):
        return True
    if tl == 2 and hit(1, tc, tr, "S"):
        return True

    # --- Warrior (ground) ---
    if tl == 2 and (hit(2, tc - 1, tr - fwd, "W") or hit(2, tc + 1, tr - fwd, "W")):
        return True

    # --- Basilisk (underworld) ---
    if tl == 3:
        for dc in (-1, 0, 1):
            if hit(3, tc - dc, tr - fwd, "B"):
                return True

    # --- Dwarf ---
    if tl in (2, 3):
        for dc in (-1, 1):
            if hit(tl, tc - dc, tr - fwd, "D"):
                return True
    if tl == 2 and hit(3, tc, tr, "D"):            # up-capture from below
        return True

    # --- Unicorn = Knight (ground) ---
    if tl == 2:
        for dc, dr in KNIGHT:
            if hit(2, tc - dc, tr - dr, "U"):
                return True

    # --- Griffin ---
    if tl == 1:
        for dc, dr in ZEBRA:
            if hit(1, tc - dc, tr - dr, "G"):
                return True
        for dc, dr in DIAG:                        # ground -> top
            if hit(2, tc - dc, tr - dr, "G"):
                return True
    elif tl == 2:
        for dc, dr in DIAG:
            if hit(1, tc - dc, tr - dr, "G"):      # top -> ground diag-below
                return True
            if hit(2, tc - dc, tr - dr, "G"):      # 1 diagonal same level
                return True

    # --- Hero ---
    if tl == 2:
        for dc, dr in DIAG:
            if (hit(2, tc - dc, tr - dr, "H") or hit(2, tc - 2 * dc, tr - 2 * dr, "H")
                    or hit(1, tc - dc, tr - dr, "H") or hit(3, tc - dc, tr - dr, "H")):
                return True
    else:                                          # top or bottom target
        for dc, dr in DIAG:
            if hit(2, tc - dc, tr - dr, "H"):
                return True

    # --- Cleric ---
    for dc, dr in KING8:
        if hit(tl, tc - dc, tr - dr, "C"):
            return True
    if tl > 1 and hit(tl - 1, tc, tr, "C"):
        return True
    if tl < 3 and hit(tl + 1, tc, tr, "C"):
        return True

    # --- King ---
    if tl == 2:
        for dc, dr in KING8:
            if hit(2, tc - dc, tr - dr, "K"):
                return True
        if hit(1, tc, tr, "K") or hit(3, tc, tr, "K"):
            return True
    else:
        if hit(2, tc, tr, "K"):
            return True

    # --- Paladin ---
    if tl == 2:
        for dc, dr in KING8 + KNIGHT:
            if hit(2, tc - dc, tr - dr, "P"):
                return True
    else:
        for dc, dr in KING8:
            if hit(tl, tc - dc, tr - dr, "P"):
                return True
    for dl, dc, dr in PALADIN_3D:
        if hit(tl - dl, tc - dc, tr - dr, "P"):
            return True

    # --- Dragon ---
    if tl == 1:
        if ray(1, DIAG, "R"):                      # Bishop
            return True
        for dc, dr in ORTHO:                        # King orthogonal step
            if hit(1, tc - dc, tr - dr, "R"):
                return True
    elif tl == 2:                                   # capture from afar
        for dc, dr in [(0, 0)] + ORTHO:
            if hit(1, tc - dc, tr - dr, "R"):
                return True

    # --- Oliphant = Rook / Thief = Bishop / Mage = Queen (ground) ---
    if tl == 2:
        if ray(2, ORTHO, "O") or ray(2, DIAG, "T") or ray(2, KING8, "M"):
            return True
        if hit(1, tc, tr, "M") or hit(3, tc, tr, "M"):
            return True
    elif tl == 1:                                   # Mage on top / from below
        for dc, dr in ORTHO:
            if hit(1, tc - dc, tr - dr, "M"):
                return True
        if hit(2, tc, tr, "M"):
            return True
        if pget((2, tc, tr)) is None and hit(3, tc, tr, "M"):
            return True
    elif tl == 3:                                   # Mage on bottom / from above
        for dc, dr in ORTHO:
            if hit(3, tc - dc, tr - dr, "M"):
                return True
        if hit(2, tc, tr, "M"):
            return True
        if pget((2, tc, tr)) is None and hit(1, tc, tr, "M"):
            return True

    # --- Elemental ---
    if tl == 3:
        if ray(3, ORTHO, "E", maxstep=2):
            return True
        for dc, dr in ORTHO:                        # ground -> bottom
            ec, er = tc - dc, tr - dr
            if pget((3, ec, er)) is None and hit(2, ec, er, "E"):
                return True
    elif tl == 2:                                   # bottom -> ground
        if pget((3, tc, tr)) is None:
            for dc, dr in ORTHO:
                if hit(3, tc - dc, tr - dr, "E"):
                    return True

    return False


def _king_pos(pieces, player):
    for pos, (o, let) in pieces.items():
        if o == player and let == "K":
            return pos
    return None


def _in_check(pieces, player, frozen=None):
    kp = _king_pos(pieces, player)
    if kp is None:
        return False
    return _attacked(pieces, kp, _enemy(player), frozen)


# ------------------------------------------------------------ apply / legal ---
def _apply(pieces, fpos, mv):
    tl, tc, tr, promo, remote = mv
    np = dict(pieces)
    if remote:                                          # Dragon stays put
        del np[(tl, tc, tr)]
        return np, True
    o, let = np.pop(fpos)
    captured = (tl, tc, tr) in np
    if promo:
        let = promo
    np[(tl, tc, tr)] = (o, let)
    return np, captured


def _legal(pieces, player):
    frozen = _frozen(pieces)
    out = []
    for pos, (o, let) in list(pieces.items()):
        if o != player or pos in frozen:
            continue
        for mv in _piece_moves(pieces, frozen, pos, player, let):
            np, _ = _apply(pieces, pos, mv)
            if not _in_check(np, player):
                out.append((pos, mv))
    return out


def _mstr(fpos, mv):
    fl, fc, fr = fpos
    tl, tc, tr, promo, remote = mv
    s = f"{fl},{fc},{fr}>{tl},{tc},{tr}"
    if promo:
        s += f"={promo}"
    return s


def _perft(pieces, player, depth):
    if depth == 0:
        return 1
    total = 0
    for fpos, mv in _legal(pieces, player):
        np, _ = _apply(pieces, fpos, mv)
        total += _perft(np, _enemy(player), depth - 1)
    return total


def _pos_key(pieces, to_move):
    parts = [f"{l}{c}{r}{o}{let}"
             for (l, c, r), (o, let) in sorted(pieces.items())]
    return "|".join(parts) + f"#{to_move}"


def _material(pieces):
    g = s = 0.0
    for (o, let) in pieces.values():
        if o == GOLD:
            g += VALUE[let]
        else:
            s += VALUE[let]
    return g, s


# --------------------------------------------------------------------- state --
@dataclass
class DragonState:
    pieces: dict = field(default_factory=dict)     # (l,c,r) -> (owner, letter)
    to_move: int = GOLD
    winner: Optional[int] = None
    draw: bool = False
    ply: int = 0
    noprog: int = 0
    seen: dict = field(default_factory=dict)
    last: Optional[tuple] = None                    # landing cell (l,c,r)


class Dragonchess(Game):
    uid = "dragonchess"
    name = "Dragonchess"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        pieces = _setup()
        s = DragonState(pieces=pieces, to_move=GOLD)
        s.seen = {_pos_key(pieces, GOLD): 1}
        return s

    def current_player(self, s):
        return s.to_move

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        return [_mstr(fpos, mv) for fpos, mv in _legal(s.pieces, s.to_move)]

    def apply_move(self, s, move, rng=None):
        if self.is_terminal(s):
            raise ValueError("game over")
        player = s.to_move
        chosen = None
        for fpos, mv in _legal(s.pieces, player):
            if _mstr(fpos, mv) == move:
                chosen = (fpos, mv)
                break
        if chosen is None:
            raise ValueError(f"illegal move {move!r}")
        fpos, mv = chosen
        moved_letter = s.pieces[fpos][1]
        new_pieces, captured = _apply(s.pieces, fpos, mv)
        opp = _enemy(player)

        progress = captured or moved_letter == "W"
        noprog = 0 if progress else s.noprog + 1
        ply = s.ply + 1
        seen = dict(s.seen)
        pk = _pos_key(new_pieces, opp)
        rep = seen.get(pk, 0) + 1
        seen[pk] = rep

        landing = (mv[0], mv[1], mv[2]) if not mv[4] else fpos
        ns = DragonState(pieces=new_pieces, to_move=opp, ply=ply,
                         noprog=noprog, seen=seen, last=landing)

        if not _legal(new_pieces, opp):
            if _in_check(new_pieces, opp):
                ns.winner = player                  # checkmate
            else:
                ns.draw = True                      # stalemate
            return ns
        if rep >= 3 or noprog >= NOPROGRESS_CAP or ply >= PLY_CAP:
            ns.draw = True
        return ns

    def is_terminal(self, s):
        return s.winner is not None or s.draw

    def returns(self, s):
        if s.winner == GOLD:
            return [1.0, -1.0]
        if s.winner == SCARLET:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s):
        import math
        g, sc = _material(s.pieces)
        v = math.tanh((g - sc) / 12.0)
        return [v, -v]

    # ----------------------------------------------------------- serialize ----
    def serialize(self, s):
        return {
            "pieces": {f"{l},{c},{r}": [o, let]
                       for (l, c, r), (o, let) in s.pieces.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "draw": s.draw,
            "ply": s.ply,
            "noprog": s.noprog,
            "seen": dict(s.seen),
            "last": (list(s.last) if s.last is not None else None),
        }

    def deserialize(self, d):
        pieces = {}
        for k, v in d["pieces"].items():
            l, c, r = (int(x) for x in k.split(","))
            pieces[(l, c, r)] = (int(v[0]), v[1])
        last = d.get("last")
        return DragonState(
            pieces=pieces,
            to_move=d["to_move"],
            winner=d.get("winner"),
            draw=d.get("draw", False),
            ply=d.get("ply", 0),
            noprog=d.get("noprog", 0),
            seen=dict(d.get("seen", {})),
            last=(tuple(last) if last is not None else None),
        )

    # ------------------------------------------------------------- notation ---
    def describe_move(self, s, move):
        head = move.split("=")
        promo = head[1] if len(head) > 1 else None
        frm, to = head[0].split(">")
        fl, fc, fr = (int(x) for x in frm.split(","))
        tl, tc, tr = (int(x) for x in to.split(","))
        occ = s.pieces.get((fl, fc, fr))
        letter = occ[1] if occ else "?"

        def sq(l, c, r):
            return f"{l}{'abcdefghijkl'[c]}{r + 1}"

        remote = letter == "R" and tl == 2
        if remote:
            return f"R{sq(fl, fc, fr)}*{sq(tl, tc, tr)}"    # capture from afar
        cap = "x" if (tl, tc, tr) in s.pieces else "-"
        prefix = "" if letter == "W" else letter
        out = f"{prefix}{sq(fl, fc, fr)}{cap}{sq(tl, tc, tr)}"
        if promo:
            out += f"={promo}"
        return out

    # ---------------------------------------------------------- presentation --
    def render(self, s, perspective=None):
        GAP = 1.5
        BH = NRANK + GAP                       # vertical block pitch
        light = "#e9d3b0"
        dark = "#a97c50"
        frozen = _frozen(s.pieces)

        cells = []
        tints = {}
        for l in (1, 2, 3):
            base_y = (3 - l) * BH              # sky highest, underworld lowest
            for c in range(NFILE):
                for r in range(NRANK):
                    ox = c
                    oy = base_y + r
                    pts = [[ox, oy], [ox + 1, oy],
                           [ox + 1, oy + 1], [ox, oy + 1]]
                    cid = f"{l},{c},{r}"
                    cells.append({"id": cid, "points": pts})
                    # near right corner (file l, rank 1) of each board is white
                    tints[cid] = light if (c + r) % 2 == 1 else dark

        icons = {"R": "dragon", "M": "wizard", "U": "unicorn", "P": "centaur"}
        pieces = []
        for (l, c, r), (o, let) in s.pieces.items():
            pc = {"cell": f"{l},{c},{r}", "owner": o, "label": let}
            if let in icons:
                pc["icon"] = icons[let]
            if (l, c, r) in frozen:
                pc["fill"] = "#7fbfff"        # frozen tint
            pieces.append(pc)

        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]},{s.last[2]}",
                               "kind": "last-move"})

        names = {GOLD: "Gold", SCARLET: "Scarlet"}
        if s.winner is not None:
            caption = f"{names[s.winner]} wins by checkmate"
        elif s.draw:
            caption = "Draw"
        else:
            caption = (f"{names[s.to_move]} to move  "
                       "(Sky / Ground / Underworld, top to bottom)")
            if _in_check(s.pieces, s.to_move, frozen):
                caption += " — CHECK"

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
