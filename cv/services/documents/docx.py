from io import BytesIO

from django.core.files.base import ContentFile
from docx import Document

from cv.models_document import DocumentArtifact
from cv.services.documents.base import DocumentGenerator


MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class DOCXGenerator(DocumentGenerator):
    def generate(self, version):
        payload = version.snapshot
        document = Document()
        contact = payload.get("contact", {})
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        if name:
            document.add_heading(name, level=0)
        if payload.get("professional_title"):
            document.add_paragraph(payload["professional_title"])
        details = [contact.get("email"), contact.get("phone"), contact.get("location")]
        details = [str(value) for value in details if value]
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
            document.add_heading(heading, level=1)
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
                        paragraph.add_run(str(title)).bold = True
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
