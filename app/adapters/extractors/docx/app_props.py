import zipfile
from lxml import etree

EXTENDED_PROPERTIES_NS = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
NAMESPACES = {"ep": EXTENDED_PROPERTIES_NS}


def extract_page_count(docx_path: str) -> tuple[int | None, int | None]:
    """
    Extracts page count and word count metadata from docProps/app.xml inside a .docx package.

    Args:
        docx_path: Absolute or relative path to the .docx archive.

    Returns:
        tuple[int | None, int | None]: (pages, words) count or (None, None) if not present or on error.
    """
    try:
        with zipfile.ZipFile(docx_path, "r") as zf:
            if "docProps/app.xml" not in zf.namelist():
                return None, None

            xml_data = zf.read("docProps/app.xml")
            root = etree.fromstring(xml_data)

            # Search with standard OpenXML extended-properties namespace, with fallback to any namespace
            pages_elem = root.find("ep:Pages", namespaces=NAMESPACES)
            if pages_elem is None:
                pages_elem = root.find(".//{*}Pages")

            words_elem = root.find("ep:Words", namespaces=NAMESPACES)
            if words_elem is None:
                words_elem = root.find(".//{*}Words")

            pages: int | None = None
            if pages_elem is not None and pages_elem.text:
                text_val = pages_elem.text.strip()
                if text_val.isdigit():
                    pages = int(text_val)

            words: int | None = None
            if words_elem is not None and words_elem.text:
                text_val = words_elem.text.strip()
                if text_val.isdigit():
                    words = int(text_val)

            return pages, words
    except Exception:
        return None, None

