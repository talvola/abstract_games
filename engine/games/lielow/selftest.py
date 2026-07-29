"""Lielow correctness anchors (pure stdlib).

Covers, on hand-built positions and on random play:

* the OPENING — the exact starting array (eight height-1 stacks a side on ranks 2
  and 7, White to move, NEITHER player crowned) and its **46** legal moves, which
  is the number the AbstractPlay reference implementation reports;
* move generation cross-checked against an INDEPENDENT second formulation
  (scan all 64 squares and ask "is this square exactly h away on a queen line?"
  instead of stepping h in eight directions) over thousands of random positions;
* the movement rule itself — EXACTLY the stack's height, never less, never more;
  stacks JUMP (a blocked line does not stop them); no landing on your own stack;
* the height mechanic — +1 on an empty square, RESET TO 1 on a capture, no change
  when walking off the edge; heights are therefore capped at 8, and a height-8
  stack has no legal move but to leave the board;
* the crown — it moves to a *unique* tallest stack and otherwise STAYS PUT, it
  travels with its stack, it re-accedes for the VICTIM after a capture, and it is
  never revived once dead;
* both ways to lose — your crowned stack captured, or walked off the edge by you;
* **a decisive result outranks the ply counter** (a crown capture on the very ply
  the cap would fire still scores as a win), paired with a control showing the cap
  really does bite on that ply, so the assertion is not vacuous;
* termination — every one of 1,500 random games ended with a crown dead; none hit
  the ply cap and none was a draw; the longest ran 73 plies against a proven
  352-ply bound;
* move-string hygiene — the walk-off move is `"c,r>off"`, never a self-path
  `"c,r>c,r"`.  That is load-bearing for the web UI: the renderer routes a move
  whose ">"-segments are ALL cell ids to the board click handler, where a
  self-path fires on the second click of the same square — the instinctive
  "deselect" click — and in Lielow that click destroys a stack and can lose the
  game outright.  `"off"` is not a cell id, so the move becomes a labelled
  action button instead;
* no stalemate is possible (the right-most stack always has a move) — asserted
  directly on every position of random play, and the defensive fallback branch is
  exercised on a hand-built position that real play cannot reach;
* purity, and a LOSSLESS serialize round-trip (``deserialize(serialize(s)) == s``
  at the STATE level, plus the exact key set and a per-field mutation test — the
  weaker ``serialize(deserialize(d)) == d`` cannot see a field serialize drops
  entirely, and a dropped `king` or `ply` would break in-progress async matches,
  which round-trip through the database on every move);
* the render contract (stack heights, the crown label, cell ids) and the
  heuristic's shape at a forced MCTS rollout cutoff.

The full move-for-move differential against AbstractPlay's `gameslib` lives in
`_diff_ap.py` (manual, needs node).
"""
import json
import random
import sys
from dataclasses import fields as dc_fields, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.lielow.game import (  # noqa: E402
    DEAD, DIRS, NCELLS, NO_KING, PLY_CAP, SIZE, LState, Lielow,
    algebraic, cell_name, height, idx, owner, signed,
)

G = Lielow()


def cr(a):
    """'d5' -> (3, 4) — chess names, used only to keep test positions legible."""
    return (ord(a[0]) - ord("a"), int(a[1]) - 1)


def mk(white=(), black=(), crowns=(None, None), to_move=0, ply=0):
    """Build a position.  ``white``/``black`` are ("d4", height) pairs;
    ``crowns`` are chess names (or None for "not crowned yet")."""
    board = [0] * NCELLS
    for seat, lst in ((0, white), (1, black)):
        for name, h in lst:
            c, r = cr(name)
            board[idx(c, r)] = signed(seat, h)
    king = tuple(NO_KING if k is None else idx(*cr(k)) for k in crowns)
    return LState(board=tuple(board), king=king, to_move=to_move, ply=ply,
                  over=False, winner=None, last=None)


def off(name):
    """The move string that walks the stack on ``name`` (a chess name) off."""
    return f"{cell_name(idx(*cr(name)))}>off"


def targets(state, frm):
    """Destinations of every legal move out of ``frm`` (chess name), in chess
    names, with the literal "off" for the walk-off-the-board move."""
    src = cell_name(idx(*cr(frm)))
    out = set()
    for m in G.legal_moves(state):
        a, _, b = m.partition(">")
        if a == src:
            out.add("off" if b == "off"
                    else algebraic(idx(*(int(x) for x in b.split(",")))))
    return out


