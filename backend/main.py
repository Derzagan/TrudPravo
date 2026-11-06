"""
Главная точка входа FastAPI приложения ТрудПраво.
"""

from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router
from backend.config import (
    CHROMA_DIR,
    EMBEDDING_MODEL,
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    ROOT_DIR,
)
from backend.db.database import init_db
from backend.rag.generator import Generator
from backend.rag.retriever import Retriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trudpravo")

FRONTEND_DIR = ROOT_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Инициализация базы данных SQLite...")
    init_db()

    logger.info("Загрузка RAG-компонентов (ChromaDB + sentence-transformers)...")
    try:
        retriever = Retriever(
            chroma_dir=str(CHROMA_DIR),
            collection_name="labor_code",
            embedding_model=EMBEDDING_MODEL,
        )
        generator = Generator(
            api_key=GROQ_API_KEY,
            base_url=GROQ_BASE_URL,
            model=GROQ_MODEL,
            retriever=retriever,
        )
        app.state.generator = generator
        logger.info("RAG-пайплайн успешно инициализирован (Groq: %s)", GROQ_MODEL)
    except Exception as exc:
        logger.error("Ошибка при инициализации RAG: %s", exc)
        app.state.generator = None

    yield


app = FastAPI(title="ТрудПраво API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение API роутов
app.include_router(router)

# Раздача статических файлов фронтенда
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "ТрудПраво API работает. Фронтенд ещё собирается."}


@app.get("/login")
def serve_login():
    login_path = FRONTEND_DIR / "login.html"
    if login_path.exists():
        return FileResponse(login_path)
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/register")
def serve_register():
    reg_path = FRONTEND_DIR / "register.html"
    if reg_path.exists():
        return FileResponse(reg_path)
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/cabinet")
def serve_cabinet():
    cab_path = FRONTEND_DIR / "cabinet.html"
    if cab_path.exists():
        return FileResponse(cab_path)
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "rag_ready": getattr(app.state, "generator", None) is not None,
        "model": GROQ_MODEL,
    }
