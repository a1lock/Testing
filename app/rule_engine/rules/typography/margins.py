"""Page margins validation rule."""

from app.domain.dto.document import DocumentDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule


@register_rule("PAGE_MARGINS")
class MarginsRule(BaseRule):
    """Validates that document page margins match the specified standard requirements."""

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Check page margins in millimeters.

        Args:
            doc: Extracted document DTO containing margin fields.
            params: Parameters including 'left_mm', 'right_mm', 'top_mm', 'bottom_mm', and 'tolerance_mm'.

        Returns:
            List of detected ViolationDTO instances (empty if compliant).
        """
        left_mm = float(params.get("left_mm", 30.0))
        right_mm = float(params.get("right_mm", 15.0))
        top_mm = float(params.get("top_mm", 20.0))
        bottom_mm = float(params.get("bottom_mm", 20.0))
        tolerance_mm = float(params.get("tolerance_mm", 1.0))

        violations: list[ViolationDTO] = []

        fields = [
            ("левое", doc.margin_left_mm, left_mm),
            ("правое", doc.margin_right_mm, right_mm),
            ("верхнее", doc.margin_top_mm, top_mm),
            ("нижнее", doc.margin_bottom_mm, bottom_mm),
        ]

        for name, actual, expected in fields:
            if actual is None:
                violations.append(
                    ViolationDTO(
                        rule_id=self.rule_id,
                        severity="ERROR",
                        message=(
                            f"Не задан размер поля страницы: {name}. "
                            f"Ожидается {expected:.1f} мм."
                        ),
                        location=LocationDTO(item_title=f"Поле страницы ({name})"),
                        actual_value="Не определено",
                        expected_value=f"{expected:.1f} мм",
                    )
                )
            elif abs(actual - expected) > tolerance_mm:
                violations.append(
                    ViolationDTO(
                        rule_id=self.rule_id,
                        severity="ERROR",
                        message=(
                            f"Неверный размер поля страницы ({name}). "
                            f"Требуется {expected:.1f} мм (допуск ±{tolerance_mm:.1f} мм), "
                            f"обнаружено {actual:.1f} мм."
                        ),
                        location=LocationDTO(item_title=f"Поле страницы ({name})"),
                        actual_value=f"{actual:.1f} мм",
                        expected_value=f"{expected:.1f} мм",
                    )
                )

        return violations