def gen_independent(board, seat):
    """A SECOND, deliberately different move generator: instead of stepping the
    stack's height in each of the eight directions, look at every square on the
    board and ask whether it lies exactly `h` away along a queen line.  Off-board
    availability is derived from the count of directions that leave the board."""
    out = set()
    for i in range(NCELLS):
        v = board[i]
        if v == 0 or owner(v) != seat:
            continue
        h = height(v)
        c, r = i % SIZE, i // SIZE
        for j in range(NCELLS):
            if j == i:
                continue
            dc, dr = j % SIZE - c, j // SIZE - r
            if (abs(dc), abs(dr)) not in ((h, 0), (0, h), (h, h)):
                continue
            t = board[j]
            if t == 0 or owner(t) != seat:
                out.add((i, j))
        if c - h < 0 or c + h >= SIZE or r - h < 0 or r + h >= SIZE:
            out.add((i, i))
    return out


def as_pairs(state):
    """Legal moves as (from_idx, to_idx); a walk-off is (i, i)."""
    out = set()
    for m in G.legal_moves(state):
        a, _, b = m.partition(">")
        i = idx(*(int(x) for x in a.split(",")))
        out.add((i, i) if b == "off"
                else (i, idx(*(int(x) for x in b.split(",")))))
    return out


def random_position(rng):
    """A plausible mid-game position: a few stacks a side at assorted heights."""
    cells = rng.sample(range(NCELLS), rng.randint(2, 14))
    board = [0] * NCELLS
    for k, i in enumerate(cells):
        board[i] = signed(k % 2, rng.randint(1, SIZE))
    king = []
    for seat in (0, 1):
        mine = [i for i in cells if board[i] and owner(board[i]) == seat]
        king.append(rng.choice(mine) if mine and rng.random() < 0.8 else NO_KING)
    return LState(board=tuple(board), king=tuple(king), to_move=rng.randint(0, 1),
                  ply=0, over=False, winner=None, last=None)


# --------------------------------------------------------------------------
def test_opening():
    s = G.initial_state()
    assert s.to_move == 0 and s.ply == 0 and not s.over and s.winner is None
    # Eight height-1 stacks a side, on the chess PAWN ranks (2 and 7).
    want = {}
    for c in range(SIZE):
        want[idx(c, 1)] = signed(0, 1)
        want[idx(c, SIZE - 2)] = signed(1, 1)
    got = {i: v for i, v in enumerate(s.board) if v}
    assert got == want, sorted(got.items())
    # NOBODY is crowned at the start: all eight stacks are tied at height 1, so
    # there is no *unique* tallest.  (The designers' rules place no crown until
    # after a move.)
    assert s.king == (NO_KING, NO_KING), s.king

    ms = G.legal_moves(s)
    assert len(ms) == len(set(ms)) == 46, len(ms)
    # ...and the exact set, derived by hand: an interior height-1 stack has 6
    # moves (its two horizontal neighbours are its own stacks); a2 and h2 have 4
    # plus the walk-off-the-edge move.
    hand = set()
    for c in range(SIZE):
        for dc, dr in DIRS:
            nc, nr = c + dc, 1 + dr
            if 0 <= nc < SIZE and 0 <= nr < SIZE and not (nr == 1):
                hand.add((idx(c, 1), idx(nc, nr)))
        if c in (0, SIZE - 1):
            hand.add((idx(c, 1), idx(c, 1)))
    assert as_pairs(s) == hand, sorted(as_pairs(s) ^ hand)
    assert targets(s, "a2") == {"a1", "a3", "b1", "b3", "off"}, targets(s, "a2")
    assert targets(s, "d2") == {"c1", "c3", "d1", "d3", "e1", "e3"}
    return len(ms)


def test_movegen_cross_check():
    rng = random.Random(4)
    n = 0
    for _ in range(4000):
        s = random_position(rng)
        assert as_pairs(s) == gen_independent(s.board, s.to_move)
        n += 1
    # ...and along real games, where the position is reachable rather than random
    for seed in range(40):
        r2 = random.Random(1000 + seed)
        s = G.initial_state()
        while not G.is_terminal(s):
            assert as_pairs(s) == gen_independent(s.board, s.to_move)
            n += 1
            s = G.apply_move(s, r2.choice(G.legal_moves(s)))
    return n


def test_movement():
    # EXACTLY the height, in a straight queen line.  A height-3 stack on d4
    # reaches only the 8 squares three away; d5/d6 (1 and 2 away) are not moves.
    s = mk(white=[("d4", 3)], black=[("h8", 1)], crowns=("d4", "h8"))
    assert targets(s, "d4") == {"a1", "a4", "a7", "d1", "d7", "g1", "g4", "g7"}
    # Stacks JUMP: filling the whole path leaves the move untouched.
    blocked = mk(white=[("d4", 3), ("d5", 1), ("d6", 1)],
                 black=[("e5", 1), ("f6", 1), ("h8", 1)], crowns=("d4", "h8"))
    assert "d7" in targets(blocked, "d4") and "g7" in targets(blocked, "d4")
    # ...but the LANDING square matters: your own stack blocks, an enemy is prey.
    own = mk(white=[("d4", 3), ("d7", 1)], black=[("g7", 2), ("h8", 1)],
             crowns=("d4", "h8"))
    t = targets(own, "d4")
    assert "d7" not in t and "g7" in t, t
    # Every direction is available (queenwise, both orthogonal and diagonal).
    lone = mk(white=[("d4", 1)], black=[("h8", 1)], crowns=("d4", "h8"))
    assert targets(lone, "d4") == {"c3", "c4", "c5", "d3", "d5", "e3", "e4", "e5"}


