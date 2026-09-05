from io import BytesIO

from django.core.files.base import ContentFile
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

from cv.models_document import DocumentArtifact
from cv.services.documents.base import DocumentGenerator
from cv.services.documents.renderer import get_render_config


MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
FONT_MAP = {
    "Helvetica": "Arial",
    "Helvetica-Bold": "Arial",
    "Times-Roman": "Times New Roman",
    "Times-Bold": "Times New Roman",
    "Courier": "Courier New",
}


def _rgb(hex_color):
    value = hex_color.lstrip("#")
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


class DOCXGenerator(DocumentGenerator):
    def generate(self, version):
        payload = version.snapshot
        config = get_render_config(payload.get("template", {}))
        document = Document()
        section = document.sections[0]
        margin = Inches(config["margin"] / 72)
        section.top_margin = margin
        section.bottom_margin = margin
        section.left_margin = margin
        section.right_margin = margin

        normal = document.styles["Normal"]
        normal.font.name = FONT_MAP.get(config["font_name"], "Arial")
        normal.font.size = Pt(config["font_size"])
        accent = _rgb(config["accent_color"])

        contact = payload.get("contact", {})
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        if name:
            paragraph = document.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = paragraph.add_run(name)
            run.bold = True
            run.font.name = FONT_MAP.get(config["font_name"], "Arial")
            run.font.size = Pt(config["heading_size"] + 7)
            run.font.color.rgb = accent
        if payload.get("professional_title"):
            paragraph = document.add_paragraph(payload["professional_title"])
            paragraph.runs[0].font.size = Pt(config["font_size"] + 2)
            paragraph.runs[0].font.color.rgb = accent
        details = [contact.get("email"), contact.get("phone"), contact.get("location")]
        details = [str(value) for value in details if value]
        if payload.get("linkedin_url"):
            details.append(payload["linkedin_url"])
        if payload.get("portfolio_url"):
            details.append(payload["portfolio_url"])
        if details:
            document.add_paragraph(" | ".join(details))

        sections = (
            ("Summary", payload.get("summary"), "text"),
            ("Experience", payload.get("experiences", []), "experience"),
            ("Education", payload.get("educations", []), "education"),
            ("Skills", payload.get("skills", []), "skills"),
            ("Projects", payload.get("projects", []), "projects"),
            ("Certifications", payload.get("certifications", []), "certifications"),
            ("Achievements", payload.get("achievements", []), "achievements"),
        )
        for heading, value, kind in sections:
            if not value:
                continue
            heading_paragraph = document.add_heading(heading, level=1)
            for run in heading_paragraph.runs:
                run.font.name = FONT_MAP.get(config["font_name"], "Arial")
                run.font.size = Pt(config["heading_size"])
                run.font.color.rgb = accent
            if kind == "text":
                document.add_paragraph(str(value))
            else:
                for item in value:
                    if kind == "experience":
                        title = f"{item.get('job_title', '')} — {item.get('employer', '')}"
                        body = item.get("description", "")
                    elif kind == "education":
                        title = f"{item.get('qualification', '')} — {item.get('institution', '')}"
                        body = item.get("field_of_study", "")
                    elif kind == "skills":
                        title, body = item.get("name", ""), item.get("proficiency", "")
                    elif kind == "projects":
                        title = f"{item.get('name', '')} — {item.get('role', '')}"
                        body = item.get("description", "")
                    elif kind == "certifications":
                        title = f"{item.get('name', '')} — {item.get('issuer', '')}"
                        body = item.get("credential_id", "")
                    else:
                        title, body = item.get("title", ""), item.get("description", "")
                    paragraph = document.add_paragraph()
                    if title:
                        run = paragraph.add_run(str(title))
                        run.bold = True
                    if body:
                        paragraph.add_run(f"\n{body}")

        stream = BytesIO()
        document.save(stream)
        stream.seek(0)
        artifact = DocumentArtifact(
            cv_version=version,
            artifact_type=DocumentArtifact.DOCX,
            mime_type=MIME_TYPE,
            template_slug=payload["template"]["slug"],
            template_config=payload["template"].get("config", {}),
        )
        artifact.file.save(f"{version.cv_id}-v{version.version_number}.docx", ContentFile(stream.read()), save=True)
        return artifact


def generate_docx(cv_version):
    return DOCXGenerator().generate(cv_version)
