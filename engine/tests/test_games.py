"""Engine + reference-game tests. Run: ``PYTHONPATH=. python -m pytest`` (or
``python tests/test_games.py`` for a dependency-free smoke run)."""

from __future__ import annotations

import random
from pathlib import Path

from agp import MCTSBot, RandomBot, check, load, play_match

GAMES = Path(__file__).resolve().parent.parent / "games"


def _load(uid):
    return load(GAMES / uid)


def test_tictactoe_conforms():
    manifest, game = _load("tic_tac_toe")
    assert check(game, manifest, games=50).ok


def test_oust_conforms():
    manifest, game = _load("oust")
    assert check(game, manifest, games=30).ok


def test_yodd_conforms_and_rules():
    manifest, game = _load("yodd")
    assert check(game, manifest, games=12).ok
    # opening: Red to move, only single-stone placements (no pass / no end)
    s = game.initial_state(options={"size": 6})
    assert game.current_player(s) == 0
    lm0 = game.legal_moves(s)
    assert "pass" not in lm0 and "end" not in lm0 and all("=" in m for m in lm0)
    # Red places one stone; the opening turn auto-ends (cap = 1)
    s = game.apply_move(s, "0,0=red")
    assert game.current_player(s) == 1 and s.turn_cells == [] and len(s.board) == 1
    # board has 1 group (odd) so Blue may pass; two passes end the game
    assert "pass" in game.legal_moves(s)
    s2 = game.apply_move(game.apply_move(s, "pass"), "pass")
    assert game.is_terminal(s2)
    # 1 red group vs 0 blue groups -> Blue (fewer) wins; never a draw
    assert s2.winner == 1 and game.returns(s2) == [-1.0, 1.0]
    # placing of EITHER colour: Blue drops a red stone next to Red's -> still 1
    # group (odd), so the turn may end after one stone ("end" offered)
    sb = game.apply_move(s, "1,0=red")
    assert game.current_player(sb) == 1 and sb.turn_cells == ["1,0"]
    assert "end" in game.legal_moves(sb)
    # an isolated stone makes the total even -> must place a 2nd stone (no end/pass)
    se = game.apply_move(s, "3,-3=blue")
    assert game.current_player(se) == 1 and se.turn_cells == ["3,-3"]
    lme = game.legal_moves(se)
    assert "end" not in lme and "pass" not in lme and lme
    se2 = game.apply_move(se, "-3,3=red")  # back to odd -> turn auto-ends
    assert game.current_player(se2) == 0 and se2.turn_cells == [] and len(se2.board) == 3


def test_grand_chess_pieces_and_promotion():
    manifest, game = _load("grand_chess")
    assert check(game, manifest, games=4).ok

    def st(pieces, **kw):
        d = {"board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in pieces.items()},
             "to_move": 0, "ep": None, "halfmove": 0, "ply": 0, "reps": {}}
        d.update(kw)
        return game.deserialize(d)

    # Marshall = rook + knight (not bishop)
    m = st({(4, 4): (0, "M"), (0, 0): (0, "K"), (9, 9): (1, "K")})
    mm = {x for x in game.legal_moves(m) if x.startswith("4,4>")}
    assert "4,4>4,9" in mm and "4,4>6,5" in mm and "4,4>6,6" not in mm

    # Cardinal = bishop + knight (not rook)
    c = st({(4, 4): (0, "C"), (0, 0): (0, "K"), (9, 0): (1, "K")})
    cm = {x for x in game.legal_moves(c) if x.startswith("4,4>")}
    assert "4,4>9,9" in cm and "4,4>6,5" in cm and "4,4>4,9" not in cm

    # no castling
    ks = st({(4, 0): (0, "K"), (0, 0): (0, "R"), (9, 0): (0, "R"), (4, 9): (1, "K")})
    assert "4,0>6,0" not in game.legal_moves(ks) and "4,0>2,0" not in game.legal_moves(ks)

    # promotion only to a captured (missing) piece type. Full white army present:
    full = {(4, 1): (0, "K"), (3, 1): (0, "Q"), (5, 1): (0, "M"), (6, 1): (0, "C"),
            (0, 0): (0, "R"), (9, 0): (0, "R"), (2, 1): (0, "B"), (7, 1): (0, "B"),
            (1, 1): (0, "N"), (8, 1): (0, "N"), (4, 9): (1, "K")}
    # ... with nothing missing, a pawn on the 10th rank has no promotion -> cannot
    #     advance there at all; on the 9th rank (optional) it may only stay a pawn.
    s = st({**full, (0, 8): (0, "P")})
    assert not any(x.startswith("0,8>") for x in game.legal_moves(s))     # stuck on rank 9
    s = st({**full, (0, 7): (0, "P")})
    p8 = {x for x in game.legal_moves(s) if x.startswith("0,7>")}
    assert p8 == {"0,7>0,8"}                                              # stay a pawn only

    # remove a rook (as if captured) -> a rook becomes a legal promotion target
    nrook = {k: v for k, v in full.items() if k != (9, 0)}
    s = st({**nrook, (0, 8): (0, "P")})
    moves = game.legal_moves(s)
    assert "0,8>0,9=R" in moves and "0,8>0,9=Q" not in moves               # only the lost type