def test_off_the_board():
    # A height-1 stack in the interior cannot leave; on the rim it can.
    s = mk(white=[("d4", 1), ("a4", 1)], black=[("h8", 1)], crowns=("d4", "h8"))
    assert "off" not in targets(s, "d4")
    assert "off" in targets(s, "a4")
    # A height-8 stack can reach NOTHING on the board: leaving is its only move.
    s = mk(white=[("d4", 8)], black=[("h8", 1)], crowns=("d4", "h8"))
    assert targets(s, "d4") == {"off"}, targets(s, "d4")
    # 8 is therefore the ceiling: a stack can never grow past it.
    for h in range(1, SIZE + 1):
        for c in range(SIZE):
            for r in range(SIZE):
                name = f"{chr(97 + c)}{r + 1}"
                st = mk(white=[(name, h)])          # a lone stack, empty board
                # A stack may leave the board exactly when SOME queenwise ray of
                # length h clears an edge, which is this orthogonal disjunction.
                edge = (c - h < 0 or c + h >= SIZE or r - h < 0 or r + h >= SIZE)
                assert ("off" in targets(st, name)) == edge, (name, h)
                if h == SIZE:
                    assert targets(st, name) == {"off"}, (name, h)
    # Walking off removes the stack and does NOT change anything else.
    s = mk(white=[("a4", 1), ("d4", 3)], black=[("h8", 1)], crowns=("d4", "h8"))
    t = G.apply_move(s, off("a4"))
    assert t.board[idx(0, 3)] == 0
    assert t.board[idx(3, 3)] == signed(0, 3)      # the other stack is untouched
    assert not t.over


def test_height_changes():
    s = mk(white=[("d4", 3)], black=[("d7", 2), ("h8", 1)], crowns=("d4", "h8"))
    # empty landing square -> grow by one
    t = G.apply_move(s, "3,3>3,0")
    assert t.board[idx(3, 0)] == signed(0, 4) and t.board[idx(3, 3)] == 0
    # enemy landing square -> capture, and the MOVER RESETS TO 1
    t = G.apply_move(s, "3,3>3,6")
    assert t.board[idx(3, 6)] == signed(0, 1), t.board[idx(3, 6)]
    assert t.board[idx(3, 3)] == 0
    # the captured stack is gone from the game, whatever its height
    assert sum(1 for v in t.board if v) == 2


