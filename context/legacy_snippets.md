# LEGACY SNIPPETS: Полезный код из старого прототипа
# Этот файл содержит проверенные Pydantic-схемы, регулярные выражения и утилиты,
# которые нужно использовать в новой архитектуре.

# ==========================================
# 1. PYDANTIC СХЕМЫ (Для слоя api/schemas/report.py)
# ==========================================
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class LocationDTO(BaseModel):
    # Новая структура для точных координат ошибки
    page_number: Optional[int] = Field(None, description="Физическая страница")
    paragraph_index: Optional[int] = Field(None, description="Порядковый номер абзаца")
    item_title: Optional[str] = Field(None, description="Например: Таблица 2")
    snippet: Optional[str] = Field(None, description="Фрагмент текста с ошибкой")

class ViolationSchema(BaseModel):
    rule_id: str = Field(..., description="Идентификатор правила")
    severity: str = Field(default="WARNING", description="ERROR | WARNING | INFO")
    message: str = Field(..., description="Описание несоответствия")
    location: LocationDTO
    actual_value: Optional[str] = None
    expected_value: Optional[str] = None

class DocumentStatsSchema(BaseModel):
    total_paragraphs: int
    total_tables: int
    total_sections: int

class ReportResponse(BaseModel):
    job_id: str
    filename: str
    is_valid: bool
    summary: str
    total_errors: int = 0
    total_warnings: int = 0
    stats: DocumentStatsSchema
    violations: List[ViolationSchema]


# ==========================================
# 2. РЕГУЛЯРНЫЕ ВЫРАЖЕНИЯ (Для слоя rule_engine/rules/)
# ==========================================
import re

# Для таблиц и иллюстраций (Учитывает разные виды тире)
FIGURE_CAPTION_REGEX = re.compile(r"^Рисунок\s+(\d+(?:\.\d+)*)\s*[—–-]\s*(.+)$", re.IGNORECASE)
TABLE_CAPTION_REGEX = re.compile(r"^Таблица\s+(\d+(?:\.\d+)*)\s*[—–-]\s*(.+)$", re.IGNORECASE)

# Для структуры (Обязательные разделы)
REQUIRED_SECTIONS = [
    ("ВВЕДЕНИЕ", r"^\s*введение\b"),
    ("ОСНОВНАЯ ЧАСТЬ", r"^\s*(глава|раздел|\d+[\.\s])"),
    ("ЗАКЛЮЧЕНИЕ", r"^\s*заключение\b"),
    ("СПИСОК ЛИТЕРАТУРЫ", r"^\s*(?:список\s+(?:использованн(?:ых|ой)|используем(?:ой|ых)|основной)?\s*(?:источников(?:\s+и\s+литературы)?|литературы(?:\s+и\s+источников)?)|список\s+(?:источников|литературы)|библиографический\s+список|библиография|литература)\b"),
]

# Для библиографии (Поиск квадратных скобок)
BRACKET_REF_REGEX = re.compile(r"\[([^\]]+)\]")

def parse_bracket_content(content: str) -> set[int]:
    """Парсит ссылки типа '1, 2, 5', '3-6', '10, с. 15' в множество чисел {1, 2, 3, 4, 5, 6, 10}"""
    nums = set()
    parts = re.split(r"[,;]", content)
    for part in parts:
        part = part.strip()
        if not part: continue
        # Отсекаем указания страниц: "с. 15"
        part_clean = re.sub(r"(с|стр|с\.|стр\.|p\.|page)\s*\d+.*", "", part, flags=re.IGNORECASE).strip()
        # Диапазон "3-6"
        range_match = re.match(r"^(\d+)\s*[–—\-]\s*(\d+)$", part_clean)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if 0 < start <= end and (end - start) < 100:
                nums.update(range(start, end + 1))
            continue
        # Одиночное число
        num_match = re.match(r"^(\d+)", part_clean)
        if num_match:
            nums.add(int(num_match.group(1)))
    return nums


# ==========================================
# 3. УТИЛИТЫ И ХЕЛПЕРЫ
# ==========================================
import difflib

def normalize_whitespace(text: str) -> str:
    """Схлопывает пробельные символы и удаляет лидирующие/конечные пробелы."""
    return re.sub(r"\s+", " ", text).strip()

def matches_heading_fuzzy(norm_a: str, norm_b: str) -> bool:
    """Нечёткое сравнение двух заголовков (полезно для сверки Оглавления с текстом)."""
    if norm_a == norm_b: return True
    text_a = re.sub(r"^[\d\s]+", "", norm_a).strip()
    text_b = re.sub(r"^[\d\s]+", "", norm_b).strip()
    if text_a and text_b:
        if text_a == text_b or text_a in text_b or text_b in text_a:
            return True
    if len(norm_a) > 6 and len(norm_b) > 6:
        if difflib.SequenceMatcher(None, norm_a, norm_b).ratio() >= 0.82:
            return True
    return False