from cv.models import ATSAnalysis
from cv.services.ai.provider import get_ai_provider
from cv.services.ai.schemas import CV_REVIEW_SCHEMA


REVIEW_RULE = (
    "Review only the facts present in the CV. Never invent qualifications, employers, dates, "
    "metrics, certifications, or achievements. Recommendations must be suggestions only."
)


def review_cv(cv_version, provider=None):
    owner_id = cv_version.cv.owner_id
    provider = provider or get_ai_provider()
    result = provider.generate_structured(
        f"Review this CV for ATS readiness and professional clarity:\n{cv_version.snapshot}",
        CV_REVIEW_SCHEMA,
        system_prompt=REVIEW_RULE,
    )
    score = max(0, min(100, int(result.get("score", 0))))
    return ATSAnalysis.objects.create(
        owner_id=owner_id,
        cv_version=cv_version,
        result=result,
        score=score,
        provider=getattr(provider, "name", ""),
        model=getattr(provider, "model", ""),
    )
