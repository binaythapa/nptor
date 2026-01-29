import uuid
from courses.models import CourseCertificate


def issue_certificate_if_eligible(user, course, progress):
    """
    Issues certificate if:
    - progress == 100
    - certificate does not already exist
    """

    if progress < 100:
        return None

    certificate, created = CourseCertificate.objects.get_or_create(
        user=user,
        course=course,
        defaults={
            "certificate_id": f"CERT-{uuid.uuid4().hex[:12].upper()}"
        }
    )

    return certificate