def test_crown():
    # The crown goes to the UNIQUE tallest stack...
    s = mk(white=[("a1", 1), ("b1", 1)], black=[("h8", 1)], crowns=(None, "h8"))
    t = G.apply_move(s, "0,0>0,1")                     # a1 grows to 2
    assert t.king[0] == idx(0, 1), t.king
    # ...and STAYS PUT when another stack ties it (BGA: "the king's identity does
    # NOT change in this situation").
    v = G.apply_move(mk(white=[("a2", 2), ("b1", 1)], black=[("h8", 1)],
                        crowns=("a2", "h8")), "1,0>1,1")   # b1 grows to 2: a tie
    assert v.board[idx(0, 1)] == signed(0, 2) and v.board[idx(1, 1)] == signed(0, 2)
    assert v.king[0] == idx(0, 1), "a tie must leave the crown where it was"
    # ...and the SAME tie with the crown on the OTHER of the two stacks.  Both
    # orders are needed: an implementation that simply takes the first stack it
    # finds at the maximum height passes one of them by luck.
    v2 = G.apply_move(mk(white=[("b2", 2), ("a1", 1)], black=[("h8", 1)],
                         crowns=("b2", "h8")), "0,0>0,1")  # a1 grows to 2: a tie
    assert v2.board[idx(0, 1)] == signed(0, 2) and v2.board[idx(1, 1)] == signed(0, 2)
    assert v2.king[0] == idx(1, 1), "a tie must leave the crown where it was"
    # A three-way tie, crown in the middle of the scan order, likewise.
    v3 = G.apply_move(mk(white=[("a1", 2), ("b1", 2), ("c1", 1)],
                         black=[("h8", 1)], crowns=("b1", "h8")), "2,0>2,1")
    assert v3.king[0] == idx(1, 0), v3.king
    # An uncrowned player facing a tie STAYS uncrowned.
    v4 = G.apply_move(mk(white=[("a1", 1), ("b1", 2)], black=[("h8", 1)],
                         crowns=(None, "h8")), "0,0>0,1")
    assert v4.king[0] == NO_KING, v4.king
    # ...but a strictly taller stack takes it.
    x = G.apply_move(replace(v, to_move=0), "1,1>1,3")
    assert x.board[idx(1, 3)] == signed(0, 3)          # b2 -> b4, height 3
    assert x.king[0] == idx(1, 3), x.king
    # The crown travels WITH its stack.  Note that the obvious form of this test
    # — move the crowned stack, watch the crown follow — is VACUOUS: the moved
    # stack usually ends up the unique tallest, so accession puts the crown back
    # on it even if the transfer was dropped entirely.  It only bites when the
    # position after the move has NO unique tallest, so accession is a no-op and
    # the transfer is the only thing carrying the crown.  Both landing kinds are
    # covered, because they are separate lines of code.
    y = mk(white=[("a2", 2), ("b1", 1)], black=[("h8", 1)], crowns=("a2", "h8"))
    z = G.apply_move(y, "0,1>0,3")
    assert z.king[0] == idx(0, 3)
    # (a) the crowned stack lands on an EMPTY square into a three-way tie.
    y = mk(white=[("a2", 2), ("b1", 3), ("c1", 3)], black=[("h8", 1)],
           crowns=("a2", "h8"))
    z = G.apply_move(y, "0,1>0,3")                     # a2 -> a4, now 3: a 3-way tie
    assert z.board[idx(0, 3)] == signed(0, 3)
    assert z.king[0] == idx(0, 3), "the crown must ride to a4, not stay on a2"
    # (b) the crowned stack CAPTURES, resetting to 1 into a tie at height 1.
    y = mk(white=[("a1", 4), ("e2", 1)], black=[("e1", 2), ("h8", 1)],
           crowns=("a1", "h8"))
    z = G.apply_move(y, "0,0>4,0")                     # a1 x e1, resets to 1: tie
    assert z.board[idx(4, 0)] == signed(0, 1)
    assert z.king[0] == idx(4, 0), "the crown must ride to e1, not stay on a1"
    # In both cases the failure mode is a crown pointing at an EMPTY square — an
    # uncapturable king and a board with no crown marker — so pin that directly
    # here, and as a standing invariant over real play (test_crown_is_on_a_stack).
    for w in (z, G.apply_move(y, "0,0>4,0")):
        assert w.board[w.king[0]] and owner(w.board[w.king[0]]) == 0, w.king
    # A capture RESETS the mover to 1, which can hand the crown to someone else.
    p = mk(white=[("a1", 3), ("b1", 2)], black=[("d1", 1), ("h8", 1)],
           crowns=("a1", "h8"))
    q = G.apply_move(p, "0,0>3,0")                     # a1 takes d1, resets to 1
    assert q.board[idx(3, 0)] == signed(0, 1)
    assert q.king[0] == idx(1, 0), "b1 (height 2) is now the unique tallest"
    # The VICTIM re-crowns too: removing their tallest promotes the next one.
    p = mk(white=[("a1", 4)], black=[("e1", 3), ("h1", 2), ("h8", 1)],
           crowns=("a1", "e1"))
    q = G.apply_move(p, "0,0>4,0")                     # white takes e1 (their crown)
    assert q.king[1] == DEAD and q.over and q.winner == 0
    p = mk(white=[("a1", 4)], black=[("e1", 3), ("h1", 2), ("h8", 1)],
           crowns=("a1", "h1"))                        # crown NOT on the tallest
    q = G.apply_move(p, "0,0>4,0")                     # take the taller, uncrowned e1
    assert q.king[1] == idx(7, 0) and not q.over       # h1 was already crowned
    p = mk(white=[("a1", 4)], black=[("e1", 3), ("h1", 2), ("h8", 1)],
           crowns=("a1", "h8"))                        # crown on the SHORTEST
    q = G.apply_move(p, "0,0>4,0")
    assert q.king[1] == idx(7, 0), "h1 (height 2) becomes black's unique tallest"
    # A player with no unique tallest and no crown yet stays uncrowned.
    p = mk(white=[("a1", 1), ("b1", 1)], black=[("h8", 1)], crowns=(None, "h8"))
    q = G.apply_move(p, off("a1"))                     # a1 walks off; b1 alone
    assert q.king[0] == idx(1, 0), "the last stack standing is unique -> crowned"