def test_borderline():
    from games.borderline.game import _attacks_king, WHITE, BLACK
    manifest, game = _load("borderline")
    assert check(game, manifest, games=8).ok

    def st(pieces, king, tm=0, ply=0):
        return game.deserialize({
            "board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in pieces.items()},
            "king": f"{king[0]},{king[1]}", "to_move": tm, "ply": ply})

    # the borderline gates the ATTACKER's position, not the king's: a piece may
    # only attack the king once it has itself crossed the borderline (White from
    # rows 4-6, Black from rows 0-2). The king is NOT safe just for being on the
    # borderline (row 3).
    # White rook that has crossed (row 5) attacks the king on the borderline:
    assert _attacks_king(st({(3, 5): (0, "R")}, king=(3, 3)).board, (3, 3), WHITE)
    # the same rook on its own side (row 2, not crossed) does NOT, though aligned:
    assert not _attacks_king(st({(3, 2): (0, "R")}, king=(3, 3)).board, (3, 3), WHITE)
    # Black attacks from rows 0-2; a Black queen on row 2 hits the king on row 3:
    assert _attacks_king(st({(4, 2): (1, "Q")}, king=(3, 3)).board, (3, 3), BLACK)
    assert not _attacks_king(st({(4, 4): (1, "Q")}, king=(3, 3)).board, (3, 3), BLACK)

    # opening: White to move, every move lands on an empty square (no captures)
    s = game.initial_state()
    assert game.current_player(s) == 0
    assert all(">" in m for m in game.legal_moves(s)) and len(game.legal_moves(s)) > 0

    # pieces cannot capture: a rook is blocked by (not allowed to take) any piece
    nc = st({(0, 3): (0, "R"), (3, 3): (1, "B")}, king=(6, 4))
    rm = {m for m in game.legal_moves(nc) if m.startswith("0,3>")}
    assert "0,3>2,3" in rm and "0,3>3,3" not in rm and "0,3>4,3" not in rm

    # king is confined to ranks 3-5 (rows 2-4): from row 4 it cannot step to row 5
    kc = st({}, king=(3, 4))
    km = {m for m in game.legal_moves(kc) if m.startswith("3,4>")}
    assert "3,4>3,5" not in km and "3,4>3,3" in km and "3,4>2,4" in km

    # the king may not be moved into the opponent's attack ("own check"), but may
    # go to the borderline (safe) or into the mover's own zone
    oc = st({(0, 2): (1, "R")}, king=(3, 3), tm=0)   # black rook controls row 2
    lm = game.legal_moves(oc)
    assert "3,3>3,2" not in lm                        # into Black's attack -> illegal
    assert "3,3>3,4" in lm and "3,3>2,3" in lm        # White's zone / borderline -> ok

    # in check you must address the threat: a move that ignores it is illegal
    chk = st({(0, 2): (1, "R"), (6, 6): (0, "N")}, king=(3, 2), tm=0)
    lm = game.legal_moves(chk)
    assert not game.is_terminal(chk) and lm                 # the king can still flee to row 3
    assert not any(m.startswith("6,6>") for m in lm)        # the knight can't save it

    # capturing the king wins: White on row 4, Black on row 2
    ww = st({(0, 4): (0, "R")}, king=(3, 4), tm=0)
    assert game.is_terminal(ww) and game.returns(ww) == [1.0, -1.0]
    bw = st({(0, 2): (1, "R")}, king=(3, 2), tm=1)
    assert game.is_terminal(bw) and game.returns(bw) == [-1.0, 1.0]


