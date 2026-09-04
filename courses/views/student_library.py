from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from courses.models import CourseEnrollment
from courses.services.progress import get_course_progress


PAGE_SIZE = 9


def _student_library(request, mode):
    enrollments = (
        CourseEnrollment.objects
        .filter(user=request.user, is_active=True)
        .select_related("course")
        .order_by("-enrolled_at")
    )

    courses = []
    for enrollment in enrollments:
        course = enrollment.course
        completed, total, progress = get_course_progress(request.user, course)

        if mode == "continue" and not (0 < progress < 100):
            continue
        if mode == "completed" and progress < 100:
            continue

        courses.append({
            "course": course,
            "completed": completed,
            "total": total,
            "progress": progress,
            "enrolled_at": enrollment.enrolled_at,
        })

    paginator = Paginator(courses, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    titles = {
        "all": "My Courses",
        "continue": "Continue Learning",
        "completed": "Completed Courses",
    }

    return render(
        request,
        "courses/student/student_library.html",
        {
            "page_obj": page_obj,
            "course_items": page_obj.object_list,
            "library_mode": mode,
            "page_title": titles[mode],
        },
    )


@login_required
def my_courses(request):
    return _student_library(request, "all")


@login_required
def continue_learning(request):
    return _student_library(request, "continue")


@login_required
def completed_courses(request):
    return _student_library(request, "completed")
