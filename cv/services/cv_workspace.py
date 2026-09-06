from cv.forms import CAREER_RECORD_FORMS
from cv.models_cv import CV
from cv.models_template import CVTemplate
from cv.services.cv_builder import build_cv_payload


SECTION_MODELS = {
    "experiences": CAREER_RECORD_FORMS["experience"][0],
    "educations": CAREER_RECORD_FORMS["education"][0],
    "skills": CAREER_RECORD_FORMS["skill"][0],
    "certifications": CAREER_RECORD_FORMS["certification"][0],
    "projects": CAREER_RECORD_FORMS["project"][0],
    "achievements": CAREER_RECORD_FORMS["achievement"][0],
}


def normalize_target_job(value):
    value = value if isinstance(value, dict) else {}
    return {
        "title": str(value.get("title", "")).strip()[:255],
        "company": str(value.get("company", "")).strip()[:255],
        "description": str(value.get("description", "")).strip()[:12000],
    }


def normalize_selected_sections(value, profile):
    if not isinstance(value, dict):
        return None

    normalized = {}
    for section, model in SECTION_MODELS.items():
        values = value.get(section)
        if not isinstance(values, list):
            continue
        valid_ids = set(model.objects.filter(profile=profile).values_list("id", flat=True))
        normalized[section] = [int(item) for item in values if str(item).isdigit() and int(item) in valid_ids]
    return normalized


def normalize_experience_bullets(value, profile):
    if not isinstance(value, dict):
        return None
    valid_ids = set(profile.careerexperience_records.values_list("id", flat=True))
    return {
        str(record_id): str(text).strip()[:5000]
        for record_id, text in value.items()
        if str(record_id).isdigit() and int(record_id) in valid_ids and str(text).strip()
    }


def normalize_cv_skills(value):
    if not isinstance(value, list):
        return None
    result = []
    seen = set()
    for item in value:
        skill = str(item).strip()[:100]
        key = skill.lower()
        if skill and key not in seen:
            result.append(skill)
            seen.add(key)
    return result[:30]


def save_builder_state(cv, data):
    if not isinstance(data, dict):
        raise ValueError("Builder state must be an object.")

    if "title" in data:
        title = str(data.get("title", "")).strip()
        if not title:
            raise ValueError("CV title is required.")
        cv.title = title[:255]

    if "status" in data:
        status = str(data.get("status", "")).strip()
        valid_statuses = {value for value, _label in CV.STATUS_CHOICES}
        if status not in valid_statuses:
            raise ValueError("Invalid CV status.")
        cv.status = status

    if "template_id" in data:
        template = CVTemplate.objects.filter(pk=data.get("template_id"), is_active=True).first()
        if template is None:
            raise ValueError("Selected CV template is not available.")
        cv.template = template

    overrides = dict(cv.overrides or {})
    for key in ("professional_title", "summary", "linkedin_url", "portfolio_url"):
        if key in data:
            overrides[key] = str(data.get(key) or "").strip()

    if "target_job" in data:
        overrides["target_job"] = normalize_target_job(data.get("target_job"))

    if "experience_bullets" in data:
        normalized = normalize_experience_bullets(data.get("experience_bullets"), cv.profile)
        if normalized is not None:
            overrides["experience_bullets"] = normalized

    if "cv_skills" in data:
        normalized = normalize_cv_skills(data.get("cv_skills"))
        if normalized is not None:
            overrides["cv_skills"] = normalized

    selected_sections = normalize_selected_sections(data.get("selected_sections"), cv.profile)
    if selected_sections is not None:
        cv.selected_sections = selected_sections

    cv.overrides = overrides
    cv.save(update_fields=["title", "status", "template", "overrides", "selected_sections", "updated_at"])
    return cv


def builder_ai_context(cv):
    payload = build_cv_payload(cv)
    return payload, normalize_target_job((cv.overrides or {}).get("target_job"))
