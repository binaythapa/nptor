from datetime import date

from cv.models import (
    CareerAchievement,
    CareerCertification,
    CareerEducation,
    CareerExperience,
    CareerProject,
    CareerSkill,
)
from cv.services.profile import get_or_create_career_profile


SECTION_CONFIG = {
    "experience": {
        "model": CareerExperience,
        "identity": ("job_title", "employer"),
        "fields": {"job_title", "employer", "location", "start_date", "end_date", "is_current", "description"},
    },
    "education": {
        "model": CareerEducation,
        "identity": ("institution", "qualification"),
        "fields": {"institution", "qualification", "field_of_study", "location", "start_date", "end_date", "description"},
    },
    "project": {
        "model": CareerProject,
        "identity": ("name",),
        "fields": {"name", "role", "url", "description", "technologies"},
    },
    "skill": {
        "model": CareerSkill,
        "identity": ("name",),
        "fields": {"name", "category", "proficiency"},
    },
    "achievement": {
        "model": CareerAchievement,
        "identity": ("title",),
        "fields": {"title", "description", "achieved_on"},
    },
    "certification": {
        "model": CareerCertification,
        "identity": ("name", "issuer"),
        "fields": {"name", "issuer", "credential_id", "credential_url", "issued_on", "expires_on"},
    },
}

SECTION_ALIASES = {
    "experiences": "experience",
    "education": "education",
    "educations": "education",
    "projects": "project",
    "skills": "skill",
    "achievements": "achievement",
    "certifications": "certification",
}

DATE_FIELDS = {"start_date", "end_date", "achieved_on", "issued_on", "expires_on"}


def _normalize_section(section):
    return SECTION_ALIASES.get(str(section).strip().lower(), str(section).strip().lower())


def _normalize_value(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return value
    return str(value).strip()


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        return None


def _confirmed_values(conversation, section):
    values = {}
    for extraction in conversation.extractions.filter(section=section, confirmed=True).order_by("created_at", "id"):
        value = _normalize_value(extraction.proposed_value)
        if value != "":
            values[extraction.field_name] = value
    return values


def _materialize_section(profile, section, values):
    config = SECTION_CONFIG.get(section)
    if not config:
        return None

    identity = config["identity"]
    if any(not values.get(field) for field in identity):
        return None

    lookup = {field: values[field] for field in identity}
    model = config["model"]
    record, _created = model.objects.get_or_create(
        profile=profile,
        **lookup,
        defaults={"source": "ai_interview", "is_confirmed": True},
    )

    updates = []
    for field in config["fields"]:
        if field not in values or field in identity:
            continue
        value = _parse_date(values[field]) if field in DATE_FIELDS else values[field]
        if field == "is_current":
            value = str(values[field]).strip().lower() in {"1", "true", "yes", "current"}
        if getattr(record, field) != value:
            setattr(record, field, value)
            updates.append(field)

    if record.source != "ai_interview":
        record.source = "ai_interview"
        updates.append("source")
    if not record.is_confirmed:
        record.is_confirmed = True
        updates.append("is_confirmed")
    if updates:
        record.save(update_fields=[*dict.fromkeys(updates), "updated_at"])
    return record


def apply_confirmed_extraction(extraction):
    """Materialize one confirmed interview extraction into the owner's profile."""
    if not extraction.confirmed:
        return None
    conversation = extraction.conversation
    profile = get_or_create_career_profile(conversation.owner)
    section = _normalize_section(extraction.section)
    values = _confirmed_values(conversation, section)
    return _materialize_section(profile, section, values)
