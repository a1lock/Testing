from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class LocationDTO(BaseModel):
    """Coordinates and text snippet pinpointing a violation location."""

    page_number: Optional[int] = Field(None, description="Физическая страница")
    paragraph_index: Optional[int] = Field(None, description="Порядковый номер абзаца")
    item_title: Optional[str] = Field(None, description="Например: Таблица 2")
    snippet: Optional[str] = Field(None, description="Фрагмент текста с ошибкой")

    model_config = ConfigDict(from_attributes=True)


class ViolationSchema(BaseModel):
    """Schema representing a single detected violation."""

    rule_id: str = Field(..., description="Идентификатор правила")
    severity: str = Field(default="WARNING", description="ERROR | WARNING | INFO")
    message: str = Field(..., description="Описание несоответствия")
    location: LocationDTO = Field(default_factory=LocationDTO)
    actual_value: Optional[str] = None
    expected_value: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentStatsSchema(BaseModel):
    """High-level structural counts for the analyzed document."""

    total_paragraphs: int = Field(0, description="Общее число абзацев")
    total_tables: int = Field(0, description="Общее число таблиц")
    total_sections: int = Field(1, description="Общее число секций")

    model_config = ConfigDict(from_attributes=True)


class ReportResponse(BaseModel):
    """Complete validation report returned to client."""

    job_id: str = Field(..., description="UUID задачи")
    filename: Optional[str] = Field("document.docx", description="Имя проверенного файла")
    is_valid: bool = Field(..., description="Успешность проверки (True если нет ERROR)")
    summary: str = Field("", description="Краткое текстовое резюме отчета")
    total_errors: int = Field(0, description="Количество критических ошибок")
    total_warnings: int = Field(0, description="Количество предупреждений")
    stats: Optional[DocumentStatsSchema] = Field(None, description="Статистика документа")
    violations: List[ViolationSchema] = Field(default_factory=list, description="Список нарушений")

    model_config = ConfigDict(from_attributes=True)
