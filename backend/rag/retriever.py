"""
Retriever — гибридный поиск (BM25 + ChromaDB) по ТК РК.
Объединяет семантический и точный поиск по терминологии и номерам статей.
"""

import json
import re
from pathlib import Path

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from backend.rag.context import build_breadcrumb

_TOKEN_RE = re.compile(r"[а-яёa-z0-9-]+", re.IGNORECASE)
_ARTICLE_RE = re.compile(r"\b(?:стать[яеий]|ст\.?)\s*(\d+(?:-\d+)?)\b", re.IGNORECASE)

_STOPWORDS = {
    # предлоги
    "в", "на", "по", "из", "за", "от", "до", "при", "над", "под", "про", "для",
    "без", "или", "через", "между", "около", "после", "перед", "вместе",
    # союзы и частицы
    "и", "а", "но", "то", "же", "ли", "не", "ни", "бы", "да", "нет",
    "так", "уже", "ещё", "ещe", "еще", "вот", "это", "что", "как", "все",
    "если", "когда", "чем", "тем", "кем", "где", "там", "тут", "здесь",
    # местоимения
    "я", "ты", "он", "она", "они", "мы", "вы", "его", "её", "их", "им",
    "мне", "меня", "тебе", "себя", "себе", "свой", "свои", "своих", "своей",
    "который", "которая", "которые", "которого", "которой",
    # вопросительные
    "какой", "какая", "какие", "какого", "сколько", "кто", "кому",
    "можно", "нужно", "надо", "должен", "должна", "должны",
    # прочие частотные
    "быть", "будет", "было", "была", "есть", "был", "мой", "мои", "моей",
    "также", "этот", "этого", "этой", "эти", "этих", "тот", "той", "тех",
    "один", "одна", "одно", "одни", "может", "могут", "буду", "будут",
}


# Словарь расширения: СТЕМЫ (корни без окончаний) → юридическая терминология ТК РК.
# Без \b в конце — чтобы ловить любые опечатки в окончаниях:
# "уволиься", "уволился", "уволен" — все матчатся на стем "\bувол"
_QUERY_SYNONYMS = [
    # зарплата / оплата труда
    (r"\bзп\b",          "заработная плата выплата"),
    (r"\bзарплат",       "заработная плата выплата оплата труда"),
    (r"\bоклад",         "заработная плата должностной оклад"),
    (r"\bне пришл",      "задержка невыплата нарушение сроков выплаты"),
    (r"\bне выплатил",   "задержка невыплата нарушение сроков выплаты"),
    (r"\bзадержал",      "задержка нарушение сроков выплаты заработной платы"),
    (r"\bвыплат",        "выплата заработной платы сроки"),
    # увольнение — стем "увол" ловит все формы и опечатки
    (r"\bувол",          "расторжение трудового договора инициатива работника прекращение увольнение уведомление"),
    (r"\bсократил",      "сокращение численности работников расторжение"),
    (r"\bсокращен",      "сокращение численности работников расторжение"),
    (r"\bвыгнал",        "расторжение трудового договора прекращение"),
    (r"\bрасторж",       "расторжение прекращение трудового договора"),
    (r"\bпредупред",     "уведомление инициатива работника расторжение"),
    (r"\bуведомл",       "уведомление инициатива работника расторжение"),
    # отпуск
    (r"\bотпуск",        "ежегодный оплачиваемый трудовой отпуск"),
    (r"\bотпускн",       "оплата ежегодного отпуска компенсация"),
    # больничный — стем "больничн"
    (r"\bбольничн",      "временная нетрудоспособность листок нетрудоспособности"),
    (r"\bзаболел",       "временная нетрудоспособность листок нетрудоспособности"),
    (r"\bтемператур",    "временная нетрудоспособность болезнь"),
    # испытательный срок
    (r"\bиспытател",     "испытательный срок испытание при приёме"),
    (r"\bиспыталк",      "испытательный срок испытание при приёме"),
    # переработка
    (r"\bпереработ",     "сверхурочная работа сверхурочное время"),
    (r"\bсверхурочн",    "сверхурочная работа оплата сверхурочного"),
    # декрет / беременность
    (r"\bдекрет",        "отпуск по беременности родам уходу за ребёнком"),
    (r"\bбеременн",      "беременность отпуск по беременности родам гарантии"),
    # штраф / удержание
    (r"\bштраф",         "удержание из заработной платы взыскание"),
    (r"\bвычет",         "удержание из заработной платы"),
    # дисциплина
    (r"\bвыговор",       "дисциплинарное взыскание замечание выговор"),
    (r"\bдисциплин",     "дисциплинарное взыскание взыскание"),
    # командировка
    (r"\bкомандировк",   "служебная командировка направление в командировку"),
    # контракт / договор
    (r"\bконтракт",      "трудовой договор индивидуальный трудовой"),
    (r"\bдоговор",       "трудовой договор индивидуальный трудовой"),
]


