from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from courses.models import Course, LessonProgress
from courses.models.subscription import CourseSubscription
from organizations.models.access import ResourceAccess
from quiz.models import Exam, ExamTrack, UserExam


def _valid_accesses(queryset):
    """Return currently usable access records without exposing expired access."""
    return [access for access in queryset if access.is_valid()]


@login_required
def student_dashboard(request):
    user = request.user

    submitted_attempts = list(
        UserExam.objects
        .filter(user=user, submitted_at__isnull=False)
        .select_related("exam")
        .order_by("-submitted_at")
    )
    active_attempt = (
        UserExam.objects
        .filter(user=user, submitted_at__isnull=True)
        .select_related("exam")
        .order_by("-started_at")
        .first()
    )

    # The dashboard is driven by ResourceAccess, the final authorization
    # boundary. This makes purchases and admin grants visible immediately,
    # instead of relying on the legacy CourseSubscription table alone.
    accesses = _valid_accesses(
        ResourceAccess.objects
        .filter(user=user, is_active=True)
        .select_related("course", "track", "exam", "subscription", "organization")
        .order_by("-granted_at")
    )

    course_access = {}
    track_access = {}
    exam_access = {}

    for access in accesses:
        if access.resource_type == ResourceAccess.RESOURCE_COURSE and access.course_id:
            course_access.setdefault(access.course_id, access)
        elif access.resource_type == ResourceAccess.RESOURCE_TRACK and access.track_id:
            track_access.setdefault(access.track_id, access)
        elif access.resource_type == ResourceAccess.RESOURCE_EXAM and access.exam_id:
            exam_access.setdefault(access.exam_id, access)

    # Keep compatibility with older course purchases that pre-date the
    # ResourceAccess entitlement path, while all new purchases use the
    # canonical access record above.
    legacy_course_subs = (
        CourseSubscription.objects
        .filter(user=user, is_active=True)
        .select_related("course")
    )
    for subscription in legacy_course_subs:
        if subscription.course_id and subscription.course_id not in course_access:
            course_access[subscription.course_id] = None

    course_ids = list(course_access)
    courses = (
        Course.objects
        .filter(id__in=course_ids, is_published=True)
        .annotate(total_lessons=Count("sections__lessons", distinct=True))
        .order_by("title")
    )

    completed_by_course = defaultdict(int)
    if course_ids:
        completed_rows = (
            LessonProgress.objects
            .filter(user=user, completed=True, lesson__section__course_id__in=course_ids)
            .values("lesson__section__course_id")
            .annotate(total=Count("id"))
        )
        completed_by_course.update({row["lesson__section__course_id"]: row["total"] for row in completed_rows})

    courses_data = []
    for course in courses:
        completed = completed_by_course.get(course.id, 0)
        total = course.total_lessons or 0
        progress = min(100, int((completed / total) * 100)) if total else 0
        courses_data.append({
            "course": course,
            "completed": completed,
            "total": total,
            "progress": progress,
            "source": course_access[course.id].source if course_access[course.id] else "individual",
        })

    tracks = (
        ExamTrack.objects
        .filter(id__in=list(track_access), is_active=True)
        .order_by("title")
    )
    track_exams = defaultdict(list)
    if tracks:
        for exam in (
            Exam.objects
            .filter(track_id__in=list(track_access), is_published=True)
            .select_related("track")
            .order_by("track_id", "level", "id")
        ):
            track_exams[exam.track_id].append(exam)

    attempts_by_exam = defaultdict(list)
    for attempt in submitted_attempts:
        attempts_by_exam[attempt.exam_id].append(attempt)

    tracks_data = []
    for track in tracks:
        exams = track_exams.get(track.id, [])
        passed = sum(
            1 for exam in exams
            if any(attempt.passed is True for attempt in attempts_by_exam.get(exam.id, []))
        )
        tracks_data.append({
            "track": track,
            "exam_count": len(exams),
            "passed": passed,
            "completed": passed == len(exams) and bool(exams),
            "source": track_access[track.id].source,
        })

    # Standalone purchased/admin-granted exams. Exams belonging to an
    # accessible track are also represented here so the Exams filter is
    # useful without forcing the user to open the track first.
    accessed_exams = (
        Exam.objects
        .filter(id__in=list(exam_access), is_published=True)
        .select_related("track")
        .order_by("title")
    )
    exams_data = []
    for exam in accessed_exams:
        attempts = attempts_by_exam.get(exam.id, [])
        last = attempts[0] if attempts else None
        passed = any(attempt.passed is True for attempt in attempts)
        exams_data.append({
            "exam": exam,
            "attempts": len(attempts),
            "last_score": last.score if last else None,
            "passed": passed,
            "source": exam_access[exam.id].source,
        })

    # Exams unlocked through a purchased track should also appear as exam
    # cards, even when there is no individual exam entitlement.
    for track in tracks_data:
        for exam in track_exams.get(track["track"].id, []):
            if exam.id in exam_access:
                continue
            attempts = attempts_by_exam.get(exam.id, [])
            last = attempts[0] if attempts else None
            exams_data.append({
                "exam": exam,
                "attempts": len(attempts),
                "last_score": last.score if last else None,
                "passed": any(attempt.passed is True for attempt in attempts),
                "source": "track",
            })

    exams_data.sort(key=lambda item: item["exam"].title.lower())

    return render(
        request,
        "quiz/student/student_dashboard.html",
        {
            "active_attempt": active_attempt,
            "total_attempts": len(submitted_attempts),
            "passed_count": sum(1 for attempt in submitted_attempts if attempt.passed is True),
            "failed_count": sum(1 for attempt in submitted_attempts if attempt.passed is False),
            "courses": courses_data,
            "tracks": tracks_data,
            "exams": exams_data,
            "learning_count": len(courses_data) + len(tracks_data) + len(exams_data),
            "generated_at": timezone.now(),
        },
    )