def test_crown_is_on_a_stack():
    """Standing invariant over real play: a live crown always sits on one of its
    OWNER'S stacks, and a player's last stack is always their crowned one.

    The first half is what catches a stale crown pointer (the crown left behind
    on the square its stack moved off, which would make that king uncapturable
    and erase the ♚ from the board).  The second half is the assumption the
    termination and no-stalemate proofs in `rules.md` rest on — it is why a
    player can never be reduced to zero stacks, and why the 15-removal bound
    holds.  Both are asserted at EVERY ply of games played with a capture bias,
    because uniform-random play hardly ever captures.

    Also counts the positions that make the tie rule load-bearing — a crown
    strictly shorter than another stack of the same player — so that if a future
    change quietly made the crown always-tallest, this test would notice.
    """
    rng = random.Random(2026)
    plies = shorter = tied_top = reset_to_one = 0
    for gi in range(240):
        bias = (0.0, 0.5, 0.9)[gi % 3]
        s = G.initial_state()
        while not G.is_terminal(s):
            for seat in (0, 1):
                k = s.king[seat]
                mine = [v for v in s.board if v and owner(v) == seat]
                if k >= 0:
                    assert s.board[k] and owner(s.board[k]) == seat, \
                        f"crown of seat {seat} is not on a stack of theirs: {k}"
                    top = max(height(v) for v in mine)
                    if height(s.board[k]) < top:
                        shorter += 1
                    elif sum(1 for v in mine if height(v) == top) > 1:
                        tied_top += 1
                    if height(s.board[k]) == 1 and top > 1:
                        reset_to_one += 1
                assert mine, "a live player with no stacks at all"
                if len(mine) == 1:
                    assert k >= 0, "the last stack must be the crowned one"
            plies += 1
            lm = G.legal_moves(s)
            if bias and rng.random() < bias:
                caps = [m for m in lm if not m.endswith(">off")
                        and s.board[idx(*(int(x) for x in
                                          m.partition(">")[2].split(",")))]]
                if caps:
                    lm = caps
            s = G.apply_move(s, rng.choice(lm))
    # The interesting cases really occur, so the assertions above are not idle.
    assert shorter > 50, shorter          # crown NOT the tallest stack
    assert tied_top > 50, tied_top        # crown tied for tallest
    assert reset_to_one > 20, reset_to_one  # crown reset to 1 by its own capture
    return plies, shorter, tied_top, reset_to_one


def test_illegal_moves_rejected():
    """`apply_move` is the enforcement point, so it must refuse the near-misses.

    (The server only ever submits a move from `legal_moves`, but `describe_move`
    and any direct use of the class go straight through `apply_move`.)"""
    s = mk(white=[("d4", 3), ("e4", 1)], black=[("g7", 2), ("h8", 1)],
           crowns=("d4", "h8"))
    bad = [
        "3,3>3,4",      # one square, not three
        "3,3>3,6-",     # malformed
        "3,3>4,7",      # not a queen line
        "3,3>off",      # d4 is height 3: no edge within reach
        "4,3>4,3",      # e4 is height 1 in the interior: cannot leave
        "6,6>6,4",      # not White's stack
        "0,0>0,3",      # no stack there at all
        "3,3>4,3",      # wrong distance onto a friendly stack
        "9,9>0,0",      # off-board cell id
    ]
    for m in bad:
        try:
            G.apply_move(s, m)
        except (ValueError, IndexError):
            continue
        raise AssertionError(f"apply_move accepted the illegal move {m!r}")
    # ...and landing on your own stack is refused even at the right distance.
    t = mk(white=[("d4", 3), ("d7", 1)], black=[("h8", 1)], crowns=("d4", "h8"))
    try:
        G.apply_move(t, "3,3>3,6")
    except ValueError:
        pass
    else:
        raise AssertionError("apply_move allowed a self-capture")
    # The self-path SPELLING of the walk-off is refused too, even for a stack
    # that CAN legally leave the board — so "a second click on an already
    # selected stack can never destroy it" holds at the engine level and not
    # only in the renderer's move routing.
    u = mk(white=[("a4", 2), ("d4", 1)], black=[("h8", 1)], crowns=("a4", "h8"))
    assert off("a4") in G.legal_moves(u)          # it really can walk off...
    try:
        G.apply_move(u, "0,3>0,3")                # ...but not spelled this way
    except ValueError:
        pass
    else:
        raise AssertionError("apply_move accepted the self-path walk-off")
    return len(bad) + 2


