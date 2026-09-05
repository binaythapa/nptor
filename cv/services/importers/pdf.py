import pdfplumber

from cv.services.importers.base import CVImportAdapter


def extract_text_from_pdf(uploaded_file):
    uploaded_file.seek(0)
    pages = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text.strip())
    uploaded_file.seek(0)
    return "\n\n".join(pages).strip()


class PDFImportAdapter(CVImportAdapter):
    source_type = "pdf"
    extract_text = staticmethod(extract_text_from_pdf)
