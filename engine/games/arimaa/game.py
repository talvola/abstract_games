"""Arimaa, by Omar Syed (2002) -- https://arimaa.com/arimaa/learn/

Arimaa is the famous "anti-computer" abstract: a chess-like game on an 8x8 board
designed to be easy for humans and (originally) hard for machines. The pieces
have a simple strength order and move one step at a time, but a player makes up
to FOUR steps per turn, and the push/pull/freeze/trap mechanics create deep play.

Rules as implemented (see rules.md; verified against arimaa.com/arimaa/learn/):

* Board: 8x8. Files a-h (columns 0..7), ranks 1-8 (rows 0..7). FOUR trap squares:
  c3, f3, c6, f6  ==  (2,2), (5,2), (2,5), (5,5).
* Pieces per side (16): 1 Elephant E, 1 Camel M, 2 Horses H, 2 Dogs D, 2 Cats C,
  8 Rabbits R. Strength: E > M > H > D > C > R.
* Gold = player 0 (home rows 1-2 = rows 0-1), Silver = player 1 (home rows 7-8 =
  rows 6-7). Gold moves first.
* SETUP phase: each player, Gold first, places all 16 of their pieces on their own
  two home rows, one at a time, in any arrangement. Then play begins.
* A turn = 1..4 STEPS. A step moves one piece one orthogonal square to an EMPTY
  square. Rabbits may not step backward (toward their own side). At least one step
  is required; you may stop early.
* PUSH/PULL each cost 2 steps and act on an enemy piece STRICTLY WEAKER than the
  mover that is orthogonally adjacent.
    - Push: move the weaker enemy to an adjacent empty square, then move your piece
      into the square it vacated.
    - Pull: move your piece to an adjacent empty square, then move the adjacent
      weaker enemy into the square your piece vacated.
* FREEZE: a piece is frozen (cannot move/step on its own and cannot be the mover of
  a push or pull) if it is orthogonally adjacent to a STRONGER enemy and has NO
  orthogonally-adjacent FRIENDLY piece. A frozen piece can still be pushed/pulled.
* TRAPS: after every step, any piece on a trap square with no orthogonally-adjacent
  FRIENDLY piece is removed (captured).
* WIN (checked at the END of a turn): (a) a player has a rabbit on the opponent's
  home rank wins; if both transient goals appear, the side that just moved wins.
  (b) a player with no rabbits loses (other side wins). (c) a player with no legal
  move (immobilized) loses.
* No net-null turn: you may not end your turn with the board identical to its state
  at the start of your turn. A 3rd occurrence of the same full position (same side
  to move) is also forbidden; we additionally cap total turns to guarantee
  termination (declared a draw at the cap).

The win is an *event* resolved inside ``apply_move`` and stored in ``winner`` (the
opening position is not terminal), per the platform "win as event" pattern.

Move encoding (clickable via Board.jsx):
  * setup placement:  "L@c,r"            (drop a reserve piece onto a home cell)
  * single step:      "c1,r1>c2,r2"
  * push: "push c1,r1>c2,r2>c3,r3"  pusher c1 -> enemy at c2 (weaker, adjacent),
            enemy moves c2 -> c3 (adjacent empty), then pusher c1 -> c2.
  * pull: "pull c1,r1>c2,r2>c3,r3"  puller c1 -> empty c2 (adjacent), then enemy at
            c3 (weaker, adjacent to c1) moves c3 -> c1.
  * end turn:         "finish"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

GOLD, SILVER = 0, 1

# Piece strengths (higher = stronger).
STRENGTH = {"R": 1, "C": 2, "D": 3, "H": 4, "M": 5, "E": 6}
LETTERS = ["E", "M", "H", "D", "C", "R"]  # display order
RESERVE = {"E": 1, "M": 1, "H": 2, "D": 2, "C": 2, "R": 8}  # 16 pieces
TRAPS = frozenset([(2, 2), (5, 2), (2, 5), (5, 5)])
ORTHO = [(0, 1), (0, -1), (1, 0), (-1, 0)]

PLY_CAP = 600  # hard cap on turns -> declared a draw (termination guarantee)


def _cell(s: str) -> tuple[int, int]:
    c, r = s.split(",")
    return int(c), int(r)


def _cs(c: int, r: int) -> str:
    return f"{c},{r}"


def _on(c: int, r: int) -> bool:
    return 0 <= c < 8 and 0 <= r < 8


def _home_rows(player: int):
    return (0, 1) if player == GOLD else (6, 7)


def _goal_row(player: int) -> int:
    """The opponent's home rank a rabbit must reach to win."""
    return 7 if player == GOLD else 0


