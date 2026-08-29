from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from courses.models import Course
from quiz.services.catalog import build_exam_catalog


@login_required
def exam_list(request):
    """
    Student exam catalogue.

    Displays:

        Courses
        Exam Tracks
        Individual / standalone exams

    Access and subscription decisions are handled by
    build_exam_catalog().
    """

    # =========================================================
    # PLATFORM COURSES
    # =========================================================
    #
    # Only platform-level courses are shown here.
    #
    # Organization courses are handled separately.
    #
    # =========================================================

    courses_qs = (
        Course.objects
        .filter(
            is_published=True,
            organization__isnull=True,
        )
        .order_by(
            "-created_at",
        )
    )

    # =========================================================
    # BUILD CATALOG
    # =========================================================

    catalog = build_exam_catalog(
        user=request.user,
        courses=courses_qs,
    )

    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "quiz/student/exam/exam_list.html",
        {
            "courses": catalog["courses"],
            "track_map": catalog["track_map"],
            "standalone_exams": (
                catalog["standalone_exams"]
            ),
        },
    )