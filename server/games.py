"""Engine integration: a reloadable game registry (bundled + uploaded games)
plus the helpers that drive a stored Match through the engine and the upload
pipeline (extract -> validate in a subprocess -> install -> hot-register).

Trust note: per the project's deferred-sandbox decision, uploaded game code is
trusted-ish. We still run validation in a *separate process* with a timeout so a
broken or hostile module can't wedge the server during validation, and we guard
against zip-slip on extraction. Real isolation (container/WASM) is future work.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"
sys.path.insert(0, str(ENGINE))

from agp import MCTSBot, PackageError, load  # noqa: E402
from agp.loader import MANIFEST_NAME, load_manifest  # noqa: E402

BUNDLED_DIR = ENGINE / "games"
UPLOAD_DIR = Path(os.environ.get("AGP_UPLOAD_DIR", ROOT / "data" / "games"))

# SECURITY — uploads are remote code execution.
# A registered game's game.py is imported and executed IN-PROCESS by this API
# server (on registry.reload() and on every move). There is no sandbox yet
# (see PLATFORM_PLAN.md "Future: sandboxing"). Until one exists, uploading a
# package == running arbitrary code on the server, so uploads are restricted to
# trusted operators and CLOSED BY DEFAULT:
#   * AGP_ADMIN_EMAILS="a@x,b@y"  -> only those signed-in users may upload.
#   * AGP_ALLOW_OPEN_UPLOADS=true -> (no allowlist) any signed-in user may
#       upload. Knowingly unsafe; only for a fully trusted/local instance.
# With neither set, uploads are denied even for authenticated users.
ADMIN_EMAILS = {
    e.strip().lower() for e in os.environ.get("AGP_ADMIN_EMAILS", "").split(",") if e.strip()
}
OPEN_UPLOADS = os.environ.get("AGP_ALLOW_OPEN_UPLOADS", "false").lower() == "true"


def can_upload(email: str) -> bool:
    email = (email or "").lower()
    if ADMIN_EMAILS:
        return email in ADMIN_EMAILS
    return OPEN_UPLOADS


def uploads_enabled() -> bool:
    return bool(ADMIN_EMAILS) or OPEN_UPLOADS


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_UPLOAD_FILES = 200
META_NAME = ".agp_meta.json"

_rng = random.Random()


class Registry:
    """Loads every package under the bundled and upload dirs. Reloadable so an
    upload appears without a server restart."""

    def __init__(self):
        self.entries: dict[str, dict] = {}
        self.reload()

    def reload(self) -> None:
        entries: dict[str, dict] = {}
        for source, base in (("bundled", BUNDLED_DIR), ("uploaded", UPLOAD_DIR)):
            if not base.exists():
                continue
            for pkg in sorted(p for p in base.iterdir() if p.is_dir()):
                try:
                    manifest, game = load(pkg)
                except PackageError as e:
                    print(f"skip {pkg}: {e}", file=sys.stderr)
                    continue
                meta = _read_meta(pkg)
                entries[manifest["uid"]] = {
                    "manifest": manifest,
                    "game": game,
                    "source": source,
                    "path": pkg,
                    "uploader": meta.get("uploader_name"),
                }
        self.entries = entries

    def get(self, uid: str):
        entry = self.entries.get(uid)
        if entry is None:
            raise HTTPException(404, f"unknown game {uid!r}")
        return entry["manifest"], entry["game"]


def _read_meta(pkg: Path) -> dict:
    p = pkg / META_NAME
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            return {}
    return {}


registry = Registry()


# ===========================================================================
#  upload pipeline
# ===========================================================================
def _safe_extract(zip_path: Path, dest: Path) -> None:
    """Extract a zip, refusing path traversal (zip-slip) and oversized archives."""
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
        if len(infos) > MAX_UPLOAD_FILES:
            raise HTTPException(400, "archive has too many files")
        total = 0
        for info in infos:
            total += info.file_size
            if total > 4 * MAX_UPLOAD_BYTES:
                raise HTTPException(400, "archive expands too large")
            target = (dest / info.filename).resolve()
            if not str(target).startswith(str(dest.resolve())):
                raise HTTPException(400, "unsafe path in archive")
        zf.extractall(dest)


def _resolve_pkg_root(extracted: Path) -> Path:
    """Find the directory containing manifest.json (flat zip or single folder)."""
    if (extracted / MANIFEST_NAME).exists():
        return extracted
    subdirs = [p for p in extracted.iterdir() if p.is_dir() and not p.name.startswith("_")]
    for d in subdirs:
        if (d / MANIFEST_NAME).exists():
            return d
    raise HTTPException(400, f"no {MANIFEST_NAME} found in archive")


def _validate_in_subprocess(pkg_root: Path) -> tuple[bool, str]:
    """Run `agp validate` in a child process with a timeout (isolation-lite)."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "agp.cli", "validate", str(pkg_root), "--games", "30"],
            cwd=str(ENGINE),
            env={**os.environ, "PYTHONPATH": str(ENGINE)},
            capture_output=True,
            text=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired:
        return False, "validation timed out (the game may not terminate)"
    return proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")


