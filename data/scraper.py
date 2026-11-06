"""
ТрудПраво — Скачивание и парсинг Трудового кодекса РК

Использует оригинальную логику парсера из HardCode-стажировки:
  parse_hierarchical_blocks() с полной иерархией и всеми edge-cases.

Добавлена обработка "ОБЩАЯ ЧАСТЬ" / "ОСОБЕННАЯ ЧАСТЬ".

Результат: chunks.json
"""

import json
import re
import sys
import io
from pathlib import Path

import requests
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DATA_DIR = Path(__file__).parent
DOCX_PATH = DATA_DIR / "trudovoy_kodeks.docx"
CHUNKS_PATH = DATA_DIR / "chunks.json"

DOC_INFO = {
    "url_page": "https://old.adilet.zan.kz/rus/docs/K1500000414",
    "download_url": "https://old.adilet.zan.kz/rus/docs/K1500000414/download/docx",
    "filename": "trudovoy_kodeks.docx",
}


# ═══════════════════════════════════════════════
#  1. Скачивание DOCX
# ═══════════════════════════════════════════════

def download_docx() -> Path:
    if DOCX_PATH.exists():
        size_mb = DOCX_PATH.stat().st_size / (1024 * 1024)
        print(f"[OK] Файл уже есть: {DOCX_PATH} ({size_mb:.1f} MB)")
        return DOCX_PATH

    print(f"[*] Скачиваю: {DOC_INFO['download_url']}")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": DOC_INFO["url_page"],
    }
    session = requests.Session()
    session.get(DOC_INFO["url_page"], headers=headers, verify=False)
    response = session.get(DOC_INFO["download_url"], headers=headers, verify=False)
    print(f"[*] HTTP статус: {response.status_code}")
    response.raise_for_status()

    DOCX_PATH.write_bytes(response.content)
    size_mb = len(response.content) / (1024 * 1024)
    print(f"[OK] Скачан: {DOCX_PATH} ({size_mb:.1f} MB)")
    return DOCX_PATH


# ═══════════════════════════════════════════════
#  2. Извлечение блоков из DOCX (твой код)
# ═══════════════════════════════════════════════

def fix_merged_word(text: str) -> str:
    return re.sub(r"([а-яё])([А-ЯЁ])", r"\1 \2", text)


def iter_block_items(parent):
    for child in parent.element.body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, parent)
        elif child.tag.endswith("}tbl"):
            yield Table(child, parent)


def table_to_text(table: Table) -> str:
    rows = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            value = " ".join(
                p.text.strip().replace("\xa0", " ")
                for p in cell.paragraphs
                if p.text.strip()
            )
            if value:
                cells.append(value)
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def docx_to_blocks(doc: Document) -> list[dict]:
    blocks = []
    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = fix_merged_word(block.text.strip().replace("\xa0", " "))
            if text:
                blocks.append({"type": "text", "text": text})
        elif isinstance(block, Table):
            table_text = fix_merged_word(table_to_text(block))
            if table_text.strip():
                blocks.append({"type": "table", "text": table_text})
    return blocks


# ═══════════════════════════════════════════════
#  3. Парсер иерархии (твой parse_hierarchical_blocks
#     + обработка "ОБЩАЯ ЧАСТЬ" / "ОСОБЕННАЯ ЧАСТЬ")
# ═══════════════════════════════════════════════

def _make_chunk(
    text,
    part_name,
    section_number,
    section_name,
    chapter_number,
    chapter_name,
    article_number,
    article_name,
    point_number,
    point_name,
    footnote=None,
    appendix_number=None,
    appendix_label=None,
    appendix_basis=None,
    appendix_name=None,
    chunk_type="text",
    izpi=None,
    rcpi=None,
    extra_metadata=None,
):
    metadata = {
        "part_name": part_name,
        "section_number": section_number,
        "section_name": section_name,
        "chapter_number": chapter_number,
        "chapter_name": chapter_name,
        "article_number": article_number,
        "article_name": article_name,
        "point_number": point_number,
        "point_name": point_name,
        "appendix_number": appendix_number,
        "appendix_label": appendix_label,
        "appendix_basis": appendix_basis,
        "appendix_name": appendix_name,
        "chunk_type": chunk_type,
        "footnote": footnote,
        "izpi": izpi,
        "rcpi": rcpi,
        "source": "trudovoy_kodeks.docx",
        "source_url": "https://adilet.zan.kz/rus/docs/K1500000414",
    }

    if extra_metadata:
        metadata.update(extra_metadata)

    return {
        "text": text.strip(),
        "metadata": metadata,
    }


