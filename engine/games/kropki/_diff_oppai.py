"""One-time differential: kropki vs the pointsgame reference engine oppai-rs.

oppai-rs (https://github.com/pointsgame/oppai-rs, AGPL) implements the same
"no-territory" Russian Dots ruleset (СКСТ / zagram); its `field` crate is the
ground truth here. We drive a tiny stdin/stdout harness around
`oppai_field::Field` in lockstep with our engine down random game lines and
compare, after EVERY move: move legality, both capture scores, and the FULL
board state (per cell: live/dead dot + owner, painted territory + painter,
empty-base mark + owner, playability).

MANUAL / ONE-TIME -- deliberately NOT a selftest.py (selftests must be pure
stdlib with no external binaries). oppai-rs code is never copied into the
package; it is used strictly as an external test oracle.

Setup (Rust toolchain required):

    git clone --depth 1 https://github.com/pointsgame/oppai-rs.git /tmp/oppai-rs
    mkdir -p /tmp/oppai-harness/src
    python3 _diff_oppai.py --write-harness /tmp/oppai-harness   # emits Cargo.toml + main.rs
    # edit /tmp/oppai-harness/Cargo.toml if oppai-rs is not at ../oppai-rs
    (cd /tmp/oppai-harness && cargo build --release)
    OPPAI_HARNESS=/tmp/oppai-harness/target/release/oppai-harness \
        python3 _diff_oppai.py

Cell-char protocol (must match the harness): 'X'/'x' red live/dead dot,
'O'/'o' blue(black) live/dead dot, 'R'/'K' cell painted by red/black,
'r'/'k' empty-base mark of red/black, '.' plain empty.

Last run (2026-07-16): 80 random games played to a full board across
8x8 / 10x10 / 13x13 / 20x20, empty and cross starts -- 10,731 moves, 10,811
full-board state comparisons (>1.3M cell states) + a score comparison after
every move, 0 mismatches; final winners agreed 80/80. (The default `main()`
sweep is a 24-game subset of that.)
"""

import os
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # -> engine/
from agp.loader import load_from_dir  # noqa: E402

HARNESS = os.environ.get("OPPAI_HARNESS", "")

HARNESS_CARGO = """\
[package]
name = "oppai-harness"
version = "0.1.0"
edition = "2021"

[dependencies]
oppai-field = { path = "../oppai-rs/field" }
rand = "0.10"
rand_xoshiro = "0.8"
"""

HARNESS_MAIN = r'''
// Tiny stdin/stdout oracle around oppai_field::Field (test harness only).
use oppai_field::field::Field;
use oppai_field::player::Player;
use rand::SeedableRng;
use rand_xoshiro::Xoshiro256PlusPlus;
use std::io::{self, BufRead, Write};

fn cell_char(f: &Field, x: u32, y: u32) -> char {
  let cell = f.cell(f.to_pos(x, y));
  if cell.is_put() {
    match (cell.get_player(), cell.is_captured()) {
      (Player::Red, false) => 'X',
      (Player::Red, true) => 'x',
      (Player::Black, false) => 'O',
      (Player::Black, true) => 'o',
    }
  } else if cell.is_captured() {
    match cell.get_player() { Player::Red => 'R', Player::Black => 'K' }
  } else if cell.is_empty_base() {
    match cell.get_empty_base_player().unwrap() { Player::Red => 'r', Player::Black => 'k' }
  } else { '.' }
}

fn main() {
  let stdin = io::stdin();
  let stdout = io::stdout();
  let mut out = stdout.lock();
  let mut field: Option<Field> = None;
  let mut rng = Xoshiro256PlusPlus::seed_from_u64(7);
  for line in stdin.lock().lines() {
    let line = line.unwrap();
    let parts: Vec<&str> = line.split_whitespace().collect();
    match parts.as_slice() {
      ["new", w, h] => {
        field = Some(Field::new_from_rng(w.parse().unwrap(), h.parse().unwrap(), &mut rng));
        writeln!(out, "ok").unwrap();
      }
      ["put", x, y, p] => {
        let f = field.as_mut().unwrap();
        let player = if p == &"1" { Player::Black } else { Player::Red };
        let pos = f.to_pos(x.parse().unwrap(), y.parse().unwrap());
        if f.put_point(pos, player) {
          writeln!(out, "ok {} {}", f.captured_count(Player::Red), f.captured_count(Player::Black)).unwrap();
        } else { writeln!(out, "illegal").unwrap(); }
      }
      ["dump"] => {
        let f = field.as_ref().unwrap();
        for y in 0..f.height() {
          let row: String = (0..f.width()).map(|x| cell_char(f, x, y)).collect();
          writeln!(out, "{}", row).unwrap();
        }
        writeln!(out, "end").unwrap();
      }
      ["quit"] => break,
      [] => {}
      _ => writeln!(out, "err unknown").unwrap(),
    }
    out.flush().unwrap();
  }
}
'''


