import re

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
IDENTITY_SENTENCE_RE = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z .'-]{1,79})\s+is\s+(?:an?|the)\s+(?P<title>[^,.;]{2,80})",
    re.IGNORECASE,
)
SECTION_NAMES = {
    "summary": "summary",
    "professional summary": "summary",
    "career summary": "summary",
    "profile": "summary",
    "objective": "summary",
    "career objective": "summary",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "employment": "experience",
    "employment history": "experience",
    "education": "education",
    "academic background": "education",
    "academic qualifications": "education",
    "skills": "skills",
    "technical skills": "skills",
    "core skills": "skills",
    "projects": "projects",
    "personal projects": "projects",
    "certifications": "certifications",
    "certificates": "certifications",
    "achievements": "achievements",
    "awards": "achievements",
}

SECTION_PATTERN = re.compile(
    r"(?<![A-Za-z])(?:"
    + "|".join(re.escape(name) for name in sorted(SECTION_NAMES, key=len, reverse=True))
    + r")(?:\s*[:\-]\s*|(?=\s{2,}|\n|$))",
    re.IGNORECASE,
)


def _add_field(fields, section, field_name, value):
    value = value.strip(" \t\n:|-•")
    if value:
        fields.append({
            "section": section,
            "field_name": field_name,
            "value": value,
            "confirmed": False,
        })


def _normalize_heading(value):
    return re.sub(r"\s+", " ", value.rstrip(":-").strip()).lower()


def _split_inline_sections(text):
    """Split section headings even when a DOCX extractor returns one long paragraph."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    matches = list(SECTION_PATTERN.finditer(normalized))
    if not matches:
        return [(None, normalized.strip())]

    parts = []
    prefix = normalized[:matches[0].start()].strip()
    if prefix:
        parts.append((None, prefix))

    for index, match in enumerate(matches):
        heading = match.group(0).strip(" :\n-")
        canonical = SECTION_NAMES.get(_normalize_heading(heading))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        value = normalized[start:end].strip()
        if canonical and value:
            parts.append((canonical, value))
    return parts


def _extract_identity(lines):
    if not lines:
        return None, None

    first = lines[0].strip()
    if EMAIL_RE.fullmatch(first):
        return None, None

    if "|" in first:
        pieces = [piece.strip() for piece in first.split("|") if piece.strip()]
        if pieces:
            name = pieces[0]
            title = pieces[1] if len(pieces) > 1 and not EMAIL_RE.search(pieces[1]) else None
            if len(name) <= 80 and re.match(r"^[A-Za-z][A-Za-z .'-]+$", name):
                return name, title

    first_normalized = _normalize_heading(first)
    if first_normalized not in SECTION_NAMES and len(first) <= 80:
        return first, None

    for line in lines:
        match = IDENTITY_SENTENCE_RE.match(line)
        if match:
            return match.group("name"), match.group("title")
    return None, None


def parse_career_facts(text):
    """Extract conservative, deterministic career facts without inventing information."""
    raw_text = text or ""
    lines = [line.strip() for line in raw_text.replace("\r", "\n").split("\n") if line.strip()]
    fields = []

    email_match = EMAIL_RE.search(raw_text)
    full_name, header_title = _extract_identity(lines)
    if full_name:
        _add_field(fields, "contact", "full_name", full_name)
    if email_match:
        _add_field(fields, "contact", "email", email_match.group(0))

    if header_title:
        _add_field(fields, "contact", "professional_title", header_title)
    elif full_name and len(lines) > 1:
        candidate = lines[1].strip()
        if candidate and not EMAIL_RE.search(candidate) and _normalize_heading(candidate) not in SECTION_NAMES:
            _add_field(fields, "contact", "professional_title", candidate)

    sections = _split_inline_sections(raw_text)
    has_structured_sections = any(section for section, _value in sections)

    if not has_structured_sections:
        identity_consumed = set(lines[:2]) if full_name else set()
        remainder = [line for line in lines if line not in identity_consumed and not EMAIL_RE.search(line)]
        if remainder:
            _add_field(fields, "summary", "text", "\n".join(remainder))
    else:
        for section, value in sections:
            if section is None:
                pre_lines = [line for line in value.splitlines() if line.strip()]
                if pre_lines:
                    consumed = set()
                    if full_name and pre_lines[0].strip() == full_name:
                        consumed.add(pre_lines[0].strip())
                    if header_title and header_title in pre_lines:
                        consumed.add(header_title)
                    elif full_name and len(pre_lines) > 1 and pre_lines[1].strip() != header_title:
                        consumed.add(pre_lines[1].strip())
                    remainder = [line for line in pre_lines if line.strip() not in consumed and not EMAIL_RE.search(line)]
                    if remainder:
                        _add_field(fields, "summary", "text", "\n".join(remainder))
                continue

            if section == "skills":
                for skill in re.split(r"[,|•;\n]", value):
                    _add_field(fields, "skills", "name", skill)
            else:
                _add_field(fields, section, "text", value)

    result = {"fields": fields}
    for field in fields:
        if field["field_name"] in {"full_name", "email", "professional_title"}:
            result[field["field_name"]] = field["value"]
    return result