def install_upload(zip_bytes: bytes, uploader_id: int, uploader_name: str) -> dict:
    """Validate and install an uploaded game package. Returns its manifest.
    Raises HTTPException with a helpful message on any failure.

    NOTE: the caller (route) is responsible for authorizing the uploader via
    can_upload(); this function trusts that check has passed."""
    if len(zip_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "upload too large (max 5 MB)")

    tmp = Path(tempfile.mkdtemp(prefix="agp_upload_"))
    try:
        zip_path = tmp / "pkg.zip"
        zip_path.write_bytes(zip_bytes)
        if not zipfile.is_zipfile(zip_path):
            raise HTTPException(400, "not a valid .zip file")
        extracted = tmp / "x"
        extracted.mkdir()
        _safe_extract(zip_path, extracted)
        pkg_root = _resolve_pkg_root(extracted)

        manifest = load_manifest(pkg_root)  # validates required keys + engine_api
        uid = manifest["uid"]
        existing = registry.entries.get(uid)
        if existing and existing["source"] == "bundled":
            raise HTTPException(409, f"{uid!r} is a built-in game and cannot be overwritten")

        ok, report = _validate_in_subprocess(pkg_root)
        if not ok:
            raise HTTPException(422, "conformance validation failed:\n" + report[-2000:])

        # Install: replace any prior upload of this uid.
        dest = UPLOAD_DIR / uid
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(pkg_root, dest)
        (dest / META_NAME).write_text(json.dumps({
            "uploader_id": uploader_id,
            "uploader_name": uploader_name,
        }))
        registry.reload()
        return manifest
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def new_id() -> str:
    return uuid.uuid4().hex


def build_history(game, match) -> list[dict]:
    """Replay the match's moves to produce labelled history for the move log:
    [{ply, seat, player, label}]. Replay is needed because describe_move wants
    the position *before* each move."""
    try:
        state = game.initial_state(options=match.options or {})
    except Exception:  # noqa: BLE001
        return []
    out = []
    for mr in sorted(match.moves, key=lambda r: r.ply):
        try:
            label = game.describe_move(state, mr.move)
        except Exception:  # noqa: BLE001
            label = mr.move
        name = match.players[mr.seat].get("name") if mr.seat < len(match.players) else f"P{mr.seat}"
        out.append({"ply": mr.ply, "seat": mr.seat, "player": name, "label": label})
        try:
            state = game.apply_move(state, mr.move)
        except Exception:  # noqa: BLE001
            break
    return out


# ===========================================================================
#  match driving
# ===========================================================================
import re

_FREEFORM_MOVE_RE = re.compile(r"^(-?\d+,-?\d+)>(-?\d+,-?\d+)(=.+)?$")
_FREEFORM_REMOVE_RE = re.compile(r"^@(-?\d+,-?\d+)$")


def is_freeform(game) -> bool:
    """Whether a game is unenforced (honor-system). See agp.FreeformGame."""
    return getattr(game, "enforced", True) is False


def freeform_move_ok(game, state, move: str) -> bool:
    """Validate a move for an unenforced game *structurally* (the server is a
    move-relay, not a referee): an action token, or a board move/removal whose
    source cell currently holds a piece. Topology-agnostic — occupancy is read
    from render() so it works for any board type."""
    if move in game.legal_moves(state):           # pass / resign / draw actions
        return True
    occupied = {p["cell"] for p in game.render(state).get("pieces", [])}
    m = _FREEFORM_MOVE_RE.match(move)
    if m:
        return m.group(1) in occupied
    rm = _FREEFORM_REMOVE_RE.match(move)
    if rm:
        return rm.group(1) in occupied
    return False


def position_view(game, state) -> dict:
    terminal = game.is_terminal(state)
    return {
        "render": game.render(state),
        "legal_moves": game.legal_moves(state),
        "current_player": game.current_player(state),
        "num_players": game.num_players,
        "freeform": is_freeform(game),
        "terminal": terminal,
        "returns": game.returns(state) if terminal else None,
    }


def advance_bots(match, game) -> None:
    state = game.deserialize(match.state)
    ply = len(match.moves)
    while not game.is_terminal(state):
        seat_idx = game.current_player(state)
        seat = match.players[seat_idx]
        if seat.get("type") != "bot":
            break
        move = MCTSBot(_rng, iterations=int(seat.get("iterations", 300))).select(game, state)
        state = game.apply_move(state, move, rng=_rng)
        match.moves.append(_move_record(match.id, ply, seat_idx, move))
        ply += 1
    _commit_position(match, game, state)


def apply_human_move(match, game, move: str) -> None:
    state = game.deserialize(match.state)
    state = game.apply_move(state, move, rng=_rng)
    match.moves.append(_move_record(match.id, len(match.moves), match.current_player, move))
    _commit_position(match, game, state)


def _commit_position(match, game, state) -> None:
    match.state = game.serialize(state)
    match.current_player = game.current_player(state)
    if game.is_terminal(state):
        match.status = "finished"
        ret = game.returns(state)
        best = max(ret)
        winners = [i for i, v in enumerate(ret) if v == best]
        match.winner = winners[0] if (len(winners) == 1 and best > 0) else None


def _move_record(match_id, ply, seat, move):
    from .models import MoveRecord

    return MoveRecord(match_id=match_id, ply=ply, seat=seat, move=move)
