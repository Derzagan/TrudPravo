"""
ТрудПраво — Конфигурация
Загружает переменные из .env
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env из корня проекта
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

# Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# JWT
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа

# Пути
DATA_DIR = ROOT_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"
CHUNKS_PATH = DATA_DIR / "chunks.json"

# RAG
CONFIDENCE_THRESHOLD = 0.35
RAG_TOP_K = 5

# Эмбеддинги (локальная многоязычная модель — поддерживает русский)
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
