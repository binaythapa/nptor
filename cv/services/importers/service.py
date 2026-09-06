from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from cv.models import CareerProfile, CareerSkill
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
    return field


def _apply_imported_fields(imported, user):
    profile = imported.profile
    contact_name = None
    contact_email = None

    for field in imported.fields.all():
        value = field.value.strip()
        if not value:
            continue
        if field.section == "contact" and field.field_name == "full_name":
            contact_name = value
        elif field.section == "contact" and field.field_name == "email":
            contact_email = value
        elif field.section == "contact" and field.field_name == "professional_title":
            profile.professional_title = value
        elif field.section == "summary" and field.field_name == "text":
            profile.summary = value
        elif field.section == "skills" and field.field_name == "name":
            CareerSkill.objects.get_or_create(profile=profile, name=value)

    profile.save(update_fields=["professional_title", "summary", "updated_at"])

    user_update_fields = []
    if contact_name:
        parts = contact_name.split()
        user.first_name = parts[0]
        user.last_name = " ".join(parts[1:])
        user_update_fields.extend(["first_name", "last_name"])
    if contact_email:
        user.email = contact_email
        user_update_fields.append("email")
    if user_update_fields:
        user.save(update_fields=list(dict.fromkeys(user_update_fields)))


@transaction.atomic
def confirm_import(imported_id, user, values):
    imported = CVImport.objects.select_related("profile").prefetch_related("fields").filter(
        pk=imported_id,
        owner=user,
    ).first()
    if imported is None:
        raise CVImport.DoesNotExist

    fields = list(imported.fields.all())
    for field in fields:
        if field.pk in values:
            confirm_import_field(field.pk, user, values[field.pk])

    imported.refresh_from_db()
    if imported.fields.filter(confirmed=False).exists():
        raise ValueError("Please review and confirm every imported field before adding it to your CV.")

    _apply_imported_fields(imported, user)
    imported.status = CVImport.STATUS_CONFIRMED
    imported.save(update_fields=["status", "updated_at"])
    return imported
