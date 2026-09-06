from cv.services.ai.provider import get_ai_provider


TRUTH_RULE = (
    "Use only facts present in the supplied CV data. Do not invent employers, dates, "
    "qualifications, certifications, achievements, metrics, or responsibilities."
)


def suggest_summary(cv_payload, provider=None):
    provider = provider or get_ai_provider()
    prompt = f"{TRUTH_RULE}\nWrite a concise professional CV summary from this data:\n{cv_payload}"
    text = provider.generate_text(prompt, system_prompt=TRUTH_RULE)
    return {"summary": text.strip(), "source": "ai_suggestion", "confirmed": False}


def rewrite_bullet(bullet, context, provider=None):
    provider = provider or get_ai_provider()
    prompt = (
        f"{TRUTH_RULE}\nRewrite this CV bullet to be concise, specific, and professional. "
        f"Do not add facts or metrics.\nBullet: {bullet}\nContext: {context}"
    )
    text = provider.generate_text(prompt, system_prompt=TRUTH_RULE)
    return {"bullet": text.strip(), "source": "ai_suggestion", "confirmed": False}


def suggest_skills(cv_payload, target_job_title, provider=None):
    provider = provider or get_ai_provider()
    prompt = (
        f"{TRUTH_RULE}\nSuggest resume skills for the target role. Only use skills present in the supplied CV data "
        f"or clearly supported by existing career records. Return one skill per line and no commentary. "
        f"Target role: {target_job_title}\nCV data: {cv_payload}"
    )
    text = provider.generate_text(prompt, system_prompt=TRUTH_RULE)
    skills = []
    for line in text.splitlines():
        value = line.strip().lstrip("-*•").strip()
        if value and value not in skills:
            skills.append(value)
    return {"skills": skills[:12], "source": "ai_suggestion", "confirmed": False}
