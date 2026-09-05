from io import BytesIO

from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from cv.models_document import DocumentArtifact
from cv.services.documents.base import DocumentGenerator


class PDFGenerator(DocumentGenerator):
    def generate(self, version):
        payload = version.snapshot
        stream = BytesIO()
        pdf = canvas.Canvas(stream, pagesize=A4)
        width, height = A4
        x = 48
        y = height - 48

        def line(text, size=10, leading=14):
            nonlocal y
            if y < 55:
                pdf.showPage()
                y = height - 48
            pdf.setFont("Helvetica", size)
            pdf.drawString(x, y, str(text)[:110])
            y -= leading

        contact = payload.get("contact", {})
        line(f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(), 18, 24)
        line(payload.get("professional_title", ""), 12, 18)
        line(contact.get("email", ""), 9, 14)
        if contact.get("phone"):
            line(contact["phone"], 9, 14)
        if contact.get("location"):
            line(contact["location"], 9, 18)

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
            line(heading, 11, 17)
            if kind is None:
                for part in str(value).splitlines() or [str(value)]:
                    line(part, 9, 13)
            elif kind == "experience":
                for item in value:
                    line(f"{item.get('job_title', '')} — {item.get('employer', '')}", 10, 14)
                    if item.get("location"):
                        line(item["location"], 9, 12)
                    line(item.get("description", ""), 9, 13)
            elif kind == "education":
                for item in value:
                    line(f"{item.get('qualification', '')} — {item.get('institution', '')}", 10, 14)
                    line(item.get("field_of_study", ""), 9, 13)
            elif kind == "skill":
                line(", ".join(str(item.get("name", "")) for item in value if item.get("name")), 9, 14)
            elif kind == "project":
                for item in value:
                    line(f"{item.get('name', '')} — {item.get('role', '')}", 10, 14)
                    line(item.get("description", ""), 9, 13)
            elif kind == "certification":
                for item in value:
                    line(f"{item.get('name', '')} — {item.get('issuer', '')}", 9, 13)
            elif kind == "achievement":
                for item in value:
                    line(item.get("title", ""), 9, 13)
                    line(item.get("description", ""), 9, 13)

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
