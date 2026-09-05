from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, render

from courses.models import Course, LessonProgress
from quiz.models import (
    Country,
    Exam,
    GovernmentBody,
    GovernmentExamProgram,
    GovernmentExamStage,
    GovernmentExamVersion,
    UserExam,
)


@login_required
def government_program_dashboard(request, country_slug, body_slug, program_slug):
    country = get_object_or_404(Country, slug=country_slug, is_active=True)
    body = get_object_or_404(
        GovernmentBody,
        country=country,
        slug=body_slug,
        is_active=True,
    )
    program = get_object_or_404(
        GovernmentExamProgram.objects.select_related("content_vertical"),
        country=country,
        government_body=body,
        slug=program_slug,
        is_active=True,
    )

    courses = list(
        program.courses.filter(
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )
        .annotate(total_lessons=Count("sections__lessons", distinct=True))
        .order_by("title")
    )
    course_ids = [course.id for course in courses]
    completed_by_course = defaultdict(int)
    if course_ids:
        rows = (
            LessonProgress.objects
            .filter(user=request.user, completed=True, lesson__section__course_id__in=course_ids)
            .values("lesson__section__course_id")
            .annotate(total=Count("id"))
        )
        completed_by_course.update(
            {row["lesson__section__course_id"]: row["total"] for row in rows}
        )

    course_cards = []
    for course in courses:
        total = course.total_lessons or 0
        completed = completed_by_course.get(course.id, 0)
        progress = min(100, int((completed / total) * 100)) if total else 0
        course_cards.append(
            {
                "course": course,
                "completed": completed,
                "total": total,
                "progress": progress,
            }
        )

    stages = list(
        GovernmentExamStage.objects.filter(
            version__program=program,
            version__status=GovernmentExamVersion.ACTIVE,
            is_active=True,
        )
        .select_related("version", "exam")
        .order_by("version__effective_from", "order", "id")
    )
    exam_ids = list(dict.fromkeys(stage.exam_id for stage in stages))
    exams = list(
        Exam.objects.filter(id__in=exam_ids, is_published=True)
        .select_related("primary_category")
        .order_by("title")
    )
    attempts = list(
        UserExam.objects.filter(
            user=request.user,
            exam_id__in=exam_ids,
            submitted_at__isnull=False,
        )
        .select_related("exam")
        .order_by("-submitted_at")
    )
    attempts_by_exam = defaultdict(list)
    for attempt in attempts:
        attempts_by_exam[attempt.exam_id].append(attempt)

    exam_cards = []
    for exam in exams:
        exam_attempts = attempts_by_exam.get(exam.id, [])
        latest = exam_attempts[0] if exam_attempts else None
        passed = any(attempt.passed is True for attempt in exam_attempts)
        exam_cards.append(
            {
                "exam": exam,
                "attempts": len(exam_attempts),
                "latest_score": latest.score if latest else None,
                "passed": passed,
            }
        )

    total_lessons = sum(item["total"] for item in course_cards)
    completed_lessons = sum(item["completed"] for item in course_cards)
    overall_progress = min(100, int((completed_lessons / total_lessons) * 100)) if total_lessons else 0
    passed_exams = sum(1 for item in exam_cards if item["passed"])
    attempted_exams = sum(1 for item in exam_cards if item["attempts"])
    latest_attempt = attempts[0] if attempts else None
    average_score = (
        round(sum(float(attempt.score or 0) for attempt in attempts) / len(attempts), 1)
        if attempts
        else None
    )

    return render(
        request,
        "quiz/student/government_dashboard.html",
        {
            "country": country,
            "body": body,
            "program": program,
            "courses": course_cards,
            "stages": stages,
            "exams": exam_cards,
            "stats": {
                "overall_progress": overall_progress,
                "course_count": len(course_cards),
                "exam_count": len(exam_cards),
                "attempted_exams": attempted_exams,
                "passed_exams": passed_exams,
                "average_score": average_score,
                "total_attempts": len(attempts),
            },
            "latest_attempt": latest_attempt,
        },
    )