def _rabbit_backward(player: int) -> tuple[int, int]:
    """The forbidden (backward) step direction for this player's rabbits."""
    return (0, -1) if player == GOLD else (0, 1)


@dataclass
class ArimaaState:
    board: dict = field(default_factory=dict)      # (c,r) -> (owner, letter)
    to_move: int = GOLD
    # setup phase: per-player remaining reserve to place (empty dict once placed)
    hands: dict = field(default_factory=dict)      # player -> {letter: count}
    setup: bool = True
    # in-turn (play) bookkeeping
    steps_used: int = 0
    turn_start: Optional[tuple] = None             # frozen snapshot of board at turn start
    reps: dict = field(default_factory=dict)       # position-key -> count (3-fold)
    ply: int = 0                                    # completed turns
    winner: Optional[int] = None


def _board_key(board: dict) -> tuple:
    return tuple(sorted((c, r, o, t) for (c, r), (o, t) in board.items()))


def _pos_key(board: dict, to_move: int) -> tuple:
    return (_board_key(board), to_move)


def _resolve_traps(board: dict) -> dict:
    """Return a copy of board with any unsupported trap-square pieces removed."""
    out = dict(board)
    for (tc, tr) in TRAPS:
        if (tc, tr) not in out:
            continue
        owner = out[(tc, tr)][0]
        supported = any(
            out.get((tc + dc, tr + dr), (None,))[0] == owner for dc, dr in ORTHO
        )
        if not supported:
            del out[(tc, tr)]
    return out


def _has_friendly_neighbor(board: dict, c: int, r: int, owner: int) -> bool:
    return any(board.get((c + dc, r + dr), (None,))[0] == owner for dc, dr in ORTHO)


def _is_frozen(board: dict, c: int, r: int) -> bool:
    """A piece is frozen if adjacent to a stronger enemy and has no friendly
    neighbour."""
    cell = board.get((c, r))
    if cell is None:
        return False
    owner, letter = cell
    str_self = STRENGTH[letter]
    stronger_enemy = False
    friendly = False
    for dc, dr in ORTHO:
        nb = board.get((c + dc, r + dr))
        if nb is None:
            continue
        no, nt = nb
        if no == owner:
            friendly = True
        elif STRENGTH[nt] > str_self:
            stronger_enemy = True
    return stronger_enemy and not friendly


def _rabbit_ok(player: int, letter: str, dr: int) -> bool:
    """Is a step with vertical delta ``dr`` allowed for this piece?"""
    if letter != "R":
        return True
    return (0, dr) != _rabbit_backward(player)


