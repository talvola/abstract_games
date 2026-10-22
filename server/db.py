"""Database setup. SQLite locally (zero config), Postgres in production -- pick
via the DATABASE_URL env var. Schema is created on startup (no migrations yet;
add Alembic when the model stabilises in a later phase)."""

from __future__ import annotations

import os

from sqlalchemy import create_engine, make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./agp.db")

# Render/Heroku/Neon hand out postgres:// or postgresql:// URLs with no driver.
# Name the driver explicitly: SQLAlchemy 2.1 changed the DEFAULT postgresql
# driver from psycopg2 to psycopg (v3), so a bare URL crashed prod at startup
# ("No module named 'psycopg'") the first time a deploy picked up 2.1. We ship
# psycopg2-binary (server/requirements.txt).
for _bare in ("postgres://", "postgresql://"):
    if DATABASE_URL.startswith(_bare):
        DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len(_bare):]
        break

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
if make_url(DATABASE_URL).host not in (None, "localhost", "127.0.0.1", "::1"):
    import certifi

    # Verify the remote server's certificate (Neon): the URL's sslmode=require
    # encrypts but accepts ANY cert. psycopg2-binary's bundled OpenSSL has a
    # build-machine cert dir, so sslrootcert=system finds no roots and every
    # connection fails; point it at certifi's bundle (pinned to a release
    # without the compromised emSign ECC Root CA - G3). These override the URL.
    # Local servers (a pgserver repro over a unix socket) are left alone.
    _connect_args = {"sslmode": "verify-full", "sslrootcert": certifi.where(),
                     "channel_binding": "require"}
engine =create_engine(DATABASE_URL, connect_args=_connect_args, future=True)

# SQLite ignores FOREIGN KEY constraints unless asked, Postgres always enforces
# them -- so a delete that strands child rows passed every local test and 500'd
# in production (DELETE /api/matches/{id} on any rated game, until 2026-10-08).
# Enforce them here too so tests and dev behave like prod.
if engine.dialect.name == "sqlite":
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _sqlite_fk_on(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from . import models  # noqa: F401 - register mappers

    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
