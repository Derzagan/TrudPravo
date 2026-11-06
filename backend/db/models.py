"""
Модели БД (SQLite + SQLAlchemy).
Источник: hrm/db/models.py, адаптировано под SQLite.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ChatSession(Base):
    __tablename__ = "sessions"

    id = Column(String(32), primary_key=True, default=_uuid)
    title = Column(String(200), nullable=False, default="Новый чат")
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(32),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_ai = Column(Boolean, nullable=False)
    content = Column(Text, nullable=False)
    meta_info = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_now, nullable=False)

    session = relationship("ChatSession", back_populates="messages")
