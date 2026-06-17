"""Load a game *package* (a directory or .zip) into a live ``Game`` instance.

Package layout::

    mygame/
      manifest.json     # metadata; "uid" must be unique and stable
      game.py           # defines the Game subclass
      rules.md          # optional
      assets/           # optional

Phase-0 trust model: packages come from trusted authors, so ``game.py`` is
imported in-process. The import is funneled through this one function so a real
sandbox (subprocess / WASM / container) can be slotted in later without
touching the rest of the platform.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import sys
import tempfile
import zipfile
from pathlib import Path

from .game import Game

MANIFEST_NAME = "manifest.json"
ENGINE_API = "1"

REQUIRED_MANIFEST_KEYS = ("uid", "name", "version", "engine_api", "players")


class PackageError(Exception):
    """Raised when a package is malformed or fails to load."""


def load_manifest(pkg_dir: Path) -> dict:
    mpath = pkg_dir / MANIFEST_NAME
    if not mpath.exists():
        raise PackageError(f"missing {MANIFEST_NAME} in {pkg_dir}")
    try:
        manifest = json.loads(mpath.read_text())
    except json.JSONDecodeError as e:
        raise PackageError(f"invalid {MANIFEST_NAME}: {e}") from e

    missing = [k for k in REQUIRED_MANIFEST_KEYS if k not in manifest]
    if missing:
        raise PackageError(f"{MANIFEST_NAME} missing keys: {', '.join(missing)}")
    if str(manifest["engine_api"]) != ENGINE_API:
        raise PackageError(
            f"engine_api {manifest['engine_api']!r} unsupported "
            f"(this engine speaks {ENGINE_API!r})"
        )
    return manifest


def _import_game_module(game_py: Path):
    # Unique module name so multiple packages can coexist in one process.
    mod_name = f"_agp_game_{abs(hash(str(game_py)))}"
    spec = importlib.util.spec_from_file_location(mod_name, game_py)
    if spec is None or spec.loader is None:
        raise PackageError(f"could not load {game_py}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:  # noqa: BLE001 - report any author error cleanly
        raise PackageError(f"error importing {game_py.name}: {e!r}") from e
    return module


def _find_game_class(module) -> type[Game]:
    candidates = [
        obj
        for _, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, Game) and obj is not Game and obj.__module__ == module.__name__
    ]
    if not candidates:
        raise PackageError("game.py defines no Game subclass")
    if len(candidates) > 1:
        names = ", ".join(c.__name__ for c in candidates)
        raise PackageError(f"game.py defines multiple Game subclasses: {names}")
    return candidates[0]


def load_from_dir(pkg_dir: Path) -> tuple[dict, Game]:
    """Load a package directory -> (manifest, game instance)."""
    pkg_dir = Path(pkg_dir)
    manifest = load_manifest(pkg_dir)
    game_py = pkg_dir / "game.py"
    if not game_py.exists():
        raise PackageError(f"missing game.py in {pkg_dir}")

    module = _import_game_module(game_py)
    game_cls = _find_game_class(module)
    game = game_cls()

    if not game.uid:
        game.uid = manifest["uid"]
    if not game.name:
        game.name = manifest["name"]
    if game.uid != manifest["uid"]:
        raise PackageError(
            f"uid mismatch: manifest {manifest['uid']!r} vs game {game.uid!r}"
        )
    return manifest, game


def load(path) -> tuple[dict, Game]:
    """Load a package from a directory or a .zip file."""
    path = Path(path)
    if path.is_dir():
        return load_from_dir(path)
    if path.suffix == ".zip" and zipfile.is_zipfile(path):
        tmp = Path(tempfile.mkdtemp(prefix="agp_pkg_"))
        with zipfile.ZipFile(path) as zf:
            zf.extractall(tmp)
        # Allow either a flat zip or a single top-level folder.
        roots = [p for p in tmp.iterdir() if p.is_dir()]
        if (tmp / MANIFEST_NAME).exists():
            return load_from_dir(tmp)
        if len(roots) == 1 and (roots[0] / MANIFEST_NAME).exists():
            return load_from_dir(roots[0])
        raise PackageError(f"no {MANIFEST_NAME} found in zip {path}")
    raise PackageError(f"not a package directory or .zip: {path}")
