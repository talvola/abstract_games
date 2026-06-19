#!/usr/bin/env python3
"""Emit a freeform (unenforced) Abstract Games Platform package from a Game
Courier settings file — the automatable, no-GAME-Code import path (see SKILL.md
§7 and engine/FREEFORM_MODE.md).

A Game Courier settings file is a PHP blob of ``$default['key'] = …`` assignments.
Only the *declarative* keys are needed for a freeform board: ``code`` (extended
FEN), ``cols`` (board width), ``game`` (name), and optionally ``files``/``ranks``
labels and ``rulesurl``. Movement/rule GAME Code is deliberately ignored — a
freeform board has no rules.

Usage:
    # from a saved settings file (retrieved via showsource.php, see SKILL.md §1)
    python3 freeform_from_settings.py --settings univers.php

    # or pass the position directly
    python3 freeform_from_settings.py --code "rbnmqkanbr/pppppppppp/****/PPPPPPPPPP/RBNMQKANBR" \
        --cols 10 --name "Univers Chess" --rules-url chess/univers.html

Writes manifest.json + game.py + rules.md into engine/games/<uid>/ (override with
--out). Square boards only; hex/circular/custom shapes are rejected with guidance
(those need a human — see SKILL.md "When to pause and ask").
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Import the engine's extended-FEN parser so this tool and the emitted package
# agree on geometry exactly (and so we can validate the parse up front).
ENGINE = Path(__file__).resolve().parents[3] / "engine"
sys.path.insert(0, str(ENGINE))
from agp.freeform import parse_fen  # noqa: E402


def extract(php: str, key: str) -> str | None:
    """Pull one ``$default['key']`` value (heredoc/nowdoc or quoted scalar)."""
    here = re.search(
        rf"\$default\[['\"]{key}['\"]\]\s*=\s*<<<'?(\w+)'?\r?\n(.*?)\r?\n\1\s*;",
        php, re.DOTALL,
    )
    if here:
        return here.group(2).strip()
    quoted = re.search(
        rf"\$default\[['\"]{key}['\"]\]\s*=\s*(['\"])(.*?)\1\s*;", php, re.DOTALL
    )
    return quoted.group(2).strip() if quoted else None


def author_of(php: str) -> str | None:
    m = re.search(r"\$author\s*=\s*(['\"])(.*?)\1", php)
    return m.group(2) if m else None


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "imported_game"


def class_name(uid: str) -> str:
    return "".join(p.capitalize() for p in uid.split("_")) or "ImportedGame"


def source_url(rules_url: str | None) -> str | None:
    if not rules_url:
        return None
    if rules_url.startswith(("http://", "https://")):
        return rules_url
    return "https://www.chessvariants.com/" + rules_url.lstrip("/")


def build(code: str, cols: int, name: str, uid: str, author: str | None,
          rules_url: str | None) -> dict:
    board = parse_fen(code, cols)          # validates the FEN; raises on garbage
    if not board:
        raise SystemExit("error: parsed an empty board — check --code / --cols")
    height = max(r for _, r in board) + 1
    src = source_url(rules_url)

    manifest = {
        "uid": uid,
        "name": name,
        "version": "1.0.0",
        "engine_api": "1",
        "author": f"{author + ' / ' if author else ''}imported from Game Courier",
        "mode": "freeform",
        "players": {"min": 2, "max": 2},
        "has_randomness": False,
        "hidden_info": False,
        "category": "Sandbox",
        "tags": ["freeform", "sandbox", "import"],
        **({"bgg_url": src} if src else {}),
        "description": (
            f"{name}, imported from Game Courier as an UNENFORCED board: the "
            f"{cols}×{height} opening position is set up, but no rules are "
            "checked — either player may move, capture, or remove any piece on "
            "the honor system. End by resigning or agreeing a draw. There is no "
            "computer opponent."
        ),
    }

    game_py = f'''"""{name} — imported from Game Courier as a freeform (unenforced) board.

{('Source: ' + src) if src else 'Source: Game Courier (chessvariants.com)'}
Only the board + opening position were imported; Game Courier's rule code is not
translated (a freeform board enforces nothing). To make this a fully-enforced
game, port it to a ChessLike/Game module instead (see the skill).
"""

from agp.freeform import FreeformGame, parse_fen

CODE = "{code}"


class {class_name(uid)}(FreeformGame):
    uid = "{uid}"
    name = "{name}"
    WIDTH = {cols}
    HEIGHT = {height}

    def setup_board(self):
        return parse_fen(CODE, self.WIDTH)
'''

    rules_md = f"""# {name}

This board was imported from **Game Courier** as an **unenforced** (honor-system)
sandbox: the opening position is set up on a {cols}×{height} board, but the
platform checks **no rules** — no legal-move highlighting, no captures logic, no
win detection.

- On your turn, drag any piece to any square (whatever is there is captured).
  Moves are not checked — you and your opponent agree on and police the rules.
- Use **Pass** to hand over the turn, **Resign** to concede, or **Offer draw**
  (the opponent may Accept or Decline).

{('See the original rules: ' + src) if src else ''}

> Imported board + setup only. For a fully-enforced version, port it to a
> `ChessLike`/`Game` module.
"""

    return {"manifest": manifest, "game.py": game_py, "rules.md": rules_md}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--settings", help="path to a Game Courier settings .php file")
    ap.add_argument("--code", help="extended FEN (overrides the settings file)")
    ap.add_argument("--cols", type=int, help="board width (files)")
    ap.add_argument("--name", help="game name")
    ap.add_argument("--uid", help="package uid (default: slug of the name)")
    ap.add_argument("--rules-url", help="rules page (relative to chessvariants.com or absolute)")
    ap.add_argument("--out", help="output dir (default: engine/games/<uid>)")
    ap.add_argument("--shape", default="", help="GC shape; only square is supported")
    args = ap.parse_args(argv)

    php = ""
    if args.settings:
        php = Path(args.settings).read_text(encoding="utf-8", errors="ignore")

    code = args.code or (extract(php, "code") if php else None)
    cols = args.cols or (int(c) if php and (c := extract(php, "cols")) else None)
    name = args.name or (extract(php, "game") if php else None)
    rules_url = args.rules_url or (extract(php, "rulesurl") if php else None)
    author = author_of(php) if php else None
    shape = (args.shape or (extract(php, "shape") if php else "") or "").lower()

    if not code or not cols or not name:
        ap.error("need code, cols, and name (from --settings or --code/--cols/--name)")
    if shape and "square" not in shape:
        ap.error(f"shape {shape!r} is not a square board — hex/circular/custom "
                 "boards need a hand port (see SKILL.md 'When to pause and ask')")

    uid = args.uid or slug(name)
    out = Path(args.out) if args.out else ENGINE / "games" / uid
    files = build(code, cols, name, uid, author, rules_url)

    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(files["manifest"], indent=2) + "\n")
    (out / "game.py").write_text(files["game.py"])
    (out / "rules.md").write_text(files["rules.md"])
    print(f"wrote {uid} -> {out}")
    print(f"  validate: cd engine && PYTHONPATH=. python3 -m agp.cli validate games/{uid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
