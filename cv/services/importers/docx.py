from docx import Document

from cv.services.importers.base import CVImportAdapter


def extract_text_from_docx(uploaded_file):
    uploaded_file.seek(0)
    document = Document(uploaded_file)
    parts = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    uploaded_file.seek(0)
    return "\n".join(parts).strip()


class DOCXImportAdapter(CVImportAdapter):
    source_type = "docx"
    extract_text = staticmethod(extract_text_from_docx)
