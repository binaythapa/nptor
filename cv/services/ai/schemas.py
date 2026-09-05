CAREER_FACT_SCHEMA = {
    "type": "object",
    "properties": {
        "section": {"type": "string"},
        "field_name": {"type": "string"},
        "proposed_value": {},
        "confirmed": {"type": "boolean"},
        "evidence": {"type": "string"},
    },
    "required": ["section", "field_name", "proposed_value", "confirmed", "evidence"],
    "additionalProperties": False,
}

CV_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "gaps": {"type": "array", "items": {"type": "string"}},
        "suggestions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["score", "strengths", "gaps", "suggestions"],
    "additionalProperties": False,
}

JOB_MATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "match_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "matching_skills": {"type": "array", "items": {"type": "string"}},
        "missing_skills": {"type": "array", "items": {"type": "string"}},
        "recommendations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["match_score", "matching_skills", "missing_skills", "recommendations"],
    "additionalProperties": False,
}

INTERVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "facts": {"type": "array", "items": CAREER_FACT_SCHEMA},
        "next_question": {"type": "string"},
    },
    "required": ["reply", "facts", "next_question"],
    "additionalProperties": False,
}