def test_win_conditions():
    # (1) capture the enemy crown
    s = mk(white=[("a1", 4)], black=[("e1", 2), ("h8", 1)], crowns=("a1", "e1"))
    t = G.apply_move(s, "0,0>4,0")
    assert t.over and t.winner == 0 and G.returns(t) == [1.0, -1.0]
    assert G.legal_moves(t) == []
    # the same for the other seat, so the test is not colour-blind
    s = mk(white=[("a1", 2), ("h8", 1)], black=[("e8", 4)], crowns=("a1", "e8"),
           to_move=1)
    t = G.apply_move(s, "4,7>0,7")
    assert not t.over                                  # a1 is on rank 1, not 8
    s = mk(white=[("a8", 2), ("h1", 1)], black=[("e8", 4)], crowns=("a8", "e8"),
           to_move=1)
    t = G.apply_move(s, "4,7>0,7")
    assert t.over and t.winner == 1 and G.returns(t) == [-1.0, 1.0]
    # (2) walk your OWN crown off the board -> you lose
    s = mk(white=[("a4", 2), ("d4", 1)], black=[("h8", 1)], crowns=("a4", "h8"))
    t = G.apply_move(s, off("a4"))
    assert t.over and t.winner == 1 and G.returns(t) == [-1.0, 1.0]
    # walking an UNCROWNED stack off is just a move
    t = G.apply_move(mk(white=[("a4", 2), ("d4", 1)], black=[("h8", 1)],
                        crowns=("d4", "h8")), off("a4"))
    assert not t.over
    # capturing a NON-crowned enemy stack is just a move
    s = mk(white=[("a1", 4)], black=[("e1", 2), ("h8", 1)], crowns=("a1", "h8"))
    t = G.apply_move(s, "0,0>4,0")
    assert not t.over and t.king[1] == idx(7, 7)


def test_decisive_outranks_the_counters():
    """A win must survive the ply cap tripping on the very same move."""
    # A crown capture delivered on the ply the cap would fire.
    s = mk(white=[("a1", 4)], black=[("e1", 2), ("h8", 1)], crowns=("a1", "e1"),
           ply=PLY_CAP - 1)
    t = G.apply_move(s, "0,0>4,0")
    assert t.ply == PLY_CAP
    assert t.over and t.winner == 0 and G.returns(t) == [1.0, -1.0], (t.winner,)
    # CONTROL: the counter really is live on that ply — the same position, a
    # quiet move, must draw.  Without this the assertion above proves nothing.
    u = G.apply_move(s, "0,0>4,4")
    assert u.ply == PLY_CAP and u.over and u.winner is None
    assert G.returns(u) == [0.0, 0.0]
    # Losing by walking your own crown off also outranks the cap.
    s = mk(white=[("a4", 2), ("d4", 1)], black=[("h8", 1)], crowns=("a4", "h8"),
           ply=PLY_CAP - 1)
    t = G.apply_move(s, off("a4"))
    assert t.over and t.winner == 1, t.winner


def test_no_stalemate():
    """A player with at least one stack ALWAYS has a legal move.

    Proof: take their right-most stack, of height h at column c.  Its eastward
    landing square is column c + h.  If that is off the board the stack may leave
    the board; otherwise the square is on the board and cannot hold one of their
    own stacks (that stack would be further right), so it is empty or an enemy —
    either way a legal move.  Asserted below on random positions and on the whole
    of random play, and the defensive branch is exercised separately.
    """
    rng = random.Random(9)
    n = 0
    for _ in range(3000):
        s = random_position(rng)
        for seat in (0, 1):
            has_piece = any(v and owner(v) == seat for v in s.board)
            moves = G.legal_moves(replace(s, to_move=seat))
            assert bool(moves) == has_piece, (seat, has_piece, len(moves))
            n += 1
    # The unreachable fallback is still wired up: hand-build a position where a
    # capture leaves the victim with no stacks at all AND no crown to lose (real
    # play cannot get here — a player's last stack is always their crowned one).
    s = mk(white=[("a1", 4)], black=[("e1", 2)], crowns=("a1", None))
    t = G.apply_move(s, "0,0>4,0")
    assert t.king[1] == NO_KING and not any(v < 0 for v in t.board)
    assert t.over and t.winner == 0, (t.over, t.winner)
    return n


def test_termination():
    rng = random.Random(31)
    longest = 0
    ends = {"crown captured": 0, "walked off": 0}
    for _ in range(1500):
        s = G.initial_state()
        while not G.is_terminal(s):
            assert G.legal_moves(s), "non-terminal state with no moves"
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        # Every game ends with a crown dead — never by the cap, never a draw.
        assert s.winner is not None, "random play produced a draw"
        assert DEAD in s.king, s.king
        assert s.ply < PLY_CAP, s.ply
        ends["walked off" if s.last[0] == s.last[1] else "crown captured"] += 1
        longest = max(longest, s.ply)
    assert ends["crown captured"] > 0 and ends["walked off"] > 0, ends
    # The proven bound is 352 plies (see rules.md); the cap sits well above it,
    # and the manifest's max_random_plies (400) sits between the two.
    assert PLY_CAP > 352
    return longest, ends


