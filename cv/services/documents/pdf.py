from io import BytesIO

from django.core.files.base import ContentFile
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from cv.models_document import DocumentArtifact
from cv.services.documents.base import DocumentGenerator
from cv.services.documents.renderer import get_render_config


class PDFGenerator(DocumentGenerator):
    def generate(self, version):
        payload = version.snapshot
        config = get_render_config(payload.get("template", {}))
        stream = BytesIO()
        pdf = canvas.Canvas(stream, pagesize=A4)
        width, height = A4
        margin = config["margin"]
        x = margin
        y = height - margin
        body_color = colors.HexColor("#374151")
        accent_color = colors.HexColor(config["accent_color"])

        def line(text, size=None, leading=None, bold=False, color=None):
            nonlocal y
            leading = leading or max(12, (size or config["font_size"]) + 3)
            if y < margin:
                pdf.showPage()
                y = height - margin
            font = config["font_name"]
            if bold and font in {"Helvetica", "Times-Roman"}:
                font = "Helvetica-Bold" if font == "Helvetica" else "Times-Bold"
            pdf.setFont(font, size or config["font_size"])
            pdf.setFillColor(color or body_color)
            pdf.drawString(x, y, str(text)[:110])
            y -= leading

        contact = payload.get("contact", {})
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        if name:
            line(name, config["heading_size"] + 7, config["heading_size"] + 11, bold=True, color=accent_color)
        if payload.get("professional_title"):
            line(payload["professional_title"], config["font_size"] + 2, config["font_size"] + 7, color=accent_color)
        details = [contact.get("email"), contact.get("phone"), contact.get("location")]
        details = [str(value) for value in details if value]
        if payload.get("linkedin_url"):
            details.append(payload["linkedin_url"])
        if payload.get("portfolio_url"):
            details.append(payload["portfolio_url"])
        if details:
            line(" | ".join(details), max(8, config["font_size"] - 1), config["font_size"] + 3)

        sections = (
            ("SUMMARY", payload.get("summary"), None),
            ("EXPERIENCE", payload.get("experiences", []), "experience"),
            ("EDUCATION", payload.get("educations", []), "education"),
            ("SKILLS", payload.get("skills", []), "skill"),
            ("PROJECTS", payload.get("projects", []), "project"),
            ("CERTIFICATIONS", payload.get("certifications", []), "certification"),
            ("ACHIEVEMENTS", payload.get("achievements", []), "achievement"),
        )
        for heading, value, kind in sections:
            if not value:
                continue
            line(heading, config["heading_size"], config["heading_size"] + 7, bold=True, color=accent_color)
            if kind is None:
                for part in str(value).splitlines() or [str(value)]:
                    line(part, max(8, config["font_size"] - 1), config["font_size"] + 3)
            elif kind == "experience":
                for item in value:
                    line(f"{item.get('job_title', '')} — {item.get('employer', '')}", config["font_size"], config["font_size"] + 4, bold=True)
                    if item.get("location"):
                        line(item["location"], max(8, config["font_size"] - 1), config["font_size"] + 2)
                    if item.get("description"):
                        for part in str(item["description"]).splitlines():
                            line(part, max(8, config["font_size"] - 1), config["font_size"] + 3)
            elif kind == "education":
                for item in value:
                    line(f"{item.get('qualification', '')} — {item.get('institution', '')}", config["font_size"], config["font_size"] + 4, bold=True)
                    if item.get("field_of_study"):
                        line(item["field_of_study"], max(8, config["font_size"] - 1), config["font_size"] + 3)
            elif kind == "skill":
                line(", ".join(str(item.get("name", "")) for item in value if item.get("name")), max(8, config["font_size"] - 1), config["font_size"] + 3)
            elif kind == "project":
                for item in value:
                    line(f"{item.get('name', '')} — {item.get('role', '')}", config["font_size"], config["font_size"] + 4, bold=True)
                    if item.get("description"):
                        line(item["description"], max(8, config["font_size"] - 1), config["font_size"] + 3)
            elif kind == "certification":
                for item in value:
                    line(f"{item.get('name', '')} — {item.get('issuer', '')}", max(8, config["font_size"] - 1), config["font_size"] + 3)
            elif kind == "achievement":
                for item in value:
                    line(item.get("title", ""), max(8, config["font_size"] - 1), config["font_size"] + 3, bold=True)
                    if item.get("description"):
                        line(item["description"], max(8, config["font_size"] - 1), config["font_size"] + 3)
            y -= config["section_gap"]

        pdf.save()
        stream.seek(0)
        artifact = DocumentArtifact(
            cv_version=version,
            artifact_type=DocumentArtifact.PDF,
            mime_type="application/pdf",
            template_slug=payload["template"]["slug"],
            template_config=payload["template"].get("config", {}),
        )
        artifact.file.save(f"{version.cv_id}-v{version.version_number}.pdf", ContentFile(stream.read()), save=True)
        return artifact


def generate_pdf(cv_version):
    return PDFGenerator().generate(cv_version)
