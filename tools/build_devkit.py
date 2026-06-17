#!/usr/bin/env python3
"""Assemble the self-contained game-dev kit and zip it to dist/gamedev-kit.zip.

The kit = the hand-written sources in gamedev-kit/ + the engine SDK (agp/),
SPEC.md, and a worked example copied from engine/. Building from the engine
keeps the distributed SDK from drifting out of sync with the platform.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT_SRC = ROOT / "gamedev-kit"
ENGINE = ROOT / "engine"
DIST = ROOT / "dist"
STAGE = DIST / "gamedev-kit"

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".agp_meta.json", "*.db")

PYPROJECT = """\
[project]
name = "agp-gamedev-kit"
version = "0.1.0"
description = "SDK for authoring Abstract Games Platform game modules."
requires-python = ">=3.10"
dependencies = []

[project.scripts]
agp = "agp.cli:main"

[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["agp"]
"""


def main() -> None:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    # hand-written kit sources (README, AGENTS, template/, .claude/ skill)
    shutil.copytree(KIT_SRC, STAGE, dirs_exist_ok=True, ignore=_IGNORE)
    # the SDK + contract
    shutil.copytree(ENGINE / "agp", STAGE / "agp", ignore=_IGNORE)
    shutil.copy2(ENGINE / "SPEC.md", STAGE / "SPEC.md")
    # a worked example
    (STAGE / "examples").mkdir(exist_ok=True)
    shutil.copytree(ENGINE / "games" / "tic_tac_toe", STAGE / "examples" / "tic_tac_toe", ignore=_IGNORE)
    # installable project
    (STAGE / "pyproject.toml").write_text(PYPROJECT)

    zip_path = DIST / "gamedev-kit.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(STAGE.rglob("*")):
            if f.is_file():
                zf.write(f, Path("gamedev-kit") / f.relative_to(STAGE))

    files = sum(1 for _ in STAGE.rglob("*") if _.is_file())
    print(f"built {zip_path} ({files} files, {zip_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