def test_ply_cap_is_live():
    """The cap is a real backstop, not dead code — patch the LIVE module object
    (``load_from_dir`` imports game.py under a synthetic module name, so patching
    ``games.lielow.game`` by path would silently patch a different object) and
    check the behaviour actually changes."""
    mod = sys.modules[type(G).__module__]
    old = mod.PLY_CAP
    try:
        mod.PLY_CAP = 6
        rng = random.Random(2)
        s = G.initial_state()
        while not G.is_terminal(s):
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        assert s.ply == 6 and s.over and s.winner is None, (s.ply, s.winner)
        assert G.returns(s) == [0.0, 0.0]
    finally:
        mod.PLY_CAP = old
    assert mod.PLY_CAP == PLY_CAP


def test_purity_and_serialize():
    rng = random.Random(77)
    keys = {"board", "king", "to_move", "ply", "over", "winner", "last"}
    assert {f.name for f in dc_fields(LState)} == keys
    n = 0
    for _ in range(60):
        s = G.initial_state()
        while True:
            d = G.serialize(s)
            assert set(d) == keys, set(d)
            json.dumps(d)                                   # JSON-able
            # LOSSLESS at the STATE level: every field survives.  The weaker
            # serialize(deserialize(d)) == d form cannot see a dropped field.
            assert G.deserialize(d) == s, (G.deserialize(d), s)
            assert G.deserialize(json.loads(json.dumps(d))) == s
            n += 1
            if G.is_terminal(s):
                break
            m = rng.choice(G.legal_moves(s))
            before = (s.board, s.king, s.to_move, s.ply, s.over, s.winner, s.last)
            t = G.apply_move(s, m)
            assert (s.board, s.king, s.to_move, s.ply, s.over, s.winner,
                    s.last) == before, "apply_move mutated its input"
            assert t is not s
            s = t
    # MUTATION TEST of the round-trip itself: perturbing any single field must be
    # detected, so a field that serialize forgot could not slip through.
    s = G.apply_move(G.initial_state(), "0,1>0,2")
    base = G.serialize(s)
    for field, val in (("to_move", 0), ("ply", 99), ("over", True),
                       ("winner", 1), ("last", [0, 0]),
                       ("king", [NO_KING, NO_KING]),
                       ("board", [0] * NCELLS)):
        d = dict(base)
        d[field] = val
        assert G.deserialize(d) != s, f"round-trip is blind to {field}"
    return n


def test_move_encoding():
    """The walk-off move must NOT look like a cell path.

    `web/src/Board.jsx` routes a move to the board click handler when every
    ">"-segment is a real cell id, and fires it as soon as the clicked cells
    match.  A self-path "c,r>c,r" therefore fires on the SECOND click of the same
    square — which is how a player deselects a piece everywhere else — and in
    Lielow that irreversibly removes the stack, losing the game when it is the
    crowned one.  "off" is not a cell id, so the move falls through to the
    labelled action-button channel and has to be chosen deliberately.
    """
    cell_ids = {f"{c},{r}" for c in range(SIZE) for r in range(SIZE)}

    def is_cell_path(m):                       # mirrors Board.jsx `isCellPath`
        return all(seg.split("=")[0] in cell_ids for seg in m.split(">"))

    rng = random.Random(12)
    walkoffs = most = 0
    for _ in range(120):
        s = G.initial_state()
        while not G.is_terminal(s):
            ms = G.legal_moves(s)
            names = G.render(s)["actionNames"]
            n_off = 0
            for m in ms:
                a, _, b = m.partition(">")
                assert a in cell_ids, m
                if b == "off":
                    n_off += 1
                    assert not is_cell_path(m), m       # -> action button
                    assert m in names and names[m], m   # ...with a real label
                    assert algebraic(idx(*(int(x) for x in a.split(",")))) \
                        in names[m], names[m]           # naming ITS stack
                else:
                    assert b in cell_ids and b != a, m  # never a self-path
                    assert is_cell_path(m), m           # -> board clicks
                    assert m not in names, m
            # every action button is a legal move, and there are never more of
            # them than the mover has stacks (8), so the row stays usable
            assert set(names) <= set(ms) and n_off == len(names)
            assert n_off <= SIZE, n_off
            most = max(most, n_off)
            walkoffs += n_off
            s = G.apply_move(s, rng.choice(ms))
    # the button that loses the game says so
    s = mk(white=[("a4", 2), ("d4", 1)], black=[("h8", 1)], crowns=("a4", "h8"))
    assert "RESIGNS" in G.render(s)["actionNames"][off("a4")]
    assert "RESIGNS" not in G.render(
        mk(white=[("a4", 2), ("d4", 1)], black=[("h8", 1)],
           crowns=("d4", "h8")))["actionNames"][off("a4")]
    # a terminal position offers no buttons at all
    t = G.apply_move(s, off("a4"))
    assert t.over and G.render(t)["actionNames"] == {} and G.legal_moves(t) == []
    return most


