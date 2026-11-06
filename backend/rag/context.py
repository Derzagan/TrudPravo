"""
Построение breadcrumb-пути из метаданных чанка.
Источник: ais_demo/rag/context.py + part_name для ТК РК.
"""


def build_breadcrumb(metadata: dict) -> str:
    parts: list[str] = []

    part_name = metadata.get("part_name")
    if part_name:
        parts.append(part_name)

    section_name = metadata.get("section_name")
    if section_name:
        number = metadata.get("section_number")
        parts.append(f"Раздел {number}. {section_name}" if number else section_name)

    chapter_name = metadata.get("chapter_name")
    if chapter_name:
        number = metadata.get("chapter_number")
        parts.append(f"Глава {number}. {chapter_name}" if number else chapter_name)

    article_name = metadata.get("article_name")
    article_number = metadata.get("article_number")
    if article_number or article_name:
        label = "Статья"
        if article_number:
            label += f" {article_number}"
        if article_name:
            label += f". {article_name}"
        parts.append(label)

    point_number = metadata.get("point_number")
    if point_number:
        parts.append(f"Пункт {point_number}")

    appendix_label = metadata.get("appendix_label")
    if appendix_label:
        parts.append(appendix_label)

    return " · ".join(parts)


def build_context_text(metadata: dict, text: str) -> str:
    breadcrumb = build_breadcrumb(metadata)
    if breadcrumb:
        return f"{breadcrumb}\n{text}"
    return text