def write_harness(dest):
    dest = Path(dest)
    (dest / "src").mkdir(parents=True, exist_ok=True)
    (dest / "Cargo.toml").write_text(HARNESS_CARGO)
    (dest / "src" / "main.rs").write_text(HARNESS_MAIN)
    print(f"harness source written to {dest}; point [dependencies].oppai-field "
          f"at your oppai-rs checkout and `cargo build --release`.")


class Oracle:
    def __init__(self):
        if not HARNESS or not Path(HARNESS).exists():
            raise SystemExit("set $OPPAI_HARNESS to the built harness binary "
                             "(see module docstring)")
        self.p = subprocess.Popen([HARNESS], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, bufsize=1)

    def cmd(self, c):
        self.p.stdin.write(c + "\n")
        self.p.stdin.flush()
        return self.p.stdout.readline().strip()

    def new(self, w, h):
        assert self.cmd(f"new {w} {h}") == "ok"
        self.h = h

    def put(self, x, y, player):
        r = self.cmd(f"put {x} {y} {player}")
        if r == "illegal":
            return None
        _, sr, sb = r.split()
        return int(sr), int(sb)

    def dump(self):
        self.p.stdin.write("dump\n")
        self.p.stdin.flush()
        rows = []
        while True:
            line = self.p.stdout.readline().rstrip("\n")
            if line == "end":
                return rows
            rows.append(line)


# our flag bits (keep in sync with game.py)
PLAYER, PUT, CAP, BASE = 1, 2, 4, 16


def our_dump(g, s):
    """Render our state in the oracle's cell-char format (internal y = top)."""
    stride = s.w + 1
    rows = []
    for y in range(s.h):
        row = []
        for x in range(s.w):
            f = s.cells[(y + 1) * stride + x + 1]
            if f & PUT:
                ch = "XO"[f & PLAYER] if not f & CAP else "xo"[f & PLAYER]
            elif f & CAP:
                ch = "RK"[f & PLAYER]
            elif f & BASE:
                ch = "rk"[f & PLAYER]
            else:
                ch = "."
            row.append(ch)
        rows.append("".join(row))
    return rows


def run_game(g, oracle, w, h, cross, seed):
    rng = random.Random(seed)
    size = f"{w}x{h}"
    s = g.initial_state(options={"size": size,
                                 "start": "cross" if cross else "empty"})
    oracle.new(w, h)
    if cross:
        w2, h2 = w // 2, h // 2
        for (x, y), p in (((w2 - 1, h2 - 1), 0), ((w2 - 1, h2), 1),
                          ((w2, h2), 0), ((w2, h2 - 1), 1)):
            assert oracle.put(x, y, p) is not None
    moves = comps = 0
    while True:
        theirs = oracle.dump()
        ours = our_dump(g, s)
        comps += 1
        if ours != theirs:
            print(f"STATE MISMATCH {size} cross={cross} seed={seed} ply {s.ply}")
            for a, b in zip(ours, theirs):
                print(f"  {a}   {b}" + ("   <<<" if a != b else ""))
            return None
        placements = [m for m in g.legal_moves(s) if m != "pass"]
        if not placements:
            break
        mv = rng.choice(placements)
        c, r = map(int, mv.split(","))
        res = oracle.put(c, h - 1 - r, g.current_player(s))
        s = g.apply_move(s, mv)
        moves += 1
        if res is None:
            print(f"LEGALITY MISMATCH {size} seed={seed}: oracle rejects {mv}")
            return None
        if list(res) != list(s.scores):
            print(f"SCORE MISMATCH {size} cross={cross} seed={seed} ply {s.ply}: "
                  f"ours={s.scores} oracle={list(res)} after {mv}")
            for a, b in zip(our_dump(g, s), oracle.dump()):
                print(f"  {a}   {b}" + ("   <<<" if a != b else ""))
            return None
    sr, sb = s.scores
    winner = 0 if sr > sb else (1 if sb > sr else None)
    assert g.is_terminal(s)
    ret = g.returns(s)
    exp = [0.0, 0.0] if winner is None else ([1.0, -1.0] if winner == 0 else [-1.0, 1.0])
    assert ret == exp, (ret, exp)
    return moves, comps, s.scores


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--write-harness":
        write_harness(sys.argv[2])
        return 0
    g = load_from_dir(Path(__file__).resolve().parent)[1]
    oracle = Oracle()
    total_m = total_c = games = 0
    for w, h in ((8, 8), (10, 10), (13, 13)):
        for cross in (False, True):
            for seed in range(4):
                res = run_game(g, oracle, w, h, cross, seed * 31 + w)
                if res is None:
                    return 1
                m, c, sc = res
                total_m += m
                total_c += c
                games += 1
                print(f"  {w}x{h} cross={int(cross)} seed{seed}: OK, "
                      f"{m} moves, final {sc[0]}-{sc[1]}")
    print(f"DIFFERENTIAL OK — {games} full games, {total_m} moves, "
          f"{total_c} full-board comparisons, 0 mismatches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
