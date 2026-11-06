"""
TrudPravo — Vectorize chunks -> ChromaDB

Эмбеддинги: sentence-transformers (локально, бесплатно)
Хранилище: ChromaDB (файловая БД)

Запуск: python data/vectorize.py
"""

import json
import sys
import io
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.config import CHROMA_DIR, CHUNKS_PATH, EMBEDDING_MODEL

COLLECTION_NAME = "labor_code"


def load_chunks() -> list[dict]:
    if not CHUNKS_PATH.exists():
        print(f"[!] Файл не найден: {CHUNKS_PATH}")
        print("    Сначала: python data/scraper.py")
        sys.exit(1)

    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"[OK] Загружено {len(chunks)} чанков")
    return chunks


def build_embedding_text(chunk: dict) -> str:
    """
    Текст для эмбеддинга: контекст + основной текст.
    Контекст (статья, глава) улучшает качество поиска.
    """
    meta = chunk["metadata"]
    parts = []

    if meta.get("article_number") and meta.get("article_name"):
        parts.append(f"Статья {meta['article_number']}. {meta['article_name']}")

    if meta.get("chapter_name"):
        parts.append(f"Глава: {meta['chapter_name']}")

    parts.append(chunk["text"])
    return "\n".join(parts)


def chunk_metadata_for_chroma(chunk: dict) -> dict:
    """ChromaDB принимает только str/int/float/bool — None -> ''."""
    meta = chunk["metadata"]
    clean = {}
    for key, value in meta.items():
        if value is None:
            clean[key] = ""
        elif isinstance(value, (str, int, float, bool)):
            clean[key] = value
        else:
            clean[key] = str(value)
    return clean


def main():
    print("=" * 60)
    print("TrudPravo -- Vectorize -> ChromaDB")
    print("=" * 60)

    # Загружаем чанки
    chunks = load_chunks()
    chunks = [c for c in chunks if c["text"].strip()]
    print(f"[OK] Непустых чанков: {len(chunks)}")

    # Загружаем модель эмбеддингов (локально)
    print(f"[*] Загружаю модель: {EMBEDDING_MODEL}...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"[OK] Модель загружена")

    # Создаём тексты для эмбеддинга
    texts = [build_embedding_text(c) for c in chunks]

    # Создаём эмбеддинги (всё локально, без API)
    print(f"[*] Создаю эмбеддинги для {len(texts)} текстов...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)
    embeddings_list = [emb.tolist() for emb in embeddings]
    print(f"[OK] Эмбеддинги: {len(embeddings_list)}x{len(embeddings_list[0])} dims")

    # Инициализируем ChromaDB
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Удаляем старую коллекцию
    try:
        chroma_client.delete_collection(COLLECTION_NAME)
        print(f"[*] Удалена старая коллекция '{COLLECTION_NAME}'")
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Trudovoy kodeks RK"},
    )
    print(f"[OK] Коллекция: {COLLECTION_NAME}")

    # Готовим данные
    ids = [f"chunk_{i:04d}" for i in range(len(chunks))]
    documents = [c["text"] for c in chunks]
    metadatas = [chunk_metadata_for_chroma(c) for c in chunks]

    # Добавляем батчами
    BATCH = 500
    for i in range(0, len(ids), BATCH):
        end = min(i + BATCH, len(ids))
        collection.add(
            ids=ids[i:end],
            documents=documents[i:end],
            metadatas=metadatas[i:end],
            embeddings=embeddings_list[i:end],
        )
        print(f"     ChromaDB: {end}/{len(ids)}")

    print(f"\n[OK] ChromaDB: {collection.count()} документов")
    print(f"[OK] Сохранено: {CHROMA_DIR}")

    # ── Тестовый поиск ──
    print("\n" + "-" * 40)
    print("[TEST] 'увольнение на испытательном сроке'")
    test_emb = model.encode(["увольнение на испытательном сроке"]).tolist()
    results = collection.query(query_embeddings=test_emb, n_results=3)

    for j, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        art = meta.get("article_number", "?")
        pt = meta.get("point_number", "")
        ch = meta.get("chapter_name", "")
        print(f"  {j+1}. [Ст.{art} п.{pt}] dist={dist:.4f}")
        print(f"     {doc[:100]}...")
        print(f"     Глава: {ch}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