def expand_query(query: str) -> str:
    """Расширяет разговорный запрос юридическими синонимами из ТК РК.
    Работает на стемах — ловит любые опечатки в окончаниях слов."""
    q = query
    for pattern, replacement in _QUERY_SYNONYMS:
        if re.search(pattern, q, flags=re.IGNORECASE):
            q = q + " " + replacement
    return q


def tokenize(text: str) -> list[str]:
    tokens = [t.lower() for t in _TOKEN_RE.findall(text or "")]
    return [t for t in tokens if len(t) >= 3 and t not in _STOPWORDS]


class Retriever:
    def __init__(self, chroma_dir: str, collection_name: str, embedding_model: str):
        # 1. Векторный клиент ChromaDB
        self._model = SentenceTransformer(embedding_model)
        self._client = chromadb.PersistentClient(path=chroma_dir)
        self._collection = self._client.get_collection(name=collection_name)

        # 2. BM25 индекс из chunks.json
        chunks_file = Path(chroma_dir).parent / "chunks.json"
        self._chunks = []
        self._tokenized_corpus = []

        if chunks_file.exists():
            with open(chunks_file, "r", encoding="utf-8") as f:
                raw_chunks = json.load(f)

            for i, chunk in enumerate(raw_chunks):
                text = (chunk.get("text") or "").strip()
                if not text:
                    continue
                metadata = chunk.get("metadata") or {}
                breadcrumb = build_breadcrumb(metadata)
                context_text = f"{breadcrumb}\n{text}" if breadcrumb else text
                chunk_id = f"chunk_{i:04d}"

                item = {
                    "chunk_id": chunk_id,
                    "text": text,
                    "metadata": metadata,
                    "breadcrumb": breadcrumb,
                    "context_text": context_text,
                }
                self._chunks.append(item)
                self._tokenized_corpus.append(tokenize(context_text))

            self._bm25 = BM25Okapi(self._tokenized_corpus)
        else:
            self._bm25 = None

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Гибридный поиск: BM25 (точные термины) + ChromaDB (семантика) + RRF fusion.
        """
        # Расширяем запрос юридическими синонимами перед поиском
        expanded = expand_query(query)

        fused_scores = {}  # chunk_id -> dict
        query_tokens = tokenize(expanded)

        # 1. BM25 поиск
        if self._bm25 and query_tokens:
            bm25_scores = self._bm25.get_scores(query_tokens)
            ranked_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)

            for rank, idx in enumerate(ranked_indices[:20]):
                if bm25_scores[idx] <= 0:
                    break
                item = self._chunks[idx]
                cid = item["chunk_id"]
                rrf = 1.0 / (60 + rank + 1)
                fused_scores[cid] = {
                    "item": item,
                    "score": rrf,
                }

        # 2. Dense Vector поиск через ChromaDB
        try:
            vector = self._model.encode([expanded]).tolist()[0]
            response = self._collection.query(
                query_embeddings=[vector],
                n_results=min(15, self._collection.count()),
                include=["documents", "metadatas", "distances"],
            )

            ids = response["ids"][0]
            documents = response["documents"][0]
            metadatas = response["metadatas"][0]
            distances = response["distances"][0]

            for rank, (cid, text, meta, dist) in enumerate(zip(ids, documents, metadatas, distances)):
                rrf = 1.0 / (60 + rank + 1)
                if cid in fused_scores:
                    fused_scores[cid]["score"] += rrf
                else:
                    breadcrumb = build_breadcrumb(meta)
                    item = {
                        "chunk_id": cid,
                        "text": text,
                        "metadata": meta,
                        "breadcrumb": breadcrumb,
                        "context_text": f"{breadcrumb}\n{text}" if breadcrumb else text,
                    }
                    fused_scores[cid] = {
                        "item": item,
                        "score": rrf,
                    }
        except Exception:
            pass

        # 3. Бонус за точное совпадение номера статьи (если запрошена конкретная статья)
        art_match = _ARTICLE_RE.search(query)
        target_article = art_match.group(1) if art_match else None

        for cid, data in fused_scores.items():
            meta = data["item"]["metadata"]
            if target_article and str(meta.get("article_number")) == target_article:
                data["score"] += 1.0

        # 4. Сортировка по финальному скору
        ranked = sorted(fused_scores.values(), key=lambda x: x["score"], reverse=True)

        results = []
        for entry in ranked[:top_k]:
            item = dict(entry["item"])
            item["score"] = round(entry["score"], 4)
            results.append(item)

        return results
