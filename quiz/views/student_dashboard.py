from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import render
from django.utils import timezone

from courses.models import Course, CourseEnrollment
from courses.models.subscription import CourseSubscription
from organizations.models.access import ResourceAccess
from quiz.models import UserExam


@login_required
def student_dashboard(request):
    """Render the student overview without treating public access as ownership."""
    user = request.user

    submitted_attempts = list(
        UserExam.objects
        .filter(user=user, submitted_at__isnull=False)
        .select_related("exam")
        .order_by("-submitted_at")[:5]
    )
    active_attempt = (
        UserExam.objects
        .filter(user=user, submitted_at__isnull=True)
        .select_related("exam")
        .order_by("-started_at")
        .first()
    )

    completed_attempts = UserExam.objects.filter(
        user=user,
        submitted_at__isnull=False,
    )
    total_attempts = completed_attempts.count()
    passed_attempts = completed_attempts.filter(passed=True).count()
    average_score = completed_attempts.aggregate(value=Avg("score"))["value"]

    # Dashboard statistics must represent explicit ownership only. Public
    # availability is intentionally excluded. Organization assignments,
    # administrator grants, individual purchases, course enrollments, and
    # course subscriptions are all included.
    now = timezone.now()
    owned_course_ids = set(
        CourseEnrollment.objects.filter(
            user=user,
            is_active=True,
        ).values_list("course_id", flat=True)
    )
    owned_course_ids.update(
        CourseSubscription.objects.filter(
            user=user,
            is_active=True,
        ).values_list("course_id", flat=True)
    )
    owned_course_ids.update(
        ResourceAccess.objects.filter(
            user=user,
            resource_type=ResourceAccess.RESOURCE_COURSE,
            course__isnull=False,
            is_active=True,
            revoked_at__isnull=True,
            expires_at__isnull=True,
        ).exclude(source=ResourceAccess.SOURCE_PUBLIC).values_list("course_id", flat=True)
    )
    owned_course_ids.update(
        ResourceAccess.objects.filter(
            user=user,
            resource_type=ResourceAccess.RESOURCE_COURSE,
            course__isnull=False,
            is_active=True,
            revoked_at__isnull=True,
            expires_at__gt=now,
        ).exclude(source=ResourceAccess.SOURCE_PUBLIC).values_list("course_id", flat=True)
    )

    learning_courses = Course.objects.filter(
        id__in=owned_course_ids,
        is_published=True,
    ).count()

    recent_results = [
        {
            "attempt": attempt,
            "status": "Passed" if attempt.passed else "Failed",
        }
        for attempt in submitted_attempts
    ]

    return render(
        request,
        "quiz/student/student_dashboard_overview.html",
        {
            "active_attempt": active_attempt,
            "total_attempts": total_attempts,
            "passed_attempts": passed_attempts,
            "average_score": round(float(average_score), 1) if average_score is not None else 0,
            "learning_courses": learning_courses,
            "recent_results": recent_results,
        },
    )
