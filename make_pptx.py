"""Красивая презентация ТрудПраво со скриншотами."""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# ── Цвета ──
BLUE      = RGBColor(0x1A, 0x56, 0xDB)
BLUE_DARK = RGBColor(0x0F, 0x2B, 0x6E)
BLUE_LIGHT= RGBColor(0xDB, 0xEA, 0xFE)
DARK      = RGBColor(0x1E, 0x29, 0x3B)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
GRAY      = RGBColor(0x64, 0x74, 0x8B)
LIGHT_BG  = RGBColor(0xF8, 0xFA, 0xFC)
GREEN     = RGBColor(0x16, 0xA3, 0x4A)
ACCENT    = RGBColor(0x38, 0xBD, 0xF8)

# Скриншоты
IMG_MAIN = r"C:\Users\w2\.gemini\antigravity\brain\cabc0c47-659c-451f-a174-ab8b90b5ffa1\.user_uploaded\media_1792089553933_db762d67.jpg"
IMG_CHAT = r"C:\Users\w2\.gemini\antigravity\brain\cabc0c47-659c-451f-a174-ab8b90b5ffa1\.user_uploaded\media_1792089571965_ec3c30cb.jpg"
IMG_REFUSE = r"C:\Users\w2\.gemini\antigravity\brain\cabc0c47-659c-451f-a174-ab8b90b5ffa1\.user_uploaded\media_1792089602877_c235aacc.jpg"


