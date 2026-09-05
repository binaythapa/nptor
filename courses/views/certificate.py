from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from courses.models import CourseCertificate
from courses.services.certificate_pdf import generate_certificate_pdf


def _certificate_queryset():
    return CourseCertificate.objects.select_related("user", "course")


def certificate_verify(request, certificate_id):
    """Publicly verify an NPTOR course-completion certificate."""
    certificate = get_object_or_404(
        _certificate_queryset(),
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


def certificate_download(request, certificate_id):
    """Download a verified certificate using its public certificate ID."""
    certificate = get_object_or_404(
        _certificate_queryset(),
        certificate_id=certificate_id,
    )

    pdf = generate_certificate_pdf(
        certificate.user,
        certificate.course,
        certificate,
    )

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="NPTOR-{certificate.certificate_id}.pdf"'
    )
    return response
