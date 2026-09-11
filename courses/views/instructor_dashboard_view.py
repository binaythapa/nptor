from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import render

from courses.models import Course
from courses.services.permissions import can_view_instructor_dashboard


@login_required
def instructor_dashboard(request):
    """Render the instructor dashboard without duplicating courses across contexts."""
    organization = getattr(request, "organization", None)

    if organization and not can_view_instructor_dashboard(
        request.user,
        organization,
    ):
        return HttpResponseForbidden(
            "You are not allowed to view organization instructor data."
        )

    base_queryset = (
        Course.objects
        .select_related("created_by", "organization", "reviewed_by")
        .annotate(
            total_lessons=Count("sections__lessons", distinct=True),
            total_enrollments=Count("enrollments", distinct=True),
        )
        .order_by("-created_at")
    )

    if organization:
        organization_courses = base_queryset.filter(
            organization=organization,
            owner_type=Course.OWNER_ORGANIZATION,
        )
        admin_courses = base_queryset.none()
        my_courses = base_queryset.filter(
            created_by=request.user,
            owner_type=Course.OWNER_PLATFORM,
            organization__isnull=True,
        )
    elif request.user.is_superuser:
        organization_courses = base_queryset.none()
        admin_courses = base_queryset.filter(
            owner_type=Course.OWNER_PLATFORM,
            organization__isnull=True,
        )
        my_courses = base_queryset.none()
    else:
        organization_courses = base_queryset.none()
        admin_courses = base_queryset.none()
        my_courses = base_queryset.filter(
            created_by=request.user,
            owner_type=Course.OWNER_PLATFORM,
            organization__isnull=True,
        )

    pending_review_count = 0
    if request.user.is_superuser:
        pending_review_count = Course.objects.filter(
            approval_status=Course.APPROVAL_PENDING,
        ).count()

    return render(
        request,
        "courses/instructor/dashboard.html",
        {
            "organization_courses": organization_courses,
            "admin_courses": admin_courses,
            "my_courses": my_courses,
            "pending_review_count": pending_review_count,
        },
    )
