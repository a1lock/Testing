"""Module for extracting formatting and resolving style hierarchies from docx XML."""

from typing import Any
import docx

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NAMESPACES = {"w": W_NS}


def safe_xpath(element: Any, query: str) -> list[Any]:
    """
    Evaluates xpath query safely across both python-docx BaseOxmlElement and raw lxml Elements.
    """
    if element is None:
        return []
    try:
        return element.xpath(query, namespaces=NAMESPACES)
    except TypeError:
        # BaseOxmlElement.xpath() from python-docx doesn't accept namespaces argument
        return element.xpath(query)
    except Exception:
        try:
            return element.xpath(query)
        except Exception:
            return []


class StyleHierarchyResolver:
    """Resolves inherited formatting properties across Microsoft Word style hierarchies."""

    def __init__(self, doc: docx.Document) -> None:
        self.doc = doc
        self._style_elements_by_id: dict[str, Any] = {}
        self._style_elements_by_name: dict[str, Any] = {}
        self._doc_default_indent: float | None = None
        self._doc_default_alignment: str | None = None
        self._doc_default_font_size: float | None = None
        self._doc_default_font_name: str | None = None

        self._indent_cache: dict[str, float | None] = {}
        self._alignment_cache: dict[str, str | None] = {}
        self._font_size_cache: dict[str, float | None] = {}
        self._font_name_cache: dict[str, str | None] = {}

        self._index_styles()

    def _index_styles(self) -> None:
        """Indexes all style elements and docDefaults from styles.xml."""
        if not hasattr(self.doc, "styles") or self.doc.styles is None:
            return

        styles_elem = getattr(self.doc.styles, "element", None)
        if styles_elem is None:
            return

        # 1. Parse docDefaults
        doc_defaults = safe_xpath(styles_elem, "./w:docDefaults")
        if doc_defaults:
            dd = doc_defaults[0]
            ind_nodes = safe_xpath(dd, "./w:pPrDefault/w:pPr/w:ind")
            if ind_nodes:
                self._doc_default_indent = self._extract_indent_from_ind(ind_nodes[0])

            jc_nodes = safe_xpath(dd, "./w:pPrDefault/w:pPr/w:jc/@w:val")
            if jc_nodes:
                self._doc_default_alignment = self._map_alignment(jc_nodes[0])

            sz_nodes = safe_xpath(dd, "./w:rPrDefault/w:rPr/w:sz/@w:val")
            if sz_nodes:
                try:
                    self._doc_default_font_size = float(sz_nodes[0]) / 2.0
                except ValueError:
                    pass

            rfonts_nodes = safe_xpath(dd, "./w:rPrDefault/w:rPr/w:rFonts/@w:ascii")
            if rfonts_nodes:
                self._doc_default_font_name = rfonts_nodes[0]

        # 2. Index styles by styleId and by name
        style_nodes = safe_xpath(styles_elem, "./w:style")
        for s in style_nodes:
            sid = s.get(f"{{{W_NS}}}styleId")
            if sid:
                self._style_elements_by_id[sid] = s

            name_nodes = safe_xpath(s, "./w:name/@w:val")
            if name_nodes:
                name_val = name_nodes[0]
                self._style_elements_by_name[name_val.lower()] = s

    @staticmethod
    def _extract_indent_from_ind(ind_elem: Any) -> float | None:
        if ind_elem is None:
            return None

        # 1. First line indent (dxa / twips)
        fl = ind_elem.get(f"{{{W_NS}}}firstLine")
        if fl is not None:
            try:
                return float(fl) * 25.4 / 1440.0
            except ValueError:
                pass

        # 2. Hanging indent (negative first line)
        hanging = ind_elem.get(f"{{{W_NS}}}hanging")
        if hanging is not None:
            try:
                return -float(hanging) * 25.4 / 1440.0
            except ValueError:
                pass

        # 3. First line in characters (e.g. 125 = 1.25 chars)
        flc = ind_elem.get(f"{{{W_NS}}}firstLineChars")
        if flc is not None:
            try:
                chars = float(flc) / 100.0
                return chars * 10.0
            except ValueError:
                pass

        # 4. Hanging in characters
        hc = ind_elem.get(f"{{{W_NS}}}hangingChars")
        if hc is not None:
            try:
                chars = float(hc) / 100.0
                return -chars * 10.0
            except ValueError:
                pass

        return None

    @staticmethod
    def _map_alignment(jc_val: str | None) -> str | None:
        if not jc_val:
            return None
        jc_lower = jc_val.lower()
        if jc_lower in ("both", "justify"):
            return "JUSTIFY"
        if jc_lower == "center":
            return "CENTER"
        if jc_lower in ("right", "end"):
            return "RIGHT"
        if jc_lower in ("left", "start"):
            return "LEFT"
        return jc_val.upper()

    def get_paragraph_indent_mm(self, paragraph: Any) -> float:
        """
        Determines the effective first line indent of a paragraph, checking:
        1. Direct paragraph formatting (python-docx and raw XML).
        2. Paragraph style and its inheritance chain (python-docx and XML).
        3. Document defaults (docDefaults).
        Falls back to 0.0 mm.
        """
        # 1. Direct python-docx first_line_indent
        try:
            if paragraph.paragraph_format and paragraph.paragraph_format.first_line_indent is not None:
                return float(paragraph.paragraph_format.first_line_indent.mm)
        except Exception:
            pass

        # 2. Direct raw XML on paragraph <w:pPr>/<w:ind>
        if hasattr(paragraph, "_p") and paragraph._p is not None:
            ind_nodes = safe_xpath(paragraph._p, "./w:pPr/w:ind")
            if ind_nodes:
                val = self._extract_indent_from_ind(ind_nodes[0])
                if val is not None:
                    return val

        # 3. Style hierarchy
        style_key = self._get_paragraph_style_key(paragraph)
        if style_key:
            if style_key in self._indent_cache:
                cached = self._indent_cache[style_key]
                if cached is not None:
                    return cached
            else:
                indent = self._resolve_style_indent(paragraph)
                self._indent_cache[style_key] = indent
                if indent is not None:
                    return indent

        # 4. docDefaults
        if self._doc_default_indent is not None:
            return self._doc_default_indent

        return 0.0

    def _get_paragraph_style_key(self, paragraph: Any) -> str | None:
        if hasattr(paragraph, "_p") and paragraph._p is not None:
            p_style_nodes = safe_xpath(paragraph._p, "./w:pPr/w:pStyle/@w:val")
            if p_style_nodes:
                return p_style_nodes[0]
        if hasattr(paragraph, "style") and paragraph.style:
            return getattr(paragraph.style, "name", None)
        return None

    def _resolve_style_indent(self, paragraph: Any) -> float | None:
        # A. Traverse python-docx style hierarchy
        curr_style = getattr(paragraph, "style", None)
        visited_docx_styles: set[int] = set()
        while curr_style is not None and id(curr_style) not in visited_docx_styles:
            visited_docx_styles.add(id(curr_style))
            try:
                if curr_style.paragraph_format and curr_style.paragraph_format.first_line_indent is not None:
                    return float(curr_style.paragraph_format.first_line_indent.mm)
            except Exception:
                pass
            curr_style = getattr(curr_style, "base_style", None)

        # B. Traverse XML style hierarchy in doc.styles
        style_key = self._get_paragraph_style_key(paragraph)
        visited_xml_styles: set[int] = set()
        curr_elem = self._find_style_element(style_key)

        while curr_elem is not None and id(curr_elem) not in visited_xml_styles:
            visited_xml_styles.add(id(curr_elem))
            ind_nodes = safe_xpath(curr_elem, "./w:pPr/w:ind")
            if ind_nodes:
                val = self._extract_indent_from_ind(ind_nodes[0])
                if val is not None:
                    return val

            # Follow w:basedOn
            based_on_nodes = safe_xpath(curr_elem, "./w:basedOn/@w:val")
            if based_on_nodes:
                curr_elem = self._find_style_element(based_on_nodes[0])
            else:
                curr_elem = None

        return None

    def _find_style_element(self, key: str | None) -> Any | None:
        if not key:
            return None
        if key in self._style_elements_by_id:
            return self._style_elements_by_id[key]
        key_lower = key.lower()
        if key_lower in self._style_elements_by_name:
            return self._style_elements_by_name[key_lower]
        return None

    def get_paragraph_alignment(self, paragraph: Any) -> str | None:
        """Determines paragraph alignment considering direct formatting and style inheritance."""
        # 1. Direct python-docx
        try:
            if paragraph.alignment is not None:
                return getattr(paragraph.alignment, "name", str(paragraph.alignment)).upper()
        except Exception:
            pass

        # 2. Direct XML
        if hasattr(paragraph, "_p") and paragraph._p is not None:
            jc_nodes = safe_xpath(paragraph._p, "./w:pPr/w:jc/@w:val")
            if jc_nodes:
                return self._map_alignment(jc_nodes[0])

        # 3. Style hierarchy
        style_key = self._get_paragraph_style_key(paragraph)
        if style_key:
            if style_key in self._alignment_cache:
                return self._alignment_cache[style_key]

            alignment = self._resolve_style_alignment(paragraph)
            self._alignment_cache[style_key] = alignment
            if alignment is not None:
                return alignment

        # 4. docDefaults
        return self._doc_default_alignment

    def _resolve_style_alignment(self, paragraph: Any) -> str | None:
        curr_style = getattr(paragraph, "style", None)
        visited: set[int] = set()
        while curr_style is not None and id(curr_style) not in visited:
            visited.add(id(curr_style))
            try:
                if curr_style.paragraph_format and curr_style.paragraph_format.alignment is not None:
                    return getattr(curr_style.paragraph_format.alignment, "name", str(curr_style.paragraph_format.alignment)).upper()
            except Exception:
                pass
            curr_style = getattr(curr_style, "base_style", None)

        style_key = self._get_paragraph_style_key(paragraph)
        curr_elem = self._find_style_element(style_key)
        visited_xml: set[int] = set()
        while curr_elem is not None and id(curr_elem) not in visited_xml:
            visited_xml.add(id(curr_elem))
            jc_nodes = safe_xpath(curr_elem, "./w:pPr/w:jc/@w:val")
            if jc_nodes:
                return self._map_alignment(jc_nodes[0])
            based_on_nodes = safe_xpath(curr_elem, "./w:basedOn/@w:val")
            curr_elem = self._find_style_element(based_on_nodes[0]) if based_on_nodes else None

        return None

    def get_run_font_size(self, run: Any, paragraph: Any) -> float | None:
        """Determines run font size in pt, checking run, paragraph style, and doc defaults."""
        # 1. Direct python-docx
        try:
            if run.font and run.font.size is not None:
                return float(run.font.size.pt)
        except Exception:
            pass

        # 2. Direct run XML
        if hasattr(run, "_r") and run._r is not None:
            sz_nodes = safe_xpath(run._r, "./w:rPr/w:sz/@w:val")
            if sz_nodes:
                try:
                    return float(sz_nodes[0]) / 2.0
                except ValueError:
                    pass

        # 3. Paragraph style
        style_key = self._get_paragraph_style_key(paragraph)
        if style_key:
            if style_key in self._font_size_cache:
                return self._font_size_cache[style_key]

            size = self._resolve_style_font_size(paragraph)
            self._font_size_cache[style_key] = size
            if size is not None:
                return size

        return None

    def _resolve_style_font_size(self, paragraph: Any) -> float | None:
        curr_style = getattr(paragraph, "style", None)
        visited: set[int] = set()
        while curr_style is not None and id(curr_style) not in visited:
            visited.add(id(curr_style))
            try:
                if curr_style.font and curr_style.font.size is not None:
                    return float(curr_style.font.size.pt)
            except Exception:
                pass
            curr_style = getattr(curr_style, "base_style", None)

        style_key = self._get_paragraph_style_key(paragraph)
        curr_elem = self._find_style_element(style_key)
        visited_xml: set[int] = set()
        while curr_elem is not None and id(curr_elem) not in visited_xml:
            visited_xml.add(id(curr_elem))
            sz_nodes = safe_xpath(curr_elem, "./w:rPr/w:sz/@w:val")
            if sz_nodes:
                try:
                    return float(sz_nodes[0]) / 2.0
                except ValueError:
                    pass
            based_on_nodes = safe_xpath(curr_elem, "./w:basedOn/@w:val")
            curr_elem = self._find_style_element(based_on_nodes[0]) if based_on_nodes else None

        return None

    def get_list_level(self, paragraph: Any) -> int | None:
        """Extracts list nesting level from paragraph or its style."""
        if hasattr(paragraph, "_p") and paragraph._p is not None:
            ilvl_nodes = safe_xpath(paragraph._p, "./w:pPr/w:numPr/w:ilvl/@w:val")
            if ilvl_nodes:
                try:
                    return int(ilvl_nodes[0])
                except ValueError:
                    pass

        style_key = self._get_paragraph_style_key(paragraph)
        curr_elem = self._find_style_element(style_key)
        if curr_elem is not None:
            ilvl_nodes = safe_xpath(curr_elem, "./w:pPr/w:numPr/w:ilvl/@w:val")
            if ilvl_nodes:
                try:
                    return int(ilvl_nodes[0])
                except ValueError:
                    pass

        return None