def parse_hierarchical_blocks(blocks: list[dict]) -> list[dict]:
    chunks = []
    current_part_name = None
    current_section_number = None
    current_section_name = None
    current_chapter_number = None
    current_chapter_name = None
    current_article_number = None
    current_article_name = None
    current_article_text = ""
    current_article_footnote = None
    current_izpi = None
    current_rcpi = None
    current_point_number = None
    current_point_name = None
    current_point_text = ""
    current_appendix_number = None
    current_appendix_label = None
    current_appendix_basis = None
    current_appendix_name = None
    appendix_header_lines = []
    current_subpoint_buffer = []
    current_auto_point = 0
    last_header = None

    appendix_re = re.compile(r"^Приложение(?:\s+(\d+))?(?:\s+(.*))?$", re.IGNORECASE)
    note_re = re.compile(r"^Примечание\s+(ИЗПИ|РЦПИ)!", re.IGNORECASE)
    part_re = re.compile(r"^(ОБЩАЯ ЧАСТЬ|ОСОБЕННАЯ ЧАСТЬ)", re.IGNORECASE)

    def make(text_value, point_number=None, point_name=None, chunk_type="text", extra=None):
        return _make_chunk(
            text_value,
            current_part_name,
            current_section_number,
            current_section_name,
            current_chapter_number,
            current_chapter_name,
            current_article_number,
            current_article_name,
            point_number,
            point_name,
            current_article_footnote,
            current_appendix_number,
            current_appendix_label,
            current_appendix_basis,
            current_appendix_name,
            chunk_type,
            current_izpi,
            current_rcpi,
            extra,
        )

    def finalize_appendix_header():
        nonlocal current_appendix_basis, appendix_header_lines
        if appendix_header_lines:
            joined = " ".join(appendix_header_lines).strip()
            current_appendix_basis = (
                f"{current_appendix_basis} {joined}".strip()
                if current_appendix_basis
                else joined
            )
            appendix_header_lines = []

    def flush_subpoints():
        nonlocal current_subpoint_buffer
        if current_subpoint_buffer:
            for sp in current_subpoint_buffer:
                chunks.append(make(sp, current_point_number, current_point_name, "subpoint"))
            current_subpoint_buffer.clear()

    def flush_article_text():
        nonlocal current_article_text
        if current_article_text.strip():
            chunk_type = "appendix_text" if current_appendix_label else "article_text"
            chunks.append(make(current_article_text.strip(), None, None, chunk_type))
            current_article_text = ""

    def flush_point_text():
        nonlocal current_point_text
        if current_point_text.strip():
            chunks.append(
                make(
                    current_point_text.strip(),
                    current_point_number,
                    current_point_name,
                    "point",
                )
            )
            current_point_text = ""

    def flush_all():
        finalize_appendix_header()
        flush_subpoints()
        flush_article_text()
        flush_point_text()

    def reset_law_context():
        nonlocal current_section_number, current_section_name
        nonlocal current_chapter_number, current_chapter_name
        nonlocal current_article_number, current_article_name, current_article_footnote
        nonlocal current_point_number, current_point_name, current_auto_point

        current_section_number = None
        current_section_name = None
        current_chapter_number = None
        current_chapter_name = None
        current_article_number = None
        current_article_name = None
        current_article_footnote = None
        current_point_number = None
        current_point_name = None
        current_auto_point = 0

    def is_header_like_table(table_text: str) -> bool:
        flat = table_text.replace("|", " ").strip()
        if not flat:
            return False
        first_line = flat.split("\n", 1)[0].strip()
        if appendix_re.match(first_line):
            return True
        if flat.lower() in {"форма", "таблица"}:
            return True
        return False

    def process_line(line: str):
        nonlocal current_part_name
        nonlocal current_section_number, current_section_name
        nonlocal current_chapter_number, current_chapter_name
        nonlocal current_article_number, current_article_name
        nonlocal current_article_text, current_article_footnote
        nonlocal current_izpi, current_rcpi
        nonlocal current_point_number, current_point_name, current_point_text
        nonlocal current_appendix_number, current_appendix_label
        nonlocal current_appendix_basis, current_appendix_name
        nonlocal appendix_header_lines, current_auto_point, last_header

        line = line.strip()
        if not line:
            return

        # ОБЩАЯ ЧАСТЬ / ОСОБЕННАЯ ЧАСТЬ
        part_match = part_re.match(line)
        if part_match:
            flush_all()
            current_part_name = part_match.group(1).strip()
            last_header = "part"
            return

        # Приложение
        appendix_match = appendix_re.match(line)
        if appendix_match:
            flush_all()
            current_appendix_number = appendix_match.group(1)
            current_appendix_label = (
                f"Приложение {current_appendix_number}"
                if current_appendix_number
                else "Приложение"
            )
            current_appendix_basis = (
                appendix_match.group(2).strip() if appendix_match.group(2) else None
            )
            current_appendix_name = None
            appendix_header_lines = []
            reset_law_context()
            last_header = "appendix"
            return

        # Примечание ИЗПИ/РЦПИ
        note_match = note_re.match(line)
        if note_match:
            if note_match.group(1).upper() == "ИЗПИ":
                current_izpi = line
            else:
                current_rcpi = line
            last_header = note_match.group(1).lower()
            return

        # РАЗДЕЛ
        if re.match(r"^РАЗДЕЛ\s+\d+", line):
            flush_all()
            current_point_number = None
            current_point_name = None
            current_article_number = None
            current_article_name = None
            current_article_footnote = None
            current_auto_point = 0
            m = re.match(r"^РАЗДЕЛ\s+(\d+)\.\s*(.*)", line)
            if m:
                current_section_number = m.group(1)
                current_section_name = m.group(2).strip()
            else:
                current_section_number = None
                current_section_name = line
            last_header = "section"

        # Глава
        elif re.match(r"^Глава\s+\d+", line):
            flush_all()
            current_point_number = None
            current_point_name = None
            current_article_number = None
            current_article_name = None
            current_article_footnote = None
            current_auto_point = 0
            m = re.match(r"^Глава\s+(\d+)\.\s*(.*)", line)
            if m:
                current_chapter_number = m.group(1)
                current_chapter_name = m.group(2).strip()
            else:
                current_chapter_number = None
                current_chapter_name = line
            last_header = "chapter"

        # Статья
        elif re.match(r"^Статья\s+[\d-]+", line):
            flush_all()
            current_point_number = None
            current_point_name = None
            current_article_text = ""
            current_article_footnote = None
            current_auto_point = 0
            m = re.match(r"^Статья\s+([\d-]+)\.\s*(.*)", line)
            if m:
                current_article_number = m.group(1)
                current_article_name = m.group(2).strip()
            else:
                current_article_number = None
                current_article_name = line
            last_header = "article"

        # Пункт (N. текст)
        elif re.match(r"^\d+(-\d+)?\.(\s|$)", line):
            flush_all()
            m = re.match(r"^(\d+(?:-\d+)?)\.\s*(.*)", line, re.DOTALL)
            current_point_number = m.group(1)
            point_text = m.group(2).strip()
            if point_text.endswith(":"):
                current_point_name = point_text
                current_point_text = ""
            else:
                current_point_name = None
                current_point_text = point_text
            last_header = None

        # Подпункт (N) текст)
        elif re.match(r"^\d+(?:-\d+)?\)", line):
            if not current_point_number and current_article_text.strip():
                current_auto_point += 1
                current_point_number = str(current_auto_point)
                current_point_name = current_article_text.strip()
                current_article_text = ""

            current_subpoint_buffer.append(line)
            last_header = None

        # Сноска
        elif "Сноска" in line:
            current_article_footnote = line
            last_header = None

        # Продолжение ИЗПИ/РЦПИ
        elif last_header == "изпи":
            current_izpi = f"{current_izpi} {line}".strip()
            last_header = None

        elif last_header == "рцпи":
            current_rcpi = f"{current_rcpi} {line}".strip()
            last_header = None

        # Продолжение заголовков
        elif last_header == "part":
            # Следующая строка после "ОБЩАЯ ЧАСТЬ" — просто пропускаем
            last_header = None

        elif last_header == "chapter":
            current_chapter_name = (current_chapter_name + " " + line).strip()

        elif last_header == "section":
            current_section_name = (current_section_name + " " + line).strip()

        elif last_header == "appendix":
            lowered = line.lower()
            if lowered in {"форма", "таблица"}:
                finalize_appendix_header()
                current_appendix_name = line
                last_header = None
            else:
                appendix_header_lines.append(line)

        # Обычный текст
        else:
            last_header = None
            if current_subpoint_buffer:
                current_subpoint_buffer[-1] += " " + line
            elif current_point_number:
                current_point_text += " " + line
            else:
                current_article_text += " " + line

    # ── Обработка блоков ──
    for block in blocks:
        if block["type"] == "table":
            table_text = block["text"]
            if is_header_like_table(table_text):
                for sub_line in table_text.replace("|", " ").split("\n"):
                    process_line(sub_line)
                continue

            flush_all()
            if table_text.strip():
                chunks.append(make(table_text, None, None, "table"))
            last_header = None
            continue

        process_line(block["text"])

    flush_all()
    return chunks


