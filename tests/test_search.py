"""
Тесты поиска ТрудПраво.
Запуск: .venv\Scripts\python.exe tests/test_search.py
"""

import sys
import io
sys.path.insert(0, ".")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from backend.rag.retriever import expand_query, Retriever
from backend.config import CHROMA_DIR, EMBEDDING_MODEL

# ─── 1. Тесты expand_query (без сети/БД) ────────────────────────────────────

def test_expand(label: str, query: str, must_contain: list[str]) -> bool:
    expanded = expand_query(query)
    missing = [w for w in must_contain if w.lower() not in expanded.lower()]
    ok = len(missing) == 0
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {label}")
    if not ok:
        print(f"         Query   : {query}")
        print(f"         Expanded: {expanded}")
        print(f"         Missing : {missing}")
    return ok


print("=" * 60)
print("1. EXPAND_QUERY — стемы и опечатки")
print("=" * 60)
results = [
    test_expand("уволиться (правильно)",    "хочу уволиться",       ["расторжение"]),
    test_expand("уволиься (опечатка)",      "хочу уволиься",        ["расторжение"]),
    test_expand("увольнения (форма)",       "процедура увольнения",  ["расторжение"]),
    test_expand("зп (аббревиатура)",        "не пришла зп",         ["заработная плата"]),
    test_expand("зарплата (форма)",         "нет зарплаты",         ["заработная плата"]),
    test_expand("зарплату (форма)",         "не дают зарплату",     ["заработная плата"]),
    test_expand("больничный (правильно)",   "я на больничном",      ["нетрудоспособность"]),
    test_expand("больничного (форма)",      "нет больничного",      ["нетрудоспособность"]),
    test_expand("заболел",                  "я заболел",            ["нетрудоспособность"]),
    test_expand("отпуск",                   "хочу в отпуск",        ["ежегодный"]),
    test_expand("отпускные",                "когда платят отпускные", ["компенсация"]),
    test_expand("испытательный",            "испытательный срок",   ["испытание"]),
    test_expand("сократили",               "меня сократили",        ["сокращение"]),
    test_expand("выговор",                 "мне дали выговор",      ["дисциплинарное"]),
]
passed = sum(results)
print(f"\nРезультат: {passed}/{len(results)} тестов прошли\n")


# ─── 2. Тесты поиска (требуют ChromaDB) ─────────────────────────────────────

print("=" * 60)
print("2. RETRIEVER SEARCH — реальный поиск по базе")
print("=" * 60)

try:
    retriever = Retriever(
        chroma_dir=str(CHROMA_DIR),
        collection_name="labor_code",
        embedding_model=EMBEDDING_MODEL,
    )
except Exception as e:
    print(f"[ERROR] Не удалось инициализировать Retriever: {e}")
    sys.exit(1)


def test_search(label: str, query: str, expected_articles: list[str]) -> bool:
    results = retriever.search(query, top_k=5)
    found_articles = [str(r["metadata"].get("article_number", "")) for r in results]
    hit = any(a in found_articles for a in expected_articles)
    status = "OK" if hit else "FAIL"
    print(f"  [{status}] {label}")
    print(f"         Query  : {query}")
    print(f"         Expect : ст. {expected_articles}")
    print(f"         Got    : ст. {found_articles[:5]}")
    return hit


search_results = [
    test_search(
        "Задержка зарплаты",
        "не пришла зп за август сейчас уже 1.10",
        ["113"],
    ),
    test_search(
        "Задержка зп (аббревиатура)",
        "зп не выплатили",
        ["113"],
    ),
    test_search(
        "Увольнение по инициативе работника",
        "хочу уволиться что делать",
        ["56", "57", "58"],  # ст.56 - инициатива работника, 57/58 - смежные
    ),
    test_search(
        "Увольнение с опечаткой",
        "хочу уволиься чьл мне делать",
        ["56", "57", "58"],
    ),
    test_search(
        "Испытательный срок",
        "максимальный испытательный срок при приеме на работу",
        ["36"],
    ),
    test_search(
        "Испытательный срок (разговорный)",
        "какой испытательный срок",
        ["36"],
    ),
    test_search(
        "Больничный",
        "заболел температура не могу идти на работу",
        ["43", "133", "134"],  # нетрудоспособность
    ),
    test_search(
        "Отпуск",
        "хочу уйти в отпуск сколько дней",
        ["87", "88", "92"],
    ),
    test_search(
        "Срок уведомления при увольнении",
        "за сколько дней предупредить об увольнении",
        ["56", "57", "53"],
    ),
    test_search(
        "Сверхурочная работа",
        "меня заставляют работать сверхурочно переработка",
        ["77", "86", "108"],  # ст.77 - рабочее время/сверхурочные
    ),
]

s_passed = sum(search_results)
print(f"\nРезультат: {s_passed}/{len(search_results)} тестов прошли")
print("=" * 60)

total = passed + s_passed
total_all = len(results) + len(search_results)
print(f"\nИТОГО: {total}/{total_all} тестов прошли")
if total == total_all:
    print("Все тесты прошли!")
else:
    print("Есть провалы — смотри детали выше.")
