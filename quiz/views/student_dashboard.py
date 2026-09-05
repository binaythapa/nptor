from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import render

from courses.models import Course
from organizations.models.access import ResourceAccess
from quiz.models import UserExam


@login_required
def student_dashboard(request):
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

    total_attempts = UserExam.objects.filter(
        user=user,
        submitted_at__isnull=False,
    ).count()
    passed_attempts = UserExam.objects.filter(
        user=user,
        submitted_at__isnull=False,
        passed=True,
    ).count()
    average_score = UserExam.objects.filter(
        user=user,
        submitted_at__isnull=False,
    ).aggregate(value=Avg("score"))["value"]

    learning_courses = ResourceAccess.objects.filter(
        user=user,
        is_active=True,
        resource_type=ResourceAccess.RESOURCE_COURSE,
        course__isnull=False,
        course__is_published=True,
    ).values("course_id").distinct().count()

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
