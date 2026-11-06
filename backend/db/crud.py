"""
CRUD-операции для SQLite (сессии и сообщения).
"""

from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy import select, desc, asc
from sqlalchemy.orm import Session

from backend.db.models import ChatSession, Message


def get_or_create_session(db: Session, session_id: Optional[str] = None) -> ChatSession:
    if session_id:
        session = db.get(ChatSession, session_id)
        if session:
            return session

    new_id = uuid.uuid4().hex[:16]
    session = ChatSession(id=new_id, title="Новый диалог")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def add_message(
    db: Session,
    session_id: str,
    from_ai: bool,
    content: str,
    meta_info: Optional[dict] = None,
) -> Message:
    msg = Message(
        session_id=session_id,
        from_ai=from_ai,
        content=content,
        meta_info=meta_info,
    )
    db.add(msg)

    # Обновляем timestamp сессии
    session = db.get(ChatSession, session_id)
    if session:
        session.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(msg)
    return msg


def get_session_messages(db: Session, session_id: str, limit: int = 50) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(asc(Message.created_at), asc(Message.id))
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def list_sessions(db: Session, limit: int = 20) -> list[ChatSession]:
    stmt = (
        select(ChatSession)
        .order_by(desc(ChatSession.updated_at))
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())
