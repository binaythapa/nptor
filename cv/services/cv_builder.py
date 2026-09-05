from copy import deepcopy

from django.db import transaction

from cv.models import (
    CareerAchievement,
    CareerCertification,
    CareerEducation,
    CareerExperience,
    CareerProject,
    CareerSkill,
)
from cv.models_cv import CV
from cv.models_version import CVVersion
from cv.services.profile import account_contact_defaults, get_or_create_career_profile


SECTION_MODELS = {
    "experiences": CareerExperience,
    "educations": CareerEducation,
    "projects": CareerProject,
    "skills": CareerSkill,
    "achievements": CareerAchievement,
    "certifications": CareerCertification,
}


def _json_value(value):
    return value.isoformat() if hasattr(value, "isoformat") and value is not None else value


def _serialize(instance, fields):
    return {field: _json_value(getattr(instance, field)) for field in fields}


def _selected_records(cv, section, queryset):
    selected = cv.selected_sections.get(section)
    if not selected:
        return list(queryset)
    ids = {int(value) for value in selected}
    return [item for item in queryset if item.id in ids]


def create_cv(user, title, template):
    """Create a standalone CV and its reusable master career profile."""
    profile = get_or_create_career_profile(user)
    return CV.objects.create(owner=user, profile=profile, template=template, title=title)


def build_cv_payload(cv):
    """Return a JSON-safe rendering payload from the master profile plus CV overrides."""
    if not cv.profile_id or cv.profile.user_id != cv.owner_id:
        raise ValueError("CV profile must belong to the CV owner")

    user = cv.owner
    profile = cv.profile
    overrides = deepcopy(cv.overrides or {})
    contact = account_contact_defaults(user)
    contact.update(overrides.get("contact", {}))

    payload = {
        "title": cv.title,
        "status": cv.status,
        "template": {
            "slug": cv.template.slug,
            "name": cv.template.name,
            "config": deepcopy(cv.template.config or {}),
        },
        "contact": contact,
        "professional_title": overrides.get("professional_title", profile.professional_title),
        "summary": overrides.get("summary", profile.summary),
        "linkedin_url": overrides.get("linkedin_url", profile.linkedin_url),
        "portfolio_url": overrides.get("portfolio_url", profile.portfolio_url),
    }

    payload["experiences"] = [
        _serialize(item, ["id", "job_title", "employer", "location", "start_date", "end_date", "is_current", "description"])
        for item in _selected_records(cv, "experiences", profile.experiences.all())
    ]
    payload["educations"] = [
        _serialize(item, ["id", "institution", "qualification", "field_of_study", "location", "start_date", "end_date", "description"])
        for item in _selected_records(cv, "educations", profile.educations.all())
    ]
    payload["projects"] = [
        _serialize(item, ["id", "name", "role", "url", "description", "technologies"])
        for item in _selected_records(cv, "projects", profile.projects.all())
    ]
    payload["skills"] = [
        _serialize(item, ["id", "name", "category", "proficiency"])
        for item in _selected_records(cv, "skills", profile.skills.all())
    ]
    payload["achievements"] = [
        _serialize(item, ["id", "title", "description", "achieved_on"])
        for item in _selected_records(cv, "achievements", profile.achievements.all())
    ]
    payload["certifications"] = [
        _serialize(item, ["id", "name", "issuer", "credential_id", "credential_url", "issued_on", "expires_on"])
        for item in _selected_records(cv, "certifications", profile.certifications.all())
    ]

    return payload


@transaction.atomic
def create_cv_version(cv):
    """Persist a point-in-time snapshot of the current CV payload."""
    last = CVVersion.objects.select_for_update().filter(cv=cv).order_by("-version_number").first()
    next_number = (last.version_number + 1) if last else 1
    return CVVersion.objects.create(
        cv=cv,
        version_number=next_number,
        snapshot=build_cv_payload(cv),
    )


def duplicate_cv(cv, title=None):
    """Create an independent editable copy of a CV."""
    if cv.owner_id != cv.profile.user_id:
        raise ValueError("CV profile must belong to the CV owner")
    return CV.objects.create(
        owner=cv.owner,
        profile=cv.profile,
        template=cv.template,
        title=title or f"{cv.title} Copy",
        status=CV.STATUS_DRAFT,
        selected_sections=deepcopy(cv.selected_sections or {}),
        overrides=deepcopy(cv.overrides or {}),
    )