def test_chess_conforms():
    manifest, game = _load("los_alamos_chess")
    assert check(game, manifest, games=15).ok


def test_full_chess_perft_and_special_moves():
    manifest, game = _load("chess")
    assert check(game, manifest, games=6).ok

    # perft: leaf-node counts from the opening must match the known values --
    # the gold standard for move-generation correctness (castling/ep/promotion).
    def perft(s, d):
        return 1 if d == 0 else sum(perft(game.apply_move(s, m), d - 1)
                                    for m in game.legal_moves(s))
    s0 = game.initial_state()
    assert perft(s0, 1) == 20
    assert perft(s0, 2) == 400
    assert perft(s0, 3) == 8902

    def st(board, **kw):
        d = {"board": board, "to_move": 0, "castling": "", "ep": None,
             "halfmove": 0, "ply": 0, "reps": {}}
        d.update(kw)
        return game.deserialize(d)

    # castling: both rooks home, nothing between -> O-O and O-O-O available
    cs = st({"4,0": [0, "K"], "0,0": [0, "R"], "7,0": [0, "R"], "4,7": [1, "K"]},
            castling="KQ")
    lm = game.legal_moves(cs)
    assert "4,0>6,0" in lm and "4,0>2,0" in lm
    after = game.apply_move(cs, "4,0>6,0").board
    assert after[(6, 0)] == (0, "K") and after[(5, 0)] == (0, "R") and (7, 0) not in after

    # en passant: black pawn just double-stepped d7-d5; ep target d6 (3,5),
    # the pawn that may be captured is on d5 (3,4)  -> unified "target,captured".
    ep = st({"4,4": [0, "P"], "3,4": [1, "P"], "4,0": [0, "K"], "4,7": [1, "K"]},
            ep="3,5,3,4")
    assert "4,4>3,5" in game.legal_moves(ep)
    eb = game.apply_move(ep, "4,4>3,5").board
    assert eb[(3, 5)] == (0, "P") and (3, 4) not in eb   # captured pawn removed

    # promotion: four choices, and =N really makes a knight
    pr = st({"0,6": [0, "P"], "4,0": [0, "K"], "7,7": [1, "K"]})
    promos = [m for m in game.legal_moves(pr) if m.startswith("0,6>0,7")]
    assert sorted(promos) == ["0,6>0,7=B", "0,6>0,7=N", "0,6>0,7=Q", "0,6>0,7=R"]
    assert game.apply_move(pr, "0,6>0,7=N").board[(0, 7)] == (0, "N")

    # fool's mate: 1. f3 e5 2. g4 Qh4#  -> Black (player 1) wins by checkmate
    s = game.initial_state()
    for mv in ("5,1>5,2", "4,6>4,4", "6,1>6,3", "3,7>7,3"):
        s = game.apply_move(s, mv)
    assert game.is_terminal(s) and game.returns(s) == [-1.0, 1.0]


