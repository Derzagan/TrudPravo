"""
ТрудПраво — Парсер иерархии Трудового кодекса РК

Разбивает сырой текст ТК на чанки по структуре:
    Раздел → Глава → Статья → Пункт → Подпункт

Адаптация парсера из HardCode-стажировки под текстовый формат (вместо DOCX).

Результат: chunks.json
"""

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent
INPUT_FILE = DATA_DIR / "raw_text.txt"
OUTPUT_FILE = DATA_DIR / "chunks.json"


def make_chunk(
    text: str,
    section_number: str = None,
    section_name: str = None,
    chapter_number: str = None,
    chapter_name: str = None,
    article_number: str = None,
    article_name: str = None,
    point_number: str = None,
    chunk_type: str = "text",
    footnote: str = None,
) -> dict:
    """Создаёт чанк с метаданными иерархии."""
    return {
        "text": text.strip(),
        "metadata": {
            "section_number": section_number,
            "section_name": section_name,
            "chapter_number": chapter_number,
            "chapter_name": chapter_name,
            "article_number": article_number,
            "article_name": article_name,
            "point_number": point_number,
            "chunk_type": chunk_type,
            "footnote": footnote,
            "source": "Трудовой кодекс РК от 23.11.2015 № 414-V",
            "source_url": "https://old.adilet.zan.kz/rus/docs/K1500000414",
        },
    }


def parse_labor_code(text: str) -> list[dict]:
    """
    Парсит текст ТК РК в чанки по иерархии.

    Логика (адаптация parse_hierarchical_blocks):
    - РАЗДЕЛ N. ... → обновляет текущий раздел
    - Глава N. ...  → обновляет текущую главу
    - Статья N. ... → начинает новую статью
    - N. ...        → пункт внутри статьи
    - N) ...        → подпункт
    - Сноска. ...   → сноска к статье
    """
    chunks = []
    lines = text.split("\n")

    # Текущий контекст иерархии
    cur_section_num = None
    cur_section_name = None
    cur_chapter_num = None
    cur_chapter_name = None
    cur_article_num = None
    cur_article_name = None
    cur_point_num = None
    cur_footnote = None

    # Буферы текста
    article_text = ""
    point_text = ""
    subpoint_buffer = []

    # Флаг для многострочных заголовков
    last_header = None

    def _make(text_val, point_num=None, chunk_type="text"):
        return make_chunk(
            text_val,
            cur_section_num, cur_section_name,
            cur_chapter_num, cur_chapter_name,
            cur_article_num, cur_article_name,
            point_num, chunk_type, cur_footnote,
        )

    def flush_subpoints():
        nonlocal subpoint_buffer
        for sp in subpoint_buffer:
            chunks.append(_make(sp, cur_point_num, "subpoint"))
        subpoint_buffer.clear()

    def flush_point():
        nonlocal point_text
        if point_text.strip():
            chunks.append(_make(point_text.strip(), cur_point_num, "point"))
            point_text = ""

    def flush_article():
        nonlocal article_text
        if article_text.strip():
            chunks.append(_make(article_text.strip(), None, "article_text"))
            article_text = ""

    def flush_all():
        flush_subpoints()
        flush_point()
        flush_article()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # --- РАЗДЕЛ ---
        m = re.match(r"^РАЗДЕЛ\s+(\d+)\.\s*(.*)", line, re.IGNORECASE)
        if m or re.match(r"^РАЗДЕЛ\s+\d+", line, re.IGNORECASE):
            flush_all()
            cur_point_num = None
            cur_article_num = None
            cur_article_name = None
            cur_footnote = None
            if m:
                cur_section_num = m.group(1)
                cur_section_name = m.group(2).strip()
            else:
                m2 = re.match(r"^РАЗДЕЛ\s+(\d+)", line, re.IGNORECASE)
                cur_section_num = m2.group(1) if m2 else None
                cur_section_name = line
            last_header = "section"
            continue

        # --- Глава ---
        m = re.match(r"^Глава\s+(\d+)\.\s*(.*)", line)
        if m or re.match(r"^Глава\s+\d+", line):
            flush_all()
            cur_point_num = None
            cur_article_num = None
            cur_article_name = None
            cur_footnote = None
            if m:
                cur_chapter_num = m.group(1)
                cur_chapter_name = m.group(2).strip()
            else:
                m2 = re.match(r"^Глава\s+(\d+)", line)
                cur_chapter_num = m2.group(1) if m2 else None
                cur_chapter_name = line
            last_header = "chapter"
            continue

        # --- Статья ---
        m = re.match(r"^Статья\s+([\d]+-?\d*)\.\s*(.*)", line)
        if m:
            flush_all()
            cur_article_num = m.group(1)
            cur_article_name = m.group(2).strip()
            cur_point_num = None
            cur_footnote = None
            article_text = ""
            point_text = ""
            last_header = "article"
            continue

        # Проверка на "Статья N" без точки (многострочный заголовок)
        m = re.match(r"^Статья\s+([\d]+-?\d*)$", line)
        if m:
            flush_all()
            cur_article_num = m.group(1)
            cur_article_name = ""
            cur_point_num = None
            cur_footnote = None
            article_text = ""
            point_text = ""
            last_header = "article"
            continue

        # --- Пункт (N. текст) ---
        m = re.match(r"^(\d+(?:-\d+)?)\.\s+(.*)", line, re.DOTALL)
        if m and cur_article_num:
            flush_subpoints()
            flush_point()
            flush_article()
            cur_point_num = m.group(1)
            p_text = m.group(2).strip()
            point_text = p_text
            last_header = None
            continue

        # --- Подпункт (N) текст) ---
        m = re.match(r"^(\d+(?:-\d+)?)\)\s*(.*)", line)
        if m and cur_article_num:
            subpoint_buffer.append(line)
            last_header = None
            continue

        # --- Сноска ---
        if line.startswith("Сноска") or "Сноска." in line:
            cur_footnote = line
            last_header = None
            continue

        # --- Примечание ИЗПИ/РЦПИ (пропускаем) ---
        if re.match(r"^Примечание\s+(ИЗПИ|РЦПИ)", line, re.IGNORECASE):
            last_header = "note"
            continue

        # --- Продолжение многострочных заголовков ---
        if last_header == "section":
            cur_section_name = (cur_section_name + " " + line).strip()
            continue
        if last_header == "chapter":
            cur_chapter_name = (cur_chapter_name + " " + line).strip()
            continue
        if last_header == "article":
            if not cur_article_name:
                cur_article_name = line
            else:
                cur_article_name = (cur_article_name + " " + line).strip()
            continue
        if last_header == "note":
            continue  # Пропускаем строки примечаний

        # --- Обычный текст ---
        last_header = None
        if subpoint_buffer:
            subpoint_buffer[-1] += " " + line
        elif cur_point_num:
            point_text += " " + line
        elif cur_article_num:
            article_text += " " + line

    flush_all()
    return chunks


