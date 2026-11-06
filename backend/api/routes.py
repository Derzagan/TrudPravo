"""
FastAPI маршруты для чата и истории.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.api.schemas import ChatRequest, ChatResponse, Citation, MessageOut, SessionOut
from backend.db import crud
from backend.db.database import get_db

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest, request: Request, db: Session = Depends(get_db)):
    query = (payload.message or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Вопрос не может быть пустым.")

    generator = getattr(request.app.state, "generator", None)
    if generator is None:
        raise HTTPException(status_code=503, detail="RAG-генератор не инициализирован.")

    # 1. Получаем или создаём сессию
    session = crud.get_or_create_session(db, payload.session_id)

    # 2. Загружаем историю диалога для передачи в LLM
    past_messages = crud.get_session_messages(db, session.id)
    history = []
    for m in past_messages[-10:]:  # последние 10 сообщений
        role = "assistant" if m.from_ai else "user"
        history.append({"role": role, "content": m.content or ""})

    # 3. Сохраняем вопрос пользователя
    crud.add_message(db, session_id=session.id, from_ai=False, content=query)

    # 4. Генерируем ответ через RAG + Groq (с историей)
    try:
        rag_result = generator.answer(query, history=history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации ответа: {str(e)}")

    answer_text = rag_result.get("answer", "")
    sources = rag_result.get("sources", [])

    # 5. Сохраняем ответ ассистента в БД
    crud.add_message(
        db,
        session_id=session.id,
        from_ai=True,
        content=answer_text,
        meta_info={"sources": sources},
    )

    # 6. Преобразуем источники в схему Citation
    citations = [
        Citation(
            source_id=s.get("source_id", ""),
            source=s.get("source", ""),
            breadcrumb=s.get("breadcrumb", ""),
            article_number=s.get("article_number"),
            article_name=s.get("article_name"),
            point_number=s.get("point_number"),
            chunk_type=s.get("chunk_type"),
            score=s.get("score"),
        )
        for s in sources
    ]

    return ChatResponse(
        session_id=session.id,
        answer=answer_text,
        citations=citations,
    )


@router.get("/chat/{session_id}/messages", response_model=list[MessageOut])
def get_messages(session_id: str, db: Session = Depends(get_db)):
    messages = crud.get_session_messages(db, session_id)
    out = []
    for m in messages:
        meta = m.meta_info or {}
        raw_sources = meta.get("sources") or []
        citations = [
            Citation(
                source_id=s.get("source_id", ""),
                source=s.get("source", ""),
                breadcrumb=s.get("breadcrumb", ""),
                article_number=s.get("article_number"),
                article_name=s.get("article_name"),
                point_number=s.get("point_number"),
                chunk_type=s.get("chunk_type"),
                score=s.get("score"),
            )
            for s in raw_sources
        ]
        out.append(
            MessageOut(
                id=m.id,
                from_ai=m.from_ai,
                content=m.content,
                created_at=m.created_at,
                citations=citations,
            )
        )
    return out


@router.get("/sessions", response_model=list[SessionOut])
def get_sessions(db: Session = Depends(get_db)):
    return crud.list_sessions(db)
