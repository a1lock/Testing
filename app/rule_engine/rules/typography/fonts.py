"""Main text font validation rule."""

from app.domain.dto.document import DocumentDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule


@register_rule("MAIN_TEXT_FONT")
class MainTextFontRule(BaseRule):
    """Validates that main body text conforms to expected font size."""

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Check all body text runs for valid font size.

        Args:
            doc: Extracted document DTO.
            params: Parameters including 'expected_font_name' (default 'Times New Roman'),
                    'expected_size_pt' (default 14.0), and 'tolerance_pt' (default 0.5).

        Returns:
            List of detected ViolationDTO instances (empty if compliant).
        """
        expected_size_pt = float(params.get("expected_size_pt", 14.0))
        tolerance_pt = float(params.get("tolerance_pt", 0.5))
        _expected_font_name = str(params.get("expected_font_name", "Times New Roman"))

        violations: list[ViolationDTO] = []

        for i, p in enumerate(doc.paragraphs):
            # Skip empty lines and headings
            if not p.text.strip() or p.is_heading:
                continue

            style_lower = (p.style_name or "").lower()
            if "heading" in style_lower or "заголовок" in style_lower:
                continue

            seen_sizes_in_p: set[float] = set()

            for run in p.runs:
                if run.font_size_pt is None:
                    continue

                if abs(run.font_size_pt - expected_size_pt) > tolerance_pt:
                    size_key = round(run.font_size_pt, 1)
                    if size_key not in seen_sizes_in_p:
                        seen_sizes_in_p.add(size_key)
                        snippet = p.text.strip()[:60]
                        violations.append(
                            ViolationDTO(
                                rule_id=self.rule_id,
                                severity="ERROR",
                                message=(
                                    f"Неверный размер шрифта основного текста. "
                                    f"Требуется {expected_size_pt:.1f} пт (допуск ±{tolerance_pt:.1f} пт), "
                                    f"обнаружено {run.font_size_pt:.1f} пт."
                                ),
                                location=LocationDTO(
                                    paragraph_index=i,
                                    snippet=snippet,
                                ),
                                actual_value=f"{run.font_size_pt:.1f} пт",
                                expected_value=f"{expected_size_pt:.1f} пт",
                            )
                        )

        return violations