def filter_chapters(chunks: list[dict], target_chapters: set[str] = None) -> list[dict]:
    """
    Фильтрует чанки по номерам глав.

    Целевые главы для MVP:
    - Глава 4: Трудовой договор (испытательный срок, ст. 36-37)
    - Глава 6: Прекращение трудового договора (увольнение, ст. 49-62)
    - Глава 8: Рабочее время (ст. 68-78)
    - Глава 10: Время отдыха / Отпуска (ст. 87-98)
    - Глава 11-12: Нормирование и оплата труда (ст. 99-131)
    """
    if target_chapters is None:
        target_chapters = {"4", "5", "6", "7", "8", "9", "10", "11", "12"}

    filtered = []
    for chunk in chunks:
        ch_num = chunk["metadata"].get("chapter_number")
        if ch_num and ch_num in target_chapters:
            filtered.append(chunk)

    return filtered


def print_stats(chunks: list[dict], label: str = ""):
    """Печатает статистику по чанкам."""
    if label:
        print(f"\n📊 {label}")

    articles = set()
    chapters = set()
    for c in chunks:
        if c["metadata"].get("article_number"):
            articles.add(c["metadata"]["article_number"])
        if c["metadata"].get("chapter_number"):
            chapters.add(c["metadata"]["chapter_number"])

    types = {}
    for c in chunks:
        ct = c["metadata"]["chunk_type"]
        types[ct] = types.get(ct, 0) + 1

    print(f"  Всего чанков: {len(chunks)}")
    print(f"  Уникальных статей: {len(articles)}")
    print(f"  Глав: {sorted(chapters)}")
    print(f"  По типам: {types}")


def main():
    print("=" * 60)
    print("ТрудПраво — Парсер иерархии ТК РК")
    print("=" * 60)

    if not INPUT_FILE.exists():
        print(f"❌ Файл не найден: {INPUT_FILE}")
        print("   Сначала запустите scraper.py")
        return

    text = INPUT_FILE.read_text(encoding="utf-8")
    print(f"📄 Загружен raw_text.txt: {len(text)} символов")

    # Парсим
    all_chunks = parse_labor_code(text)
    print_stats(all_chunks, "Все чанки")

    # Фильтруем нужные главы
    filtered = filter_chapters(all_chunks)
    print_stats(filtered, "Отфильтрованные (целевые главы)")

    # Сохраняем
    OUTPUT_FILE.write_text(
        json.dumps(filtered, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n💾 Сохранено {len(filtered)} чанков в: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