def test_describe_and_render():
    s = G.initial_state()
    assert G.describe_move(s, "0,1>0,2") == "a2-a3"
    assert G.describe_move(s, off("a2")) == "a2-off"
    p = mk(white=[("a1", 4)], black=[("e1", 2), ("h8", 1)], crowns=("a1", "h8"))
    assert G.describe_move(p, "0,0>4,0") == "a1xe1"
    p = mk(white=[("a1", 4)], black=[("e1", 2), ("h8", 1)], crowns=("a1", "e1"))
    assert G.describe_move(p, "0,0>4,0") == "a1xe1#"
    p = mk(white=[("a4", 2), ("d4", 1)], black=[("h8", 1)], crowns=("a4", "h8"))
    assert G.describe_move(p, off("a4")) == "a4-off#"

    r = G.render(G.initial_state())
    b = r["board"]
    assert b == {"type": "square", "width": SIZE, "height": SIZE}, b
    cells = {f"{c},{rr}" for c in range(SIZE) for rr in range(SIZE)}
    assert len(r["pieces"]) == 16
    for pc in r["pieces"]:
        assert pc["cell"] in cells and pc["owner"] in (0, 1)
        assert pc["stack"] == [pc["owner"]]              # height 1 -> one band
        assert "label" not in pc                          # nobody is crowned yet
    json.dumps(r)
    # Heights and the crown marker show up, and ONLY on the crowned stacks.
    rng = random.Random(5)
    s = G.initial_state()
    seen_crown = seen_tall = 0
    while not G.is_terminal(s):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        r = G.render(s)
        json.dumps(r)
        crowned = set()
        for pc in r["pieces"]:
            c, rr = (int(x) for x in pc["cell"].split(","))
            v = s.board[idx(c, rr)]
            assert pc["owner"] == owner(v)
            assert pc["stack"] == [owner(v)] * height(v)
            if height(v) > 1:
                seen_tall += 1
            if "label" in pc:
                crowned.add(idx(c, rr))
        want = {k for k in s.king if k >= 0}
        assert crowned == want, (crowned, want)
        seen_crown += len(crowned)
        assert 0 < len(r["highlights"]) <= 2
    assert seen_crown and seen_tall


def test_heuristic():
    h = G.heuristic(G.initial_state())
    assert isinstance(h, list) and len(h) == 2, h
    assert all(isinstance(x, float) and -1.0 < x < 1.0 for x in h), h
    assert abs(h[0] + h[1]) < 1e-9
    # material and the crown-en-prise term point the right way
    s = mk(white=[("a1", 2), ("b1", 1)], black=[("h8", 1)], crowns=("a1", "h8"))
    assert G.heuristic(s)[0] > 0
    s = mk(white=[("a1", 4)], black=[("e1", 2), ("h8", 1)], crowns=("a1", "e1"))
    assert G.heuristic(s)[0] > G.heuristic(
        mk(white=[("a1", 4)], black=[("e1", 2), ("h8", 1)],
           crowns=("a1", "h8")))[0]
    rng = random.Random(6)
    for _ in range(400):
        v = G.heuristic(random_position(rng))
        assert isinstance(v, list) and len(v) == 2 and all(-1 < x < 1 for x in v)
    # The bug this guards is a bare float, which only bites when the rollout
    # cutoff is actually REACHED — force it with a tiny max_rollout.
    from agp.mcts import MCTSBot
    mv = MCTSBot(random.Random(1), iterations=30, max_rollout=4).select(
        G, G.initial_state())
    assert mv in G.legal_moves(G.initial_state())


def main():
    opening = test_opening()
    xchecks = test_movegen_cross_check()
    test_movement()
    test_off_the_board()
    test_height_changes()
    test_crown()
    crown_plies, shorter, tied_top, reset1 = test_crown_is_on_a_stack()
    nbad = test_illegal_moves_rejected()
    test_win_conditions()
    test_decisive_outranks_the_counters()
    most_off = test_move_encoding()
    stale = test_no_stalemate()
    longest, ends = test_termination()
    test_ply_cap_is_live()
    roundtrips = test_purity_and_serialize()
    test_describe_and_render()
    test_heuristic()
    print(f"lielow selftest OK ({opening}-move opening, {xchecks} independent "
          f"move-gen cross-checks, {stale} stalemate checks, "
          f"1500 random games (longest {longest} plies, ends {ends}), "
          f"{crown_plies} crown-pointer checks (crown shorter than another "
          f"stack {shorter}x, tied for tallest {tied_top}x, reset to 1 by its "
          f"own capture {reset1}x), {nbad} illegal moves refused, "
          f"{roundtrips} serialize round-trips, "
          f"walk-off encoding checked (<= {most_off} buttons at once))")


if __name__ == "__main__":
    main()
