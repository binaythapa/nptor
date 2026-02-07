from django.shortcuts import render, get_object_or_404

from organizations.models.organization import Organization
from courses.models import Course


def org_public_page(request, slug):
    """
    Public organization landing page.
    Accessible without login.

    Example:
    /org/<slug>/
    """

    # ===============================
    # ORGANIZATION
    # ===============================
    organization = get_object_or_404(
        Organization,
        slug=slug,
        is_active=True,
    )

    # ===============================
    # PUBLIC COURSES OF ORG
    # ===============================
    courses = Course.objects.filter(
        organization=organization,
        is_public=True,
        is_published=True,
    )

    return render(
        request,
        "organizations/public/organization.html",
        {
            "organization": organization,
            "courses": courses,
        }
    )