def rect(slide, x, y, w, h, color, alpha=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def rounded_rect(slide, x, y, w, h, color):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def txt(slide, x, y, w, h, text, size=18, bold=False, color=DARK,
        align=PP_ALIGN.LEFT, font="Segoe UI"):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font
    p.alignment = align
    return tf


def multi_txt(slide, x, y, w, h, lines, size=18, color=DARK, spacing=10, bold=False):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.font.name = "Segoe UI"
        p.font.bold = bold
        p.space_after = Pt(spacing)
    return tf


def slide_header(slide, title, subtitle=None):
    """Стандартная шапка слайда — синяя полоса сверху."""
    rect(slide, Inches(0), Inches(0), prs.slide_width, Inches(1.3), BLUE)
    # Тонкая акцентная линия
    rect(slide, Inches(0), Inches(1.3), prs.slide_width, Inches(0.06), ACCENT)
    txt(slide, Inches(0.8), Inches(0.3), Inches(11), Inches(0.8),
        title, 34, True, WHITE, PP_ALIGN.LEFT)
    if subtitle:
        txt(slide, Inches(0.8), Inches(0.85), Inches(11), Inches(0.4),
            subtitle, 16, False, RGBColor(0xBF, 0xDB, 0xFE))


def card(slide, x, y, w, h, title, desc, icon="", title_size=18, desc_size=14):
    """Карточка с заголовком и описанием."""
    rounded_rect(slide, x, y, w, h, WHITE)
    # Верхняя синяя полоска
    rect(slide, x + Inches(0.05), y, w - Inches(0.1), Inches(0.06), BLUE)
    full_title = f"{icon}  {title}" if icon else title
    txt(slide, x + Inches(0.2), y + Inches(0.2), w - Inches(0.4), Inches(0.5),
        full_title, title_size, True, BLUE, PP_ALIGN.CENTER)
    txt(slide, x + Inches(0.2), y + Inches(0.75), w - Inches(0.4), h - Inches(1),
        desc, desc_size, False, GRAY, PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════
# СЛАЙД 1 — Титульный
# ═══════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(prs.slide_layouts[6])
rect(sl, 0, 0, prs.slide_width, prs.slide_height, BLUE_DARK)
# Декоративные полосы
rect(sl, 0, Inches(3.4), prs.slide_width, Inches(0.04), ACCENT)
rect(sl, 0, Inches(4.6), prs.slide_width, Inches(0.04), ACCENT)

txt(sl, Inches(1), Inches(1.2), Inches(11.3), Inches(1),
    "⚖️", 72, False, WHITE, PP_ALIGN.CENTER)
txt(sl, Inches(1), Inches(2.3), Inches(11.3), Inches(1),
    "ТрудПраво", 60, True, WHITE, PP_ALIGN.CENTER)
txt(sl, Inches(1), Inches(3.6), Inches(11.3), Inches(0.8),
    "ИИ-помощник по трудовому законодательству Республики Казахстан",
    24, False, RGBColor(0xBF, 0xDB, 0xFE), PP_ALIGN.CENTER)

txt(sl, Inches(1), Inches(5.2), Inches(11.3), Inches(1.5),
    "RAG  •  Groq API  •  BM25 + ChromaDB  •  Sentence-Transformers  •  FastAPI",
    18, False, RGBColor(0x7D, 0xB0, 0xF0), PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════
# СЛАЙД 2 — Проблема
# ═══════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(prs.slide_layouts[6])
rect(sl, 0, 0, prs.slide_width, prs.slide_height, LIGHT_BG)
slide_header(sl, "Проблема")

problems = [
    ("📕", "Сложный закон",       "ТК РК — 204 статьи на\nюридическом языке"),
    ("❌", "Незнание прав",       "Работники не знают что\nделать при увольнении,\nзадержке зп, больничном"),
    ("💰", "Дорогие юристы",     "Консультация от 10 000 тг —\nне всем доступно"),
    ("🤖", "ChatGPT врёт",       "Выдумывает статьи,\nкоторых нет в ТК РК"),
]

for i, (icon, title, desc) in enumerate(problems):
    x = Inches(0.5) + Inches(i * 3.2)
    rounded_rect(sl, x, Inches(2.0), Inches(2.9), Inches(4.5), WHITE)
    txt(sl, x, Inches(2.3), Inches(2.9), Inches(0.8),
        icon, 48, False, DARK, PP_ALIGN.CENTER)
    txt(sl, x + Inches(0.15), Inches(3.3), Inches(2.6), Inches(0.6),
        title, 20, True, DARK, PP_ALIGN.CENTER)
    txt(sl, x + Inches(0.15), Inches(4.1), Inches(2.6), Inches(2),
        desc, 16, False, GRAY, PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════
# СЛАЙД 3 — Решение
# ═══════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(prs.slide_layouts[6])
rect(sl, 0, 0, prs.slide_width, prs.slide_height, LIGHT_BG)
slide_header(sl, "Решение — ТрудПраво")

solutions = [
    "✅  Отвечает ТОЛЬКО на основе реального текста Трудового кодекса РК",
    "📜  Каждый ответ содержит ссылку на конкретную статью и пункт",
    "💬  Понимает разговорный язык и опечатки: «зп», «уволиься», «больничный»",
    "🧠  Помнит контекст диалога — понимает короткие уточняющие вопросы",
    "🚫  Не составляет документы — только консультирует и направляет",
    "💸  Полностью бесплатный стек — без платных API",
]

rounded_rect(sl, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.2), WHITE)
multi_txt(sl, Inches(1.3), Inches(2.2), Inches(10.5), Inches(4.5),
          solutions, 22, DARK, spacing=16)

# ═══════════════════════════════════════════════════════════════
# СЛАЙД 4 — Архитектура
# ═══════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(prs.slide_layouts[6])
rect(sl, 0, 0, prs.slide_width, prs.slide_height, LIGHT_BG)
slide_header(sl, "Архитектура RAG-пайплайна")

steps = [
    ("1", "Вопрос",         "Пользователь задаёт вопрос\nна разговорном языке"),
    ("2", "Расширение",     "Стем-расширение: зп → заработная\nплата, увол → расторжение"),
    ("3", "Поиск",          "BM25 (ключевые слова) +\nChromaDB (семантика)"),
    ("4", "RRF Fusion",     "Объединение и ранжирование\nрезультатов двух поисков"),
    ("5", "Groq LLM",       "Генерация ответа с цитатами\n[S1], [S2] из контекста"),
    ("6", "Фильтрация",     "Удаление обещаний действий\nиз ответа бота"),
]

for i, (num, title, desc) in enumerate(steps):
    y = Inches(1.7) + Inches(i * 0.92)
    # Номер в круге
    circle = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.9), y + Inches(0.05), Inches(0.55), Inches(0.55))
    circle.fill.solid()
    circle.fill.fore_color.rgb = BLUE
    circle.line.fill.background()
    txt(sl, Inches(0.9), y + Inches(0.08), Inches(0.55), Inches(0.5),
        num, 22, True, WHITE, PP_ALIGN.CENTER)
    # Линия вниз
    if i < len(steps) - 1:
        rect(sl, Inches(1.14), y + Inches(0.6), Inches(0.04), Inches(0.35), BLUE_LIGHT)
    # Текст
    txt(sl, Inches(1.8), y + Inches(0.02), Inches(3), Inches(0.5),
        title, 20, True, DARK)
    txt(sl, Inches(5), y, Inches(8), Inches(0.7),
        desc, 16, False, GRAY)

# ═══════════════════════════════════════════════════════════════
# СЛАЙД 5 — Технологии
# ═══════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(prs.slide_layouts[6])
rect(sl, 0, 0, prs.slide_width, prs.slide_height, LIGHT_BG)
slide_header(sl, "Технологический стек")

techs = [
    ("Backend",      "FastAPI · Python 3.12 · SQLAlchemy · Uvicorn"),
    ("LLM",          "Groq API — openai/gpt-oss-120b (бесплатный)"),
    ("Эмбеддинги",   "paraphrase-multilingual-MiniLM-L12-v2 (локальный, 120 МБ)"),
    ("Поиск",        "BM25 (rank_bm25) + ChromaDB (векторный) + RRF Fusion"),
    ("База данных",  "SQLite (история чатов) + ChromaDB (1530 чанков ТК РК)"),
    ("Frontend",     "HTML · CSS · JavaScript — адаптивный чат-интерфейс"),
    ("Данные",       "Автоматический парсинг ТК РК с adilet.zan.kz → 1530 чанков"),
]

for i, (label, desc) in enumerate(techs):
    y = Inches(1.8) + Inches(i * 0.75)
    bg = WHITE if i % 2 == 0 else LIGHT_BG
    rounded_rect(sl, Inches(0.6), y, Inches(12.1), Inches(0.65), bg)
    # Label badge
    rounded_rect(sl, Inches(0.8), y + Inches(0.08), Inches(2.3), Inches(0.48), BLUE)
    txt(sl, Inches(0.8), y + Inches(0.1), Inches(2.3), Inches(0.45),
        label, 16, True, WHITE, PP_ALIGN.CENTER)
    txt(sl, Inches(3.4), y + Inches(0.12), Inches(9), Inches(0.45),
        desc, 17, False, DARK)

# ═══════════════════════════════════════════════════════════════
# СЛАЙД 6 — Интерфейс (скриншот главной)
# ═══════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(prs.slide_layouts[6])
rect(sl, 0, 0, prs.slide_width, prs.slide_height, LIGHT_BG)
slide_header(sl, "Интерфейс", "Главная страница — приветствие и быстрые темы")

# Тень под скрин
rounded_rect(sl, Inches(1.65), Inches(1.75), Inches(10.1), Inches(5.3),
             RGBColor(0xCB, 0xD5, 0xE1))
sl.shapes.add_picture(IMG_MAIN, Inches(1.6), Inches(1.7), Inches(10.1), Inches(5.3))

# ═══════════════════════════════════════════════════════════════
# СЛАЙД 7 — Демо: зарплата
# ═══════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(prs.slide_layouts[6])
rect(sl, 0, 0, prs.slide_width, prs.slide_height, LIGHT_BG)
slide_header(sl, "Демо: задержка зарплаты",
             "Бот находит ст. 113 ТК РК и даёт практические шаги")

rounded_rect(sl, Inches(0.65), Inches(1.75), Inches(12.1), Inches(5.3),
             RGBColor(0xCB, 0xD5, 0xE1))
sl.shapes.add_picture(IMG_CHAT, Inches(0.6), Inches(1.7), Inches(12.1), Inches(5.3))

# ═══════════════════════════════════════════════════════════════
# СЛАЙД 8 — Демо: отказ от действий
# ═══════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(prs.slide_layouts[6])
rect(sl, 0, 0, prs.slide_width, prs.slide_height, LIGHT_BG)
slide_header(sl, "Демо: безопасные ответы",
             "Бот НЕ составляет документы — только разъясняет нормы и направляет")

rounded_rect(sl, Inches(0.65), Inches(1.75), Inches(12.1), Inches(5.3),
             RGBColor(0xCB, 0xD5, 0xE1))
sl.shapes.add_picture(IMG_REFUSE, Inches(0.6), Inches(1.7), Inches(12.1), Inches(5.3))

# ═══════════════════════════════════════════════════════════════
# СЛАЙД 9 — Результаты тестов
# ═══════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(prs.slide_layouts[6])
rect(sl, 0, 0, prs.slide_width, prs.slide_height, LIGHT_BG)
slide_header(sl, "Результаты тестирования")

tests = [
    ("Задержка зарплаты",       "ст. 113 п. 1, п. 4",  "✅"),
    ("Увольнение (с опечаткой)","ст. 56, 58, 61",      "✅"),
    ("Контекстный вопрос",      "ст. 56 п. 3",         "✅"),
    ("Испытательный срок",      "ст. 36 п. 2",         "✅"),
    ("Больничный / увольнение", "ст. 54 п. 1",         "✅"),
    ("Сверхурочная работа",     "ст. 77, 108",         "✅"),
    ("Вопрос не по теме",       "— корректный отказ",  "✅"),
    ("Беременность",            "ст. 54, 58",          "✅"),
]

# Таблица
headers = [("Тема вопроса", Inches(5)), ("Найденные статьи", Inches(3.5)), ("Результат", Inches(2))]
x_start = Inches(1.2)
y_header = Inches(1.8)

# Header row
rect(sl, x_start, y_header, Inches(10.9), Inches(0.55), BLUE)
x_off = x_start
for h_text, h_w in headers:
    txt(sl, x_off + Inches(0.15), y_header + Inches(0.08), h_w, Inches(0.45),
        h_text, 17, True, WHITE)
    x_off += h_w

for i, (theme, articles, result) in enumerate(tests):
    y = Inches(2.45) + Inches(i * 0.52)
    bg = WHITE if i % 2 == 0 else LIGHT_BG
    rect(sl, x_start, y, Inches(10.9), Inches(0.48), bg)

    x_off = x_start
    txt(sl, x_off + Inches(0.15), y + Inches(0.05), headers[0][1], Inches(0.4),
        theme, 16, False, DARK)
    x_off += headers[0][1]
    txt(sl, x_off + Inches(0.15), y + Inches(0.05), headers[1][1], Inches(0.4),
        articles, 16, False, GRAY)
    x_off += headers[1][1]
    txt(sl, x_off + Inches(0.15), y + Inches(0.05), headers[2][1], Inches(0.4),
        result, 16, True, GREEN)

# Итого
rounded_rect(sl, Inches(3.5), Inches(6.8), Inches(6.3), Inches(0.55), GREEN)
txt(sl, Inches(3.5), Inches(6.83), Inches(6.3), Inches(0.5),
    "8/8 корректных ответов   •   24/24 unit-тестов поиска", 18, True, WHITE, PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════
# СЛАЙД 10 — Заключение
# ═══════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(prs.slide_layouts[6])
rect(sl, 0, 0, prs.slide_width, prs.slide_height, BLUE_DARK)
rect(sl, 0, Inches(3.2), prs.slide_width, Inches(0.04), ACCENT)

txt(sl, Inches(1), Inches(0.8), Inches(11.3), Inches(1),
    "Спасибо за внимание!", 52, True, WHITE, PP_ALIGN.CENTER)
txt(sl, Inches(1), Inches(1.8), Inches(11.3), Inches(0.6),
    "⚖️ ТрудПраво", 28, False, ACCENT, PP_ALIGN.CENTER)

summary = [
    "✅  RAG-система на базе реального текста ТК РК (1530 чанков)",
    "✅  Гибридный поиск: BM25 + векторный + RRF fusion",
    "✅  Устойчивость к опечаткам через стем-расширение запросов",
    "✅  Память диалога — понимание контекста и уточняющих вопросов",
    "✅  Безопасные ответы — не обещает и не составляет документы",
    "✅  100% бесплатный стек: Groq + sentence-transformers + SQLite",
]

multi_txt(sl, Inches(2), Inches(3.7), Inches(9.3), Inches(3.5),
          summary, 22, WHITE, spacing=14)

# ── Сохранение ──
out = r"C:\Users\w2\Desktop\itprod\ТрудПраво_Презентация.pptx"
prs.save(out)
print(f"OK: {out}")
