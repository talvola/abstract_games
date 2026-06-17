"""Persistent model for accounts and correspondence matches.

A *seat* describes one player position in a match and is stored as JSON so a
match can mix humans and bots without extra tables::

    {"type": "user", "user_id": 3, "name": "erik"}
    {"type": "bot",  "iterations": 300, "name": "Computer"}

The seat's index in ``Match.players`` is the engine player index.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(64))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    game_uid: Mapped[str] = mapped_column(String(64), index=True)
    options: Mapped[dict] = mapped_column(JSON, default=dict)
    players: Mapped[list] = mapped_column(JSON)  # list of seat dicts
    state: Mapped[dict] = mapped_column(JSON)  # serialized game state
    current_player: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active|finished
    winner: Mapped[int | None] = mapped_column(Integer, nullable=True)  # seat, or null=draw
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    moves: Mapped[list["MoveRecord"]] = relationship(
        back_populates="match", cascade="all, delete-orphan", order_by="MoveRecord.ply"
    )


class MoveRecord(Base):
    __tablename__ = "moves"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id"), index=True)
    ply: Mapped[int] = mapped_column(Integer)
    seat: Mapped[int] = mapped_column(Integer)
    move: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    match: Mapped[Match] = relationship(back_populates="moves")


class Seek(Base):
    """An open challenge waiting for an opponent to accept."""

    __tablename__ = "seeks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    creator_name: Mapped[str] = mapped_column(String(64))
    game_uid: Mapped[str] = mapped_column(String(64))
    options: Mapped[dict] = mapped_column(JSON, default=dict)
    seat_pref: Mapped[str] = mapped_column(String(16), default="random")  # first|second|random
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