class Arimaa(Game):
    uid = "arimaa"
    name = "Arimaa"

    @property
    def num_players(self) -> int:
        return 2

    # ------------------------------------------------------------------ setup
    def initial_state(self, options=None, rng=None) -> ArimaaState:
        hands = {GOLD: dict(RESERVE), SILVER: dict(RESERVE)}
        return ArimaaState(board={}, to_move=GOLD, hands=hands, setup=True)

    def current_player(self, s: ArimaaState) -> int:
        return s.to_move

    # ----------------------------------------------------------- legal moves
    def _setup_moves(self, s: ArimaaState) -> list[str]:
        player = s.to_move
        hand = s.hands.get(player, {})
        letters = [L for L in LETTERS if hand.get(L, 0) > 0]
        if not letters:
            return []
        out = []
        r0, r1 = _home_rows(player)
        for r in (r0, r1):
            for c in range(8):
                if (c, r) in s.board:
                    continue
                for L in letters:
                    out.append(f"{L}@{c},{r}")
        return out

    def _step_moves(self, s: ArimaaState) -> list[str]:
        """Single-step moves available with the remaining step budget."""
        player = s.to_move
        out = []
        for (c, r), (owner, letter) in s.board.items():
            if owner != player:
                continue
            if _is_frozen(s.board, c, r):
                continue
            for dc, dr in ORTHO:
                nc, nr = c + dc, r + dr
                if not _on(nc, nr) or (nc, nr) in s.board:
                    continue
                if not _rabbit_ok(player, letter, dr):
                    continue
                out.append(f"{_cs(c, r)}>{_cs(nc, nr)}")
        return out

    def _push_pull_moves(self, s: ArimaaState) -> list[str]:
        player = s.to_move
        out = []
        for (c, r), (owner, letter) in s.board.items():
            if owner != player:
                continue
            if _is_frozen(s.board, c, r):
                continue
            str_self = STRENGTH[letter]
            # adjacent weaker enemies
            for dc, dr in ORTHO:
                ec, er = c + dc, r + dr
                enemy = s.board.get((ec, er))
                if enemy is None:
                    continue
                eo, et = enemy
                if eo == player or STRENGTH[et] >= str_self:
                    continue
                # PUSH: enemy -> adjacent empty, mover -> enemy square
                for d2c, d2r in ORTHO:
                    dest = (ec + d2c, er + d2r)
                    if not _on(*dest) or dest in s.board:
                        continue
                    out.append(f"push {_cs(c, r)}>{_cs(ec, er)}>{_cs(*dest)}")
                # PULL: mover -> adjacent empty, enemy -> mover square
                for d2c, d2r in ORTHO:
                    dest = (c + d2c, r + d2r)
                    if not _on(*dest) or dest in s.board:
                        continue
                    out.append(f"pull {_cs(c, r)}>{_cs(*dest)}>{_cs(ec, er)}")
        return out

    def legal_moves(self, s: ArimaaState) -> list[str]:
        if self.is_terminal(s):
            return []
        if s.setup:
            return self._setup_moves(s)

        budget = 4 - s.steps_used
        raw: list[str] = []
        if budget >= 1:
            raw.extend(self._step_moves(s))
        if budget >= 2:
            raw.extend(self._push_pull_moves(s))

        # Filter out a move that would EXHAUST the step budget while returning the
        # board to its turn-start position: that leaves a net-null turn with no way
        # to finish legally (an illegal whole-turn in Arimaa), so it isn't offered.
        moves: list[str] = []
        for m in raw:
            cost = 2 if m.startswith(("push ", "pull ")) else 1
            if s.steps_used + cost >= 4:
                nb = self.apply_move(s, m).board
                if _board_key(nb) == s.turn_start:
                    continue
            moves.append(m)

        # "finish" is legal once >=1 step done AND the board changed vs turn start.
        if s.steps_used >= 1 and _board_key(s.board) != s.turn_start:
            moves.append("finish")
        return moves

    # -------------------------------------------------------------- applying
    def apply_move(self, s: ArimaaState, move: str, rng=None) -> ArimaaState:
        if s.winner is not None:
            raise ValueError("game over")

        if s.setup:
            return self._apply_setup(s, move)
        if move == "finish":
            return self._finish_turn(s)
        if move.startswith("push ") or move.startswith("pull "):
            return self._apply_pushpull(s, move)
        return self._apply_step(s, move)

    def _apply_setup(self, s: ArimaaState, move: str) -> ArimaaState:
        letter, cs = move.split("@")
        c, r = _cell(cs)
        player = s.to_move
        hand = {p: dict(h) for p, h in s.hands.items()}
        if hand[player].get(letter, 0) <= 0:
            raise ValueError(f"no {letter} in reserve")
        r0, r1 = _home_rows(player)
        if r not in (r0, r1) or (c, r) in s.board:
            raise ValueError(f"illegal setup placement {move!r}")
        board = dict(s.board)
        board[(c, r)] = (player, letter)
        hand[player][letter] -= 1
        if hand[player][letter] == 0:
            del hand[player][letter]

        if hand[player]:
            # same player keeps placing
            return ArimaaState(board=board, to_move=player, hands=hand, setup=True)
        # this player finished placing
        other = 1 - player
        if hand[other]:
            return ArimaaState(board=board, to_move=other, hands=hand, setup=True)
        # both placed -> begin play; Gold to move, fresh turn
        st = ArimaaState(board=board, to_move=GOLD, hands={GOLD: {}, SILVER: {}},
                         setup=False, steps_used=0, turn_start=_board_key(board))
        st.reps = {_pos_key(board, GOLD): 1}
        return st

    def _new_inturn(self, s: ArimaaState, board: dict, steps_used: int) -> ArimaaState:
        return ArimaaState(
            board=board, to_move=s.to_move, hands={GOLD: {}, SILVER: {}},
            setup=False, steps_used=steps_used, turn_start=s.turn_start,
            reps=dict(s.reps), ply=s.ply, winner=None,
        )

    def _apply_step(self, s: ArimaaState, move: str) -> ArimaaState:
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        player = s.to_move
        cell = s.board.get(frm)
        if cell is None or cell[0] != player:
            raise ValueError(f"no own piece at {fs}")
        owner, letter = cell
        if _is_frozen(s.board, *frm):
            raise ValueError("frozen piece")
        dc, dr = to[0] - frm[0], to[1] - frm[1]
        if (dc, dr) not in ORTHO or to in s.board or not _on(*to):
            raise ValueError(f"illegal step {move!r}")
        if not _rabbit_ok(player, letter, dr):
            raise ValueError("rabbit cannot step backward")
        board = dict(s.board)
        del board[frm]
        board[to] = (owner, letter)
        board = _resolve_traps(board)
        return self._new_inturn(s, board, s.steps_used + 1)

    def _apply_pushpull(self, s: ArimaaState, move: str) -> ArimaaState:
        kind, rest = move.split(" ", 1)
        a, b, c = (_cell(x) for x in rest.split(">"))
        player = s.to_move
        if s.steps_used > 2:
            raise ValueError("not enough steps for push/pull")
        mover = s.board.get(a)
        if mover is None or mover[0] != player:
            raise ValueError("no own pusher/puller")
        if _is_frozen(s.board, *a):
            raise ValueError("frozen mover")
        board = dict(s.board)
        if kind == "push":
            # a = mover, b = enemy (adjacent, weaker), c = empty dest for enemy
            enemy = board.get(b)
            if enemy is None or enemy[0] == player:
                raise ValueError("push target not enemy")
            if STRENGTH[enemy[1]] >= STRENGTH[mover[1]]:
                raise ValueError("cannot push equal/stronger")
            if _dist1(a, b) != 1 or _dist1(b, c) != 1 or c in board or not _on(*c):
                raise ValueError("bad push geometry")
            # enemy b->c, mover a->b
            del board[b]
            board[c] = enemy
            board = _resolve_traps(board)
            # mover may have been on a trap and removed by the enemy move? no:
            # mover still at a. Move it now.
            mv = board.pop(a)
            board[b] = mv
            board = _resolve_traps(board)
        else:  # pull
            # a = mover, b = empty dest for mover (adjacent to a), c = enemy (adjacent to a, weaker)
            enemy = board.get(c)
            if enemy is None or enemy[0] == player:
                raise ValueError("pull target not enemy")
            if STRENGTH[enemy[1]] >= STRENGTH[mover[1]]:
                raise ValueError("cannot pull equal/stronger")
            if _dist1(a, b) != 1 or _dist1(a, c) != 1 or b in board or not _on(*b):
                raise ValueError("bad pull geometry")
            # mover a->b
            del board[a]
            board[b] = mover
            board = _resolve_traps(board)
            # enemy c->a (a is now empty; but a could have been... a is empty)
            en = board.pop(c)
            board[a] = en
            board = _resolve_traps(board)
        return self._new_inturn(s, board, s.steps_used + 2)

    # ------------------------------------------------------------ turn end
    def _finish_turn(self, s: ArimaaState) -> ArimaaState:
        if s.steps_used < 1 or _board_key(s.board) == s.turn_start:
            raise ValueError("cannot finish: no net change")
        board = s.board
        mover = s.to_move
        other = 1 - mover

        # ---- win checks (end of turn) ----
        winner = self._check_win(board, mover)
        if winner is not None:
            return ArimaaState(board=board, to_move=other, hands={GOLD: {}, SILVER: {}},
                               setup=False, steps_used=0, turn_start=_board_key(board),
                               reps=dict(s.reps), ply=s.ply + 1, winner=winner)

        # ---- 3-fold repetition + ply cap (termination) ----
        ply = s.ply + 1
        reps = dict(s.reps)
        key = _pos_key(board, other)
        reps[key] = reps.get(key, 0) + 1
        # Hand to opponent. Opponent with no legal move -> immobilized -> loses.
        nxt = ArimaaState(board=board, to_move=other, hands={GOLD: {}, SILVER: {}},
                          setup=False, steps_used=0, turn_start=_board_key(board),
                          reps=reps, ply=ply, winner=None)
        if ply >= PLY_CAP or reps[key] >= 3:
            # Declared a draw at the hard cap / 3-fold (rare).
            nxt.winner = -1  # sentinel for draw
            return nxt
        if not self.legal_moves(nxt):
            # opponent immobilized at the START of its turn -> opponent loses
            nxt.winner = mover
            return nxt
        return nxt

    def _check_win(self, board: dict, mover: int) -> Optional[int]:
        """Goal / rabbit-elimination win at end of mover's turn. Mover wins ties."""
        other = 1 - mover
        mover_goal = any(o == mover and t == "R" and r == _goal_row(mover)
                         for (c, r), (o, t) in board.items())
        other_goal = any(o == other and t == "R" and r == _goal_row(other)
                         for (c, r), (o, t) in board.items())
        mover_rabbits = any(o == mover and t == "R" for (o, t) in board.values())
        other_rabbits = any(o == other and t == "R" for (o, t) in board.values())

        # Goal conditions take precedence; mover wins ties.
        if mover_goal:
            return mover
        if other_goal:
            return other
        # Rabbit elimination: if a side has no rabbits, the OTHER side wins;
        # mover wins ties (both eliminated -> mover).
        if not other_rabbits:
            return mover
        if not mover_rabbits:
            return other
        return None

    # ------------------------------------------------------------ terminal
    def is_terminal(self, s: ArimaaState) -> bool:
        return s.winner is not None

    def returns(self, s: ArimaaState) -> list[float]:
        if s.winner == GOLD:
            return [1.0, -1.0]
        if s.winner == SILVER:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # draw (-1 sentinel) or non-terminal

    # ----------------------------------------------------------- serialize
    def serialize(self, s: ArimaaState) -> dict:
        return {
            "board": {_cs(c, r): [o, t] for (c, r), (o, t) in s.board.items()},
            "to_move": s.to_move,
            "hands": {str(p): {L: n for L, n in h.items()} for p, h in s.hands.items()},
            "setup": s.setup,
            "steps_used": s.steps_used,
            "turn_start": [list(x) for x in s.turn_start] if s.turn_start is not None else None,
            # reps is keyed by (board_key, to_move); store as a list of
            # [to_move, [[c,r,owner,letter], ...], count] so it JSON round-trips.
            "reps": [[k[1], [list(t) for t in k[0]], v] for k, v in s.reps.items()],
            "ply": s.ply,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> ArimaaState:
        board = {_cell(k): tuple(v) for k, v in d["board"].items()}
        hands = {int(p): {L: int(n) for L, n in h.items()} for p, h in d["hands"].items()}
        turn_start = tuple(tuple(x) for x in d["turn_start"]) if d["turn_start"] is not None else None
        reps = {}
        for tm, entries, v in d.get("reps", []):
            key = (tuple(tuple(t) for t in entries), tm)
            reps[key] = v
        return ArimaaState(
            board=board, to_move=d["to_move"], hands=hands, setup=d["setup"],
            steps_used=d["steps_used"], turn_start=turn_start, reps=reps,
            ply=d["ply"], winner=d["winner"],
        )

    # ----------------------------------------------------------- presentation
    def describe_move(self, s: ArimaaState, move: str) -> str:
        if "@" in move:
            letter, cs = move.split("@")
            c, r = _cell(cs)
            return f"{letter}@{_alg(c, r)}"
        if move == "finish":
            return "(end turn)"
        if move.startswith("push ") or move.startswith("pull "):
            kind, rest = move.split(" ", 1)
            a, b, c = (_cell(x) for x in rest.split(">"))
            if kind == "push":
                pl = s.board.get(a, (None, "?"))[1]
                en = s.board.get(b, (None, "?"))[1]
                return f"{pl}{_alg(*a)} push {en}{_alg(*b)}->{_alg(*c)}"
            pl = s.board.get(a, (None, "?"))[1]
            en = s.board.get(c, (None, "?"))[1]
            return f"{pl}{_alg(*a)}->{_alg(*b)} pull {en}{_alg(*c)}"
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        letter = s.board.get(frm, (None, "?"))[1]
        return f"{letter}{_alg(*frm)}{_dir(frm, to)}"

    def render(self, s: ArimaaState, perspective=None) -> dict:
        names = {GOLD: "Gold", SILVER: "Silver"}
        pieces = [
            {"cell": _cs(c, r), "owner": o, "label": t}
            for (c, r), (o, t) in s.board.items()
        ]
        tints = {_cs(c, r): "#8a6d3b" for (c, r) in TRAPS}

        if s.winner is not None:
            caption = "Draw (rule cap)" if s.winner == -1 else f"{names[s.winner]} wins"
        elif s.setup:
            placed = 32 - sum(s.hands.get(GOLD, {}).values()) - sum(s.hands.get(SILVER, {}).values())
            caption = f"Setup: {names[s.to_move]} to place ({placed}/32 down)"
        else:
            left = 4 - s.steps_used
            caption = f"{names[s.to_move]} to move ({left} step{'s' if left != 1 else ''} left)"

        spec = {
            "board": {"type": "square", "width": 8, "height": 8, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
        # Setup reserve trays.
        if s.setup:
            spec["reserve"] = {
                str(p): {L: h[L] for L in LETTERS if h.get(L, 0) > 0}
                for p, h in s.hands.items()
            }
        return spec


def _dist1(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _alg(c: int, r: int) -> str:
    return f"{'abcdefgh'[c]}{r + 1}"


def _dir(frm, to) -> str:
    dc, dr = to[0] - frm[0], to[1] - frm[1]
    if (dc, dr) == (0, 1):
        return "n"
    if (dc, dr) == (0, -1):
        return "s"
    if (dc, dr) == (1, 0):
        return "e"
    if (dc, dr) == (-1, 0):
        return "w"
    return "?"