# ═══════════════════════════════════════════════
#  4. Main
# ═══════════════════════════════════════════════

def main():
    print("=" * 60)
    print("TrudPravo -- Parser TK RK (full)")
    print("=" * 60)

    # Скачиваем DOCX
    docx_path = download_docx()

    # Извлекаем блоки
    print("[*] Читаю DOCX...")
    doc = Document(str(docx_path))
    blocks = docx_to_blocks(doc)
    print(f"[OK] Блоков из DOCX: {len(blocks)}")

    # Показываем первые 5 блоков для проверки
    print("[*] Первые 5 блоков:")
    for i, b in enumerate(blocks[:5]):
        print(f"     {i}: [{b['type']}] {b['text'][:80]}...")

    # Парсим иерархию
    print("[*] Парсю иерархию...")
    all_chunks = parse_hierarchical_blocks(blocks)

    # Статистика
    all_articles = set(c["metadata"]["article_number"]
                       for c in all_chunks if c["metadata"].get("article_number"))
    all_chapters = set(c["metadata"]["chapter_number"]
                       for c in all_chunks if c["metadata"].get("chapter_number"))
    all_sections = set(c["metadata"]["section_number"]
                       for c in all_chunks if c["metadata"].get("section_number"))
    parts = set(c["metadata"]["part_name"]
                for c in all_chunks if c["metadata"].get("part_name"))

    print(f"[OK] Всего чанков: {len(all_chunks)}")
    print(f"     Частей: {parts}")
    print(f"     Разделов: {sorted(all_sections, key=lambda x: int(x) if x and x.isdigit() else 0)}")
    print(f"     Глав: {sorted(all_chapters, key=lambda x: int(x) if x and x.isdigit() else 0)}")
    print(f"     Уникальных статей: {len(all_articles)}")

    # Типы чанков
    types = {}
    for c in all_chunks:
        ct = c["metadata"]["chunk_type"]
        types[ct] = types.get(ct, 0) + 1
    print(f"     Типы: {types}")

    # Первые 3 чанка для проверки
    print("\n[*] Первые 3 чанка:")
    for i, c in enumerate(all_chunks[:3]):
        m = c["metadata"]
        print(f"     {i}: [Ст.{m.get('article_number')}, п.{m.get('point_number')}] "
              f"{c['text'][:80]}...")

    # Сохраняем ВСЁ (без фильтрации)
    CHUNKS_PATH.write_text(
        json.dumps(all_chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[OK] Сохранено: {len(all_chunks)} чанков -> {CHUNKS_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
