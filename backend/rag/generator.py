"""
Generator — формирование ответа через Groq API.
Источник: ais_demo/agents/orchestrator.py + tools.py (упрощённый, без judge/tool-calling).
Прямой RAG: retriever → контекст → LLM → ответ с [S1].
"""

import json
import re

from openai import OpenAI

from backend.rag.prompts import SYSTEM_PROMPT
from backend.rag.retriever import Retriever

_SOURCE_REF_RE = re.compile(r"\[(?:\*\*|\*)?(S\d+)(?:\*\*|\*)?\]")

# Адаптировано из hrm/agents/orchestrator.py — вырезает обещания действий из ответа
_ACTION_PROMISE_PATTERNS = [
    r"(?<!не\s)(?<!не )\b(могу|могла|готов|готова)\s+(инициир|оформ|подготов|отправ|запрос|связ|изменить|снять|перен|внести|добавить|учесть|сделать|обнов|согласов|утверд|подпис|написать|составить)",
    r"\bмы\s+(внесём|внесем|добавим|учтём|учтем|загрузим|обновим|согласуем|внесли|добавили|учли|оформим|отправим|запросим|поможем)",
    r"\b(?<!не\s)(?<!не )(оформлю|отправлю|запрошу|свяжусь|подготовлю|изменю|сниму|перенесу|внесу|добавлю|инициирую|обновлю|согласую|составлю|напишу)\b",
    r"\bпомочь\s+(оформ|подготов|отправ|перен|снять|изменить|внести|добавить|составить|написать)",
    r"\bдавайте\s+я\b",
    r"\b(хотите|если\s+хотите)[,\s]+(?:я\b|чтобы\s+я|могу)",
    r"\bпри\s+необходимости\s+(обращ|напиш|сделаю|свяж|инициир|составл)",
]
_FALLBACK_LINE = (
    "Для оформления документов обратитесь в отдел кадров вашей организации, "
    "юридическую службу или государственную инспекцию труда."
)


def _strip_action_promises(text: str) -> str:
    """Удаляет предложения, в которых ассистент обещает совершить действия."""
    if not text:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    kept: list[str] = []
    dropped = False
    for sent in sentences:
        low = sent.lower()
        if any(re.search(p, low) for p in _ACTION_PROMISE_PATTERNS):
            dropped = True
            continue
        kept.append(sent)
    cleaned = " ".join(kept).strip()
    if dropped:
        already_directs = any(
            kw in cleaned.lower()
            for kw in ("инспекци", "отдел кадров", "hr", "суд", "обратитесь")
        )
        if not already_directs:
            cleaned = (cleaned + " " + _FALLBACK_LINE).strip()
    return cleaned


class Generator:
    def __init__(self, api_key: str, base_url: str, model: str, retriever: Retriever):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.retriever = retriever

    def answer(self, question: str, top_k: int = 5, history: list[dict] | None = None) -> dict:
        """
        Полный RAG-цикл:
        1. Поиск релевантных чанков (используем расширенный запрос с учётом истории)
        2. Формирование контекста с идентификаторами [S1], [S2]...
        3. Вызов LLM (с историей диалога)
        4. Парсинг ссылок на источники

        Возвращает: {answer, sources: [{source_id, chunk_id, breadcrumb, article_number, ...}]}
        """
        history = history or []

        # 1. Поиск — если вопрос короткий/с опечаткой, добавляем контекст из последних сообщений
        search_query = question
        if history:
            # Берём последние 2 обмена для обогащения поиска
            recent = " ".join(
                m["content"] for m in history[-4:]
                if m.get("role") == "user"
            )
            if len(question.strip()) < 30 or not any(c.isalpha() for c in question[3:]):
                # Короткий или неразборчивый запрос — обогащаем контекстом
                search_query = f"{recent} {question}"

        results = self.retriever.search(search_query, top_k=top_k)

        if not results:
            return {
                "answer": "По вашему вопросу ничего не найдено в Трудовом кодексе РК.",
                "sources": [],
            }

        # 2. Контекст с идентификаторами [S1], [S2]...
        source_map = {}  # source_id -> result
        context_blocks = []

        for i, result in enumerate(results):
            source_id = f"S{i + 1}"
            source_map[source_id] = result

            metadata = result["metadata"]
            breadcrumb = result["breadcrumb"]
            label_parts = []
            if metadata.get("article_number"):
                label_parts.append(f"статья {metadata['article_number']}")
            if metadata.get("point_number"):
                label_parts.append(f"пункт {metadata['point_number']}")
            label = ", ".join(label_parts) if label_parts else "фрагмент"

            context_blocks.append(
                f"[{source_id}] {label}\n{breadcrumb}\n{result['text'].strip()}"
            )

        context = "\n\n".join(context_blocks)

        # 3. Вызов LLM — с историей диалога
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Добавляем историю (не более 10 последних сообщений, чтобы не раздувать контекст)
        messages.extend(history[-10:])

        # Текущий вопрос с контекстом из ТК РК
        messages.append({
            "role": "user",
            "content": (
                f"Контекст из Трудового кодекса РК:\n\n{context}\n\n"
                f"Вопрос пользователя: {question}"
            ),
        })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
        )

        answer_text = _strip_action_promises(response.choices[0].message.content or "")

        # 4. Парсинг ссылок
        used_refs = []
        for ref in _SOURCE_REF_RE.findall(answer_text):
            if ref not in used_refs:
                used_refs.append(ref)

        sources = []
        for ref in used_refs:
            result = source_map.get(ref)
            if not result:
                continue
            metadata = result["metadata"]
            sources.append({
                "source_id": ref,
                "chunk_id": result["chunk_id"],
                "source": metadata.get("source", ""),
                "breadcrumb": result["breadcrumb"],
                "article_number": metadata.get("article_number"),
                "article_name": metadata.get("article_name"),
                "point_number": metadata.get("point_number"),
                "chunk_type": metadata.get("chunk_type"),
                "score": round(result["score"], 4),
            })

        return {"answer": answer_text, "sources": sources}
