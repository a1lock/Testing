"""Figures format and cross-references validation rule."""

import re

from app.domain.dto.document import DocumentDTO, ParagraphDTO
from app.domain.dto.violation import LocationDTO, ViolationDTO
from app.rule_engine.base import BaseRule
from app.rule_engine.registry import register_rule

FIGURE_CAPTION_REGEX = re.compile(r"^Рисунок\s+(\d+(?:\.\d+)*)\s*[—–-]\s*(.+)$", re.IGNORECASE)


@register_rule("FIGURES_FORMAT")
class FiguresRule(BaseRule):
    """Validates figure captions formatting (alignment, dot) and cross-references in text."""

    def check(self, doc: DocumentDTO, params: dict) -> list[ViolationDTO]:
        """Validate figure captions and cross-references throughout document body.

        Args:
            doc: Extracted document DTO.
            params: Rule parameters (optional).

        Returns:
            List of detected ViolationDTO instances (empty if compliant).
        """
        violations: list[ViolationDTO] = []

        # 1. Identify all figure captions
        figures: list[tuple[int, str, ParagraphDTO]] = []  # (p_idx, fig_num, paragraph)
        caption_indices: set[int] = set()

        for i, p in enumerate(doc.paragraphs):
            text = p.text.strip()
            if not text:
                continue

            match = FIGURE_CAPTION_REGEX.match(text)
            if match:
                fig_num = match.group(1)
                figures.append((i, fig_num, p))
                caption_indices.add(i)

                # 2. Check caption alignment: strictly CENTER (ERROR if not CENTER)
                if p.alignment != "CENTER":
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="ERROR",
                            message=(
                                f"Подпись рисунка '{fig_num}' должна быть выровнена по центру. "
                                f"Обнаружено выравнивание: {p.alignment or 'по умолчанию'}."
                            ),
                            location=LocationDTO(paragraph_index=i, snippet=text[:60]),
                            actual_value=p.alignment or "None",
                            expected_value="CENTER",
                        )
                    )

                # 3. Check trailing dot: prohibited (WARNING if present)
                if text.endswith("."):
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="WARNING",
                            message=f"В конце подписи рисунка '{fig_num}' точка не ставится.",
                            location=LocationDTO(paragraph_index=i, snippet=text[:60]),
                            actual_value=text[-10:],
                            expected_value="Без точки",
                        )
                    )

                # 4. Check position relative to image: caption must NOT be placed ABOVE the image
                prev_img_p = None
                for k in range(i - 1, -1, -1):
                    pk = doc.paragraphs[k]
                    if getattr(pk, "has_image", False):
                        prev_img_p = pk
                        break
                    if pk.text.strip():
                        break

                next_img_p = None
                for k in range(i + 1, min(i + 4, len(doc.paragraphs))):
                    pk = doc.paragraphs[k]
                    if getattr(pk, "has_image", False):
                        next_img_p = pk
                        break
                    if pk.text.strip():
                        break

                if next_img_p is not None and prev_img_p is None:
                    violations.append(
                        ViolationDTO(
                            rule_id=self.rule_id,
                            severity="ERROR",
                            message=(
                                f"Подпись рисунка '{fig_num}' расположена над иллюстрацией. "
                                f"По ГОСТ 7.32 (п. 5.3.2) подпись должна находиться под иллюстрацией."
                            ),
                            location=LocationDTO(paragraph_index=i, snippet=text[:60]),
                            actual_value="Подпись над рисунком",
                            expected_value="Подпись под рисунком",
                        )
                    )

        # 4. Check cross-references in non-caption text
        body_text = "\n".join(
            p.text for idx, p in enumerate(doc.paragraphs) if idx not in caption_indices
        )

        for p_idx, fig_num, p in figures:
            caption_text = p.text.strip()
            # Reference patterns: "рисунок X", "рис. X", "рис X", "(рисунок X)", "(рис. X)"
            ref_pattern = rf"(?:\b|\()(?:\u0440\u0438\u0441\u0443\u043d[а-я]*|\u0440\u0438\u0441\.?)\s+{re.escape(fig_num)}(?!(?:\.\d|\d))"
            if not re.search(ref_pattern, body_text, re.IGNORECASE):
                violations.append(
                    ViolationDTO(
                        rule_id=self.rule_id,
                        severity="ERROR",
                        message=f"Отсутствует ссылка на рисунок {fig_num} в тексте",
                        location=LocationDTO(paragraph_index=p_idx, snippet=caption_text[:60]),
                        actual_value="Ссылка отсутствует",
                        expected_value=f"Ссылка на рисунок {fig_num}",
                    )
                )

        return violations
