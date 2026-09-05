from django.shortcuts import get_object_or_404, render

from courses.models import CourseCertificate


def certificate_verify(request, certificate_id):
    """Publicly verify an NPTOR course-completion certificate."""
    certificate = get_object_or_404(
        CourseCertificate.objects.select_related("user", "course"),
        certificate_id=certificate_id,
    )

    sections = (
        certificate.course.sections
        .prefetch_related("lessons")
        .order_by("order")
    )

    return render(
        request,
        "courses/student/certificate_verification.html",
        {
            "certificate": certificate,
            "sections": sections,
        },
    )
