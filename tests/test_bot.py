"""
Полный тест бота ТрудПраво через API.
Отправляет вопросы, записывает ответы в MD-файл.
"""

import sys
import io
import json
import time
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
SESSION_ID = "test-session-001"

# Список тестовых вопросов (в рамках одной сессии — с историей)
QUESTIONS = [
    # 1. Приветствие
    "Привет! Ты кто?",
    # 2. Зарплата
    "Мне не пришла зп за август, сейчас уже 1 октября. Что делать?",
    # 3. Увольнение (с опечаткой)
    "Хочу уволиься, что мне делать?",
    # 4. Контекстный вопрос (короткий, без ключевых слов)
    "А за сколько дней предупредить?",
    # 5. Испытательный срок
    "Какой максимальный испытательный срок при приеме на работу?",
    # 6. Отпуск
    "Сколько дней ежегодного отпуска мне положено?",
    # 7. Больничный
    "Заболел, температура. Могут ли уволить на больничном?",
    # 8. Сверхурочная работа
    "Начальник заставляет работать сверхурочно, это законно?",
    # 9. Не по теме
    "А какая погода сегодня?",
    # 10. Беременность
    "Могут ли уволить беременную женщину?",
]

results = []

print("=" * 60)
print("ТЕСТИРОВАНИЕ БОТА ТРУДПРАВО")
print("=" * 60)

# Проверяем health
try:
    h = requests.get(f"{BASE}/health", timeout=5).json()
    print(f"Health: {h}")
    if not h.get("rag_ready"):
        print("RAG не готов!")
        sys.exit(1)
except Exception as e:
    print(f"Сервер не доступен: {e}")
    sys.exit(1)

for i, question in enumerate(QUESTIONS, 1):
    print(f"\n--- Вопрос {i}/{len(QUESTIONS)} ---")
    print(f"  Q: {question}")

    try:
        resp = requests.post(
            f"{BASE}/api/chat",
            json={"message": question, "session_id": SESSION_ID},
            timeout=60,
        )
        data = resp.json()
        answer = data.get("answer", "ОШИБКА: нет ответа")
        citations = data.get("citations", [])

        cite_str = ""
        if citations:
            cite_parts = []
            for c in citations:
                sid = c.get("source_id", "")
                art = c.get("article_number", "?")
                pn = c.get("point_number", "")
                label = f"[{sid}] Статья {art}"
                if pn:
                    label += f", п. {pn}"
                cite_parts.append(label)
            cite_str = "; ".join(cite_parts)

        print(f"  A: {answer[:120]}...")
        if cite_str:
            print(f"  Cite: {cite_str}")

        results.append({
            "num": i,
            "question": question,
            "answer": answer,
            "citations": cite_str,
            "status": resp.status_code,
        })

    except Exception as e:
        print(f"  ERROR: {e}")
        results.append({
            "num": i,
            "question": question,
            "answer": f"ОШИБКА: {e}",
            "citations": "",
            "status": 0,
        })

    time.sleep(1)

# Генерируем MD-файл
print("\n\nГенерирую MD-файл...")

md = """# Результаты тестирования бота ТрудПраво

**Дата:** 02.10.2026
**Сервер:** http://localhost:8000
**Модель:** openai/gpt-oss-120b (Groq API)
**Эмбеддинги:** paraphrase-multilingual-MiniLM-L12-v2
**Поиск:** Гибридный (BM25 + ChromaDB + RRF fusion)

---

"""

for r in results:
    q = r["question"]
    a = r["answer"]
    c = r["citations"]

    md += f"## Вопрос {r['num']}\n\n"
    md += f"**Пользователь:** {q}\n\n"
    md += f"**Бот:**\n\n{a}\n\n"
    if c:
        md += f"**Источники:** {c}\n\n"
    md += "---\n\n"

# Итого
ok_count = sum(1 for r in results if r["status"] == 200)
md += f"## Итого\n\n"
md += f"- Всего вопросов: {len(results)}\n"
md += f"- Успешных ответов (HTTP 200): {ok_count}/{len(results)}\n"
md += f"- Сессия с историей: да (все вопросы в одной сессии)\n"

out_path = "tests/test_results.md"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(md)

print(f"[OK] Сохранено: {out_path}")
print("=" * 60)
