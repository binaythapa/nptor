import re

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
SECTION_NAMES = {
    "summary": "summary",
    "professional summary": "summary",
    "profile": "summary",
    "experience": "experience",
    "work experience": "experience",
    "employment": "experience",
    "education": "education",
    "skills": "skills",
    "technical skills": "skills",
    "projects": "projects",
    "certifications": "certifications",
    "achievements": "achievements",
}


def _add_field(fields, section, field_name, value):
    value = value.strip()
    if value:
        fields.append({
            "section": section,
            "field_name": field_name,
            "value": value,
            "confirmed": False,
        })


def parse_career_facts(text):
    """Extract conservative, deterministic facts without inventing information."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    fields = []
    email_match = EMAIL_RE.search(text)

    if lines and not EMAIL_RE.fullmatch(lines[0]) and len(lines[0]) <= 80:
        _add_field(fields, "contact", "full_name", lines[0])

    if email_match:
        _add_field(fields, "contact", "email", email_match.group(0))

    title_candidates = [line for line in lines[1:4] if not EMAIL_RE.search(line)]
    if title_candidates:
        _add_field(fields, "contact", "professional_title", title_candidates[0])

    for index, line in enumerate(lines):
        normalized = line.rstrip(":").strip().lower()
        section = SECTION_NAMES.get(normalized)
        if not section:
            continue
        following = []
        for candidate in lines[index + 1:]:
            if candidate.rstrip(":").strip().lower() in SECTION_NAMES:
                break
            following.append(candidate)
        if section in {"summary", "experience", "education", "projects", "certifications", "achievements"} and following:
            _add_field(fields, section, "text", "\n".join(following))
        elif section == "skills" and following:
            raw = "\n".join(following)
            for skill in re.split(r"[,|•]", raw):
                _add_field(fields, "skills", "name", skill)

    result = {"fields": fields}
    for field in fields:
        if field["field_name"] in {"full_name", "email"}:
            result[field["field_name"]] = field["value"]
    return result