def test_berolina_pawns():
    manifest, game = _load("berolina")
    assert check(game, manifest, games=6).ok

    def st(pieces, **kw):
        d = {"board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in pieces.items()},
             "to_move": 0, "castling": "", "ep_to": None, "ep_cap": None,
             "halfmove": 0, "ply": 0, "reps": {}}
        d.update(kw)
        return game.deserialize(d)

    # Berolina pawn moves diagonally (1 or 2 on first move), never straight when quiet.
    s0 = game.initial_state()
    e2 = {m for m in game.legal_moves(s0) if m.startswith("4,1>")}
    assert e2 == {"4,1>3,2", "4,1>5,2", "4,1>2,3", "4,1>6,3"}  # d3,f3 + c4,g4
    assert "4,1>4,2" not in e2 and "4,1>4,3" not in e2          # never straight (quiet)

    # captures STRAIGHT, not diagonally: e4 can take e5 (straight) but not d5 (diagonal)
    cap = st({(4, 3): (0, "P"), (4, 4): (1, "P"), (3, 4): (1, "P"),
              (4, 0): (0, "K"), (4, 7): (1, "K")})
    cm = {m for m in game.legal_moves(cap) if m.startswith("4,3>")}
    assert "4,3>4,4" in cm        # straight capture
    assert "4,3>3,4" not in cm    # cannot capture the diagonal enemy
    assert "4,3>5,4" in cm        # but may move onto the empty diagonal square

    # a pawn gives check STRAIGHT ahead, not diagonally
    chk = st({(4, 4): (1, "K"), (4, 3): (0, "P"), (0, 0): (0, "K")}, to_move=1)
    assert "(check)" in game.render(chk)["caption"]            # e4 pawn checks e5 king
    no = st({(3, 4): (1, "K"), (4, 3): (0, "P"), (0, 0): (0, "K")}, to_move=1)
    assert "(check)" not in game.render(no)["caption"]         # diagonal: no check

    # en passant on the diagonal double-step (the chessvariants example): black b4,
    # white a2-c4 passing b3; black captures b4xb3, removing the c4 pawn.
    ep = st({(0, 1): (0, "P"), (1, 3): (1, "P"), (4, 0): (0, "K"), (4, 7): (1, "K")})
    ep = game.apply_move(ep, "0,1>2,3")                        # a2 -> c4 (diagonal double)
    assert "1,3>1,2" in game.legal_moves(ep)                  # b4 may capture e.p. to b3
    ep = game.apply_move(ep, "1,3>1,2")
    b = game.serialize(ep)["board"]
    assert b.get("1,2") == [1, "P"] and "2,3" not in b         # pawn on b3, c4 removed


def test_checkers_conforms():
    manifest, game = _load("checkers")
    assert check(game, manifest, games=20).ok


def test_foxsox_conforms_and_geometry():
    manifest, game = _load("foxsox")
    assert check(game, manifest, games=15).ok
    for n, want in [(4, 32), (5, 50), (9, 162)]:
        s = game.initial_state(options={"size": n})
        cells = game.render(s)["board"]["cells"]
        assert len(cells) == 2 * n * n == want         # rhombus of triangles
        assert all(len(c["points"]) == 3 for c in cells)  # triangular cells
        assert game.current_player(s) == 0             # geese move first
    # fox reaching the goal corner wins (returns favour the fox = player 1)
    fw = game.deserialize({"size": 4, "board": {"3,3": 1, "5,2": 0}, "to_move": 1,
                           "winner": None, "drawn": False, "ply": 0})
    assert game.apply_move(fw, "3,3>2,2").winner == 1


