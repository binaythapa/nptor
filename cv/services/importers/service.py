from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from cv.models import (
    CareerAchievement,
    CareerCertification,
    CareerEducation,
    CareerExperience,
    CareerProject,
    CareerProfile,
    CareerSkill,
)
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


def _lines(value):
    return [line.strip(" \t•-*\u2022") for line in str(value).splitlines() if line.strip(" \t•-*\u2022")]


def _parts(value):
    return [part.strip() for part in str(value).split("|") if part.strip()]


def _create_experience(profile, value):
    lines = _lines(value)
    if not lines:
        return
    parts = _parts(lines[0])
    if len(parts) >= 2:
        job_title, employer = parts[0], parts[1]
        description = " | ".join(parts[2:])
        if len(lines) > 1:
            description = "\n".join(filter(None, [description, *lines[1:]]))
    else:
        job_title = lines[0]
        employer = lines[1] if len(lines) > 1 else "Imported employer"
        description = "\n".join(lines[2:])
    CareerExperience.objects.create(
        profile=profile,
        job_title=job_title[:255],
        employer=employer[:255],
        description=description,
        source="import",
        is_confirmed=True,
    )


def _create_education(profile, value):
    lines = _lines(value)
    if not lines:
        return
    parts = _parts(lines[0])
    institution_markers = ("university", "college", "institute", "school", "academy")
    institution_index = next(
        (index for index, part in enumerate(parts) if any(marker in part.lower() for marker in institution_markers)),
        None,
    )
    if institution_index is not None:
        institution = parts[institution_index]
        qualification = parts[0] if institution_index else (parts[1] if len(parts) > 1 else parts[0])
        field_of_study = " | ".join(parts[1:institution_index]) if institution_index > 1 else ""
    elif len(parts) >= 2:
        qualification, institution = parts[0], parts[-1]
        field_of_study = " | ".join(parts[1:-1])
    else:
        qualification = lines[0]
        institution = lines[1] if len(lines) > 1 else "Imported institution"
        field_of_study = ""
    description = "\n".join(lines[1:]) if len(lines) > 1 and institution_index is None else ""
    CareerEducation.objects.create(
        profile=profile,
        institution=institution[:255],
        qualification=qualification[:255],
        field_of_study=field_of_study[:255],
        description=description,
        source="import",
        is_confirmed=True,
    )


def _create_project(profile, value):
    lines = _lines(value)
    if not lines:
        return
    parts = _parts(lines[0])
    name = parts[0]
    description = " | ".join(parts[1:])
    if len(lines) > 1:
        description = "\n".join(filter(None, [description, *lines[1:]]))
    CareerProject.objects.create(
        profile=profile,
        name=name[:255],
        description=description,
        technologies="",
        source="import",
        is_confirmed=True,
    )


def _create_certification(profile, value):
    lines = _lines(value)
    if not lines:
        return
    parts = _parts(lines[0])
    name = parts[0]
    issuer = parts[1] if len(parts) > 1 else ""
    CareerCertification.objects.create(
        profile=profile,
        name=name[:255],
        issuer=issuer[:255],
        source="import",
        is_confirmed=True,
    )


def _create_achievement(profile, value):
    lines = _lines(value)
    if not lines:
        return
    parts = _parts(lines[0])
    title = parts[0]
    description = " | ".join(parts[1:])
    if len(lines) > 1:
        description = "\n".join(filter(None, [description, *lines[1:]]))
    CareerAchievement.objects.create(
        profile=profile,
        title=title[:255],
        description=description,
        source="import",
        is_confirmed=True,
    )


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
            CareerSkill.objects.get_or_create(
                profile=profile,
                name=value,
                defaults={"source": "import", "is_confirmed": True},
            )
        elif field.section == "experience" and field.field_name == "text":
            _create_experience(profile, value)
        elif field.section == "education" and field.field_name == "text":
            _create_education(profile, value)
        elif field.section == "projects" and field.field_name == "text":
            _create_project(profile, value)
        elif field.section == "certifications" and field.field_name == "text":
            _create_certification(profile, value)
        elif field.section == "achievements" and field.field_name == "text":
            _create_achievement(profile, value)

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
