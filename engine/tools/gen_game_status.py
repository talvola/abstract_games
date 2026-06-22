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
 "order_and_chaos": "conformance (exercises the =CHOICE picker)",
 "oust": "event-based win; never-draws check; conformance",
 "oware": "re-derived vs Awari; 2000-game seed-conservation proof",
 "pente": "custody-capture tests + conformance",
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
 "turkish_draughts": "40k-position + 489k jump-chain cross-check, 0 double-jumps",
 "wildebeest_chess": "review REJECTED+fixed castling ⇒ NoCastling",
 "xiangqi": "independent review + perft baseline; cannon hopper",
 "y": "selftest (three-edge connection win, the can-never-draw property verified over random full boards, swap/pie); shares the connection family with Hex",
 "yodd": "parity win; never-draws; conformance",
 "yote": "selftest (drop/step/jump, the bonus-removal double-capture, optional capture, annihilation/stuck win) + independent adversarial rule review",
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
 "fanorona": "✅ verified (alquerque connecting lines drawn)",
 "kalah": "✅ verified (mancala pits + counts, extra-turn after store landing)",
 "oware": "✅ verified (seed counts + own-row clicking correct)",
 "pentago": "✅ verified (quadrant divider lines + 8-option rotation picker)",
 "rolit": "✅ verified (NEW >2-seat UI — 4 player chips/colours, full P1→P4 round)",
 "chinese_checkers": "✅ verified (full 6-pointed star, all SIX seat colours, step+jump)",
 "xiangqi": "✅ verified (UI review: legible, uncramped)",
 "janggi": "✅ verified (UI review: legible, palace pieces correct)",
 "y": "✅ verified (NEW triangular-hex polygon board renders cleanly)",
 "yote": "✅ verified (5×6 board, drops with hand count, capture flow)",
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
