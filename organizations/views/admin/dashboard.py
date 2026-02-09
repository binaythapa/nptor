from django.shortcuts import render
from organizations.permissions import org_admin_required
from organizations.models.membership import OrganizationMember
from organizations.models.assignment import CourseAssignment
from courses.models import Course
from courses.models.progress import LessonProgress


import logging
from core.utils.memory import get_memory_usage_mb

logger = logging.getLogger("django")


@org_admin_required
def org_dashboard(request):
    mem = get_memory_usage_mb()
    logger.info(f"Organization Dashboard memory usage: {mem} MB")
    org = request.active_org

    # =========================
    # ORGANIZATION STATS
    # =========================
    stats = {
        "students": OrganizationMember.objects.filter(
            organization=org,
            role="student",
            is_active=True,
        ).count(),

        "courses": Course.objects.filter(
            organization=org,
            is_published=True,
        ).count(),

        "assignments": CourseAssignment.objects.filter(
            organization=org
        ).count(),
    }

    # =========================
    # ASSIGNED COURSES PROGRESS
    # =========================
    assignments = (
        CourseAssignment.objects
        .filter(organization=org)
        .select_related("course", "student")
    )

    assigned_courses = []

    for assignment in assignments:
        course = assignment.course
        student = assignment.student

        total_lessons = LessonProgress.objects.filter(
            lesson__section__course=course
        ).values("lesson_id").distinct().count()

        completed_lessons = LessonProgress.objects.filter(
            user=student,
            lesson__section__course=course,
            completed=True
        ).count()

        progress = int((completed_lessons / total_lessons) * 100) if total_lessons else 0

        assigned_courses.append({
            "course": course,
            "student": student,
            "progress": progress,
            "completed": completed_lessons,
            "total": total_lessons,
        })

    # =========================
    # RENDER
    # =========================
    return render(
        request,
        "organizations/admin/dashboard.html",
        {
            "org": org,
            "stats": stats,
            "assigned_courses": assigned_courses,
        }
    )