def test_goose_chase_conforms_and_geometry():
    manifest, game = _load("goose_chase")
    assert check(game, manifest, games=15).ok
    # cell counts per board match the ZRF; every cell renders as a pentagon
    want = {"2x2": 16, "3x2": 24, "3x3": 36, "4x3": 40,
            "4x4": 64, "5x4": 60, "5x5": 100, "6x5": 84}
    for board, n in want.items():
        s = game.initial_state(options={"board": board})
        cells = game.render(s)["board"]["cells"]
        assert len(cells) == n
        assert all(len(c["points"]) == 5 for c in cells)
        assert game.current_player(s) == 0  # geese move first
    # cell ids are numeric "col,row" coords (2x2: D9=3,2  E11=4,0  B8=1,3
    # C6=2,5  E5=4,6  B4=1,7  A6=0,5  E1=4,10); the ZRF label shows in the log.
    # The fox reaching the goal cell wins (returns favour the fox = player 1).
    fw = game.deserialize({"board_key": "2x2", "board": {"3,2": 1, "1,3": 0},
                           "to_move": 1, "winner": None, "drawn": False, "ply": 0})
    nxt = game.apply_move(fw, "3,2>4,0")  # D9 -> E11 (the goal)
    assert nxt.winner == 1 and game.returns(nxt) == [-1.0, 1.0]
    assert game.describe_move(fw, "3,2>4,0") == "F D9-E11"
    # geese move only sideways/away from the goal (never toward a lower row index)
    gg = game.deserialize({"board_key": "2x2", "board": {"4,10": 1, "2,5": 0},
                           "to_move": 0, "winner": None, "drawn": False, "ply": 0})
    assert set(game.legal_moves(gg)) == {"2,5>4,6", "2,5>1,7", "2,5>0,5"}


def test_fox_and_hounds_conforms_and_asymmetry():
    manifest, game = _load("fox_and_hounds")
    assert check(game, manifest, games=30).ok
    s = game.initial_state()
    assert game.current_player(s) == 0  # fox moves first
    # hounds move only forward (never to a lower row)
    h = game.deserialize({"board": {"1,0": 1, "4,7": 0}, "to_move": 1,
                          "winner": None, "drawn": False, "ply": 0})
    assert set(game.legal_moves(h)) == {"1,0>2,1", "1,0>0,1"}
    # fox reaching row 0 wins
    fw = game.deserialize({"board": {"1,1": 0, "3,0": 1}, "to_move": 0,
                           "winner": None, "drawn": False, "ply": 0})
    assert game.apply_move(fw, "1,1>0,0").winner == 0


def test_loa_conforms_and_option():
    manifest, game = _load("lines_of_action")
    assert check(game, manifest, games=12, seed=1).ok
    assert len(game.legal_moves(game.initial_state())) == 36  # known LOA opening count
    # sim_connection option: a move connecting both is a draw, or a win for mover
    b = {"board": {"3,3": 0, "5,3": 1}, "to_move": 0, "winner": None, "drawn": False, "ply": 0}
    draw = game.apply_move(game.deserialize({**b, "sim_win": False}), "3,3>5,3")
    win = game.apply_move(game.deserialize({**b, "sim_win": True}), "3,3>5,3")
    assert draw.drawn and draw.winner is None
    assert win.winner == 0 and not win.drawn


def test_hex_conforms_and_never_draws():
    manifest, game = _load("hex")
    assert check(game, manifest, games=20, seed=3).ok
    rng = random.Random(5)
    for _ in range(20):
        res = play_match(game, [RandomBot(rng), RandomBot(rng)], rng, options={"size": 7})
        assert res["result"] == "terminal" and 0.0 not in res["returns"]  # Hex can't draw


def test_checkers_forced_capture_and_multijump():
    _, game = _load("checkers")
    # a man with a jump available -> only the jump is legal; a double jump is one path
    s = game.deserialize({"board": {"1,1": [0, "m"], "2,2": [1, "m"], "2,4": [1, "m"],
                                    "0,0": [0, "k"], "7,7": [1, "k"]},
                          "to_move": 0, "halfmove": 0, "ply": 0})
    moves = game.legal_moves(s)
    assert all("x" not in m and ">" in m for m in moves)  # all are jumps (paths)
    assert "1,1>3,3>1,5" in moves  # the double jump as a single path


def test_oust_never_draws():
    # The official rules state draws cannot occur.
    _, game = _load("oust")
    rng = random.Random(7)
    for _ in range(60):
        res = play_match(game, [RandomBot(rng), RandomBot(rng)], rng,
                         options={"size": 4})
        assert res["result"] == "terminal"
        assert 0.0 not in res["returns"]  # someone always wins


