from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from cv.models import CareerProfile
from cv.models_import import CVImport, ImportedField
from cv.services.importers.docx import extract_text_from_docx
from cv.services.importers.parser import parse_career_facts
from cv.services.importers.pdf import extract_text_from_pdf

MAX_IMPORT_BYTES = 10 * 1024 * 1024
ADAPTERS = {"pdf": extract_text_from_pdf, "docx": extract_text_from_docx}
IMPORT_READ_ERROR = "Could not read the uploaded CV. Please make sure it is a valid PDF or DOCX file."


def _source_type(uploaded_file):
    name = (getattr(uploaded_file, "name", "") or "").lower()
    extension = name.rsplit(".", 1)[-1] if "." in name else ""
    if extension not in ADAPTERS:
        raise ValueError("Only PDF and DOCX CV files are supported.")
    if getattr(uploaded_file, "size", 0) > MAX_IMPORT_BYTES:
        raise ValueError("CV file exceeds the 10 MB import limit.")
    uploaded_file.seek(0)
    header = uploaded_file.read(4)
    uploaded_file.seek(0)
    if extension == "pdf" and header != b"%PDF":
        raise ValueError("The uploaded PDF file is invalid.")
    if extension == "docx" and header[:2] != b"PK":
        raise ValueError("The uploaded DOCX file is invalid.")
    return extension


@transaction.atomic
def import_cv_source(user, uploaded_file):
    source_type = _source_type(uploaded_file)
    profile, _ = CareerProfile.objects.get_or_create(user=user)
    try:
        text = ADAPTERS[source_type](uploaded_file)
    except Exception as exc:
        raise ValueError(IMPORT_READ_ERROR) from exc
    parsed = parse_career_facts(text)
    if not text.strip():
        raise ValueError("The uploaded CV contains no extractable text.")

    imported = CVImport.objects.create(
        owner=user,
        profile=profile,
        original_filename=(getattr(uploaded_file, "name", "cv") or "cv")[:255],
        source_type=source_type,
        extracted_text=text,
        parsed_data=parsed,
        status=CVImport.STATUS_REVIEW,
    )
    for field in parsed.get("fields", []):
        ImportedField.objects.create(
            cv_import=imported,
            section=field["section"],
            field_name=field["field_name"],
            value=field["value"],
            confirmed=False,
        )
    uploaded_file.seek(0)
    imported.source_file.save(imported.original_filename, ContentFile(uploaded_file.read()), save=True)
    return imported


def confirm_import_field(import_field_id, user, value):
    field = ImportedField.objects.select_related("cv_import").filter(
        pk=import_field_id,
        cv_import__owner=user,
    ).first()
    if field is None:
        raise ImportedField.DoesNotExist
    field.value = str(value).strip()
    field.confirmed = True
    field.confirmed_by = user
    field.confirmed_at = timezone.now()
    field.save(update_fields=["value", "confirmed", "confirmed_by", "confirmed_at", "updated_at"])
    if not field.cv_import.fields.filter(confirmed=False).exists():
        field.cv_import.status = CVImport.STATUS_CONFIRMED
        field.cv_import.save(update_fields=["status", "updated_at"])
    return field
