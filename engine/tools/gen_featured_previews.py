"""Write web/public/featured-previews.json: one RenderSpec per game on the
landing page's "Start here" shelf (web/src/featured.js), so the shelf can draw a
real board thumbnail with the generic Board component — with no API calls and no
server CPU per visitor.

A game whose start position is (nearly) empty — Go, Hex, Connect Four — gets a
few seeded random plies first, so its tile shows stones rather than a bare grid.
Deterministic (fixed seeds), so the file only changes when a game's render does.

Run from the repo root (build.sh does this on every deploy):
    python3 engine/tools/gen_featured_previews.py
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "engine"))

from agp.loader import load_from_dir  # noqa: E402

FEATURED_JS = ROOT / "web" / "src" / "featured.js"
OUT = ROOT / "web" / "public" / "featured-previews.json"
MIN_PIECES = 4      # fewer pieces than this at the start ⇒ play a few plies
PLIES = 8


def featured_uids() -> list[str]:
    src = FEATURED_JS.read_text()
    block = re.search(r"FEATURED\s*=\s*\[(.*?)\]", src, re.S).group(1)
    return re.findall(r"'([a-z0-9_]+)'", block)


def preview(uid: str) -> dict | None:
    pkg = ROOT / "engine" / "games" / uid
    if not (pkg / "manifest.json").exists():
        return None
    _, game = load_from_dir(pkg)
    rng = random.Random(7)
    state = game.initial_state(rng=rng)
    if len(game.render(state).get("pieces", [])) < MIN_PIECES:
        for _ in range(PLIES):
            if game.is_terminal(state):
                break
            moves = [m for m in game.legal_moves(state) if m not in ("pass", "swap")]
            if not moves:
                break
            state = game.apply_move(state, rng.choice(moves), rng=rng)
    spec = game.render(state)
    # A thumbnail shows the board only: no captions, trays, cards or previews.
    for k in ("caption", "highlights", "reserve", "palette", "moveTargets"):
        spec.pop(k, None)
    spec.get("board", {}).pop("cards", None)   # Onitama's card strip
    return spec


def main() -> None:
    out = {}
    for uid in featured_uids():
        spec = preview(uid)
        if spec is not None:
            out[uid] = spec
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(f"gen_featured_previews: {len(out)} previews -> {OUT.relative_to(ROOT)} "
          f"({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