def test_tictactoe_mcts_never_loses_as_x():
    # TTT is a draw under perfect play; a sound MCTS as X must never lose.
    _, game = _load("tic_tac_toe")
    rng = random.Random(1)
    for _ in range(12):
        res = play_match(game, [MCTSBot(rng, iterations=400), RandomBot(rng)], rng)
        assert res["returns"][0] >= 0.0  # X wins or draws, never loses


def test_freeform_mode():
    # A minimal unenforced game: an 8x8 board with two kings, no rules.
    from agp import FreeformGame

    class FreeformDemo(FreeformGame):
        uid = "freeform_demo"
        name = "Freeform Demo"
        WIDTH = HEIGHT = 8

        def setup_board(self):
            return {(4, 0): (0, "K"), (4, 7): (1, "K")}

    game = FreeformDemo()
    manifest = {"uid": "freeform_demo", "version": "0", "engine_api": "1",
                "players": {"min": 2, "max": 2}, "mode": "freeform"}
    assert check(game, manifest).ok

    s = game.initial_state()
    assert not game.is_terminal(s)
    assert game.legal_moves(s) == ["pass", "resign", "offer-draw"]

    # any piece can move anywhere, no legality, capturing what's there
    s2 = game.apply_move(s, "4,0>4,7")              # White king "captures" Black king
    assert (4, 7) in s2.board and s2.board[(4, 7)] == (0, "K")
    assert (4, 0) not in s2.board and s2.to_move == 1
    assert game.serialize(s) != game.serialize(s2)  # original untouched, new differs

    # promotion-as-relabel
    s3 = game.apply_move(s, "4,0>3,0=Q")
    assert s3.board[(3, 0)] == (0, "Q")

    # resign ends the game; the resigner (White) loses
    over = game.apply_move(s, "resign")
    assert game.is_terminal(over) and game.returns(over) == [-1.0, 1.0]

    # draw agreement: White offers, turn passes to Black who can accept
    off = game.apply_move(s, "offer-draw")
    assert off.to_move == 1 and off.draw_offer == 0
    assert game.legal_moves(off) == ["accept-draw", "decline-draw", "pass", "resign"]
    drawn = game.apply_move(off, "accept-draw")
    assert game.is_terminal(drawn) and game.returns(drawn) == [0.0, 0.0]
    # an ordinary move implicitly declines a pending offer
    moved = game.apply_move(off, "4,7>4,6")
    assert moved.draw_offer is None and not game.is_terminal(moved)


def test_parse_fen():
    from agp import parse_fen

    # the three documented encodings of the chess start are all equivalent
    a = parse_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR", 8)
    b = parse_fen("rnbqkbnrpppppppp32PPPPPPPPRNBQKBNR", 8)
    c = parse_fen("rnbqkbnr/pppppppp/****/PPPPPPPP/RNBQKBNR", 8)
    assert a == b == c
    assert len(a) == 32
    assert a[(0, 0)] == (0, "R") and a[(4, 0)] == (0, "K")   # White back rank, row 0
    assert a[(3, 7)] == (1, "q") and a[(0, 6)] == (1, "p")   # Black, top rows

    # multi-char {labels}; first-char case picks the player
    m = parse_fen("{NB}1{nb}", 3)
    assert m == {(0, 0): (0, "NB"), (2, 0): (1, "nb")}

    # "-" is a non-cell (hole), not an empty square -> omitted from the board
    h = parse_fen("R-r", 3)
    assert h == {(0, 0): (0, "R"), (2, 0): (1, "r")}

    # "/" before the natural end pads the rest of the rank with non-cells
    s = parse_fen("R/p", 3)   # rank "R" then end -> row1: R at col0; rank "p" -> row0
    assert s == {(0, 1): (0, "R"), (0, 0): (1, "p")}


def test_apply_move_is_pure():
    _, game = _load("oust")
    rng = random.Random(0)
    s = game.initial_state(options={"size": 4})
    before = game.serialize(s)
    game.apply_move(s, game.legal_moves(s)[0])
    assert game.serialize(s) == before


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all tests passed")
