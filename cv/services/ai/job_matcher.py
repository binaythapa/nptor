from cv.services.ai.provider import get_ai_provider
from cv.services.ai.schemas import JOB_MATCH_SCHEMA


MATCH_RULE = (
    "Compare the supplied CV with the supplied job description. Use only stated CV facts. "
    "Do not invent skills, qualifications, employers, dates, metrics, or experience."
)


def match_job(cv_payload, job_description, provider=None):
    provider = provider or get_ai_provider()
    prompt = (
        f"{MATCH_RULE}\nCV:\n{cv_payload}\n\nJOB DESCRIPTION:\n{job_description}"
    )
    result = provider.generate_structured(prompt, JOB_MATCH_SCHEMA, system_prompt=MATCH_RULE)
    return {**result, "source": "ai_suggestion", "confirmed": False}
