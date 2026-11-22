from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.shortcuts import render
from django.utils import timezone

from courses.models import Course, CourseEnrollment
from courses.models.subscription import CourseSubscription
from organizations.models.access import ResourceAccess
from quiz.models import UserExam, Exam
from quiz.services.streak_service import get_student_streak_summary


@login_required
def student_dashboard(request):
    """Render the centralized student learning dashboard."""
    user = request.user
    now = timezone.now()

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
    stats = completed_attempts.aggregate(
        total=Count("id"),
        passed=Count("id", filter=Q(passed=True)),
        avg_score=Avg("score"),
    )
    total_attempts = stats["total"]
    passed_attempts = stats["passed"]
    average_score = stats["avg_score"]

    # Dashboard statistics must represent explicit ownership only. Public
    # availability is intentionally excluded. Organization assignments,
    # administrator grants, individual purchases, course enrollments, and
    # course subscriptions are all included.
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
            Q(expires_at__isnull=True) | Q(expires_at__gt=now),
            user=user,
            resource_type=ResourceAccess.RESOURCE_COURSE,
            course__isnull=False,
            is_active=True,
            revoked_at__isnull=True,
        ).exclude(source=ResourceAccess.SOURCE_PUBLIC).values_list("course_id", flat=True)
    )

    learning_courses = Course.objects.filter(
        id__in=owned_course_ids,
        is_published=True,
    ).count()

    enrolled_courses = list(
        Course.objects.filter(
            id__in=owned_course_ids,
            is_published=True,
        )
        .select_related("category")
        .order_by("-id")[:3]
    )

    recent_results = [
        {
            "attempt": attempt,
            "status": "Passed" if attempt.passed else "Failed",
        }
        for attempt in submitted_attempts
    ]

    streak_summary = get_student_streak_summary(user)

    # =========================================================
    # ACTIVE STUDY PLAN & TODAY'S MISSION
    # =========================================================
    active_study_plan = user.study_plans.filter(is_active=True).first()
    study_plan_data = None
    if active_study_plan:
        day_index = active_study_plan.get_day_index()
        current_day_number = min(max(1, day_index + 1), active_study_plan.total_plan_days())
        today_completed = active_study_plan.daily_progress.get(str(day_index), 0)
        today_target = active_study_plan.questions_per_day
        today_percent = min(100, int((today_completed / today_target) * 100)) if today_target else 0
        is_today_completed = today_completed >= today_target
        completed_days = active_study_plan.get_completed_days_count()
        overall_percent = min(100, int((completed_days / max(1, active_study_plan.total_days)) * 100))
        target_name = (
            active_study_plan.exam.title
            if active_study_plan.exam
            else (active_study_plan.domain.name if active_study_plan.domain else "Target Certification")
        )
        study_plan_data = {
            "plan": active_study_plan,
            "day_number": current_day_number,
            "total_days": active_study_plan.total_plan_days(),
            "today_completed": today_completed,
            "today_target": today_target,
            "today_percent": today_percent,
            "is_today_completed": is_today_completed,
            "completed_days": completed_days,
            "overall_percent": overall_percent,
            "target_name": target_name,
        }

    # =========================================================
    # ACTIVE SUBSCRIPTIONS & ENTITLEMENTS
    # =========================================================
    active_subscriptions = list(
        CourseSubscription.objects.filter(
            user=user,
            is_active=True,
            status="active",
        )
        .select_related("course")
        .order_by("-subscribed_at")[:3]
    )
    active_access_records = list(
        ResourceAccess.objects.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now),
            user=user,
            is_active=True,
            revoked_at__isnull=True,
        )
        .exclude(source=ResourceAccess.SOURCE_PUBLIC)
        .select_related("course", "track")
        .order_by("-granted_at")[:3]
    )

    # =========================================================
    # PENDING & UPCOMING TASKS
    # =========================================================
    pending_tasks = []
    if active_attempt:
        pending_tasks.append({
            "title": f"Resume Exam: {active_attempt.exam.title}",
            "description": f"Unfinished attempt started {active_attempt.started_at.strftime('%b %d, %H:%M')}",
            "action_url": f"/quiz/exam/attempt/{active_attempt.id}/",
            "action_label": "Resume Exam",
            "badge": "In Progress",
            "badge_class": "is-warning",
            "icon": "fa-clock",
        })

    if study_plan_data and not study_plan_data["is_today_completed"]:
        pending_tasks.append({
            "title": f"Today's Study Plan Mission (Day {study_plan_data['day_number']})",
            "description": f"{study_plan_data['today_completed']} of {study_plan_data['today_target']} questions completed today",
            "action_url": "/quiz/study-plan/practice/",
            "action_label": "Continue Mission",
            "badge": "Daily Goal",
            "badge_class": "is-info",
            "icon": "fa-list-check",
        })

    if not streak_summary.get("is_active_today", False):
        pending_tasks.append({
            "title": "Practice to maintain your daily streak",
            "description": f"Solve qualifying questions today to keep your {streak_summary.get('current_streak', 0)}-day streak alive",
            "action_url": "/quiz/practice/",
            "action_label": "Practice Now",
            "badge": "Daily Streak",
            "badge_class": "is-danger",
            "icon": "fa-fire",
        })

    # =========================================================
    # RECOMMENDED NEXT LEARNING ACTIVITIES
    # =========================================================
    passed_exam_ids = [
        a.exam_id for a in submitted_attempts if getattr(a, "passed", False)
    ]
    recommended_exams = list(
        Exam.objects.filter(is_published=True)
        .prefetch_related("categories")
        .exclude(id__in=passed_exam_ids)
        .order_by("level", "-id")[:3]
    )

    return render(
        request,
        "quiz/student/student_dashboard_overview.html",
        {
            "active_attempt": active_attempt,
            "total_attempts": total_attempts,
            "passed_attempts": passed_attempts,
            "average_score": round(float(average_score), 1) if average_score is not None else 0,
            "learning_courses": learning_courses,
            "enrolled_courses": enrolled_courses,
            "recent_results": recent_results,
            "streak_summary": streak_summary,
            "study_plan_data": study_plan_data,
            "active_subscriptions": active_subscriptions,
            "active_access_records": active_access_records,
            "pending_tasks": pending_tasks,
            "recommended_exams": recommended_exams,
        },
    )
