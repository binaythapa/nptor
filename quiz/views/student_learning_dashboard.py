from collections import defaultdict
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Max
from django.shortcuts import render
from django.utils import timezone

from courses.models import Course, LessonProgress
from courses.models.subscription import CourseSubscription
from organizations.models.access import ResourceAccess
from quiz.models import Exam, ExamTrack, LearningShortlist, UserExam
from quiz.services.learning_catalog import _public_courses, _public_exams, _public_tracks


def _valid_accesses(queryset):
    """Return currently usable access records without exposing expired access."""
    return [access for access in queryset if access.is_valid()]


def _shortlist_items(user):
    rows = list(
        LearningShortlist.objects
        .filter(user=user)
        .select_related(
            "course",
            "course__category",
            "track",
            "exam",
            "exam__primary_category",
        )
    )
    valid_courses = {course.id: course for course in _public_courses().filter(id__in=[row.course_id for row in rows if row.course_id])}
    valid_tracks = {track.id: track for track in _public_tracks().filter(id__in=[row.track_id for row in rows if row.track_id])}
    valid_exams = {exam.id: exam for exam in _public_exams().filter(id__in=[row.exam_id for row in rows if row.exam_id])}

    items = []
    for row in rows:
        resource = None
        if row.resource_type == LearningShortlist.RESOURCE_COURSE:
            resource = valid_courses.get(row.course_id)
        elif row.resource_type == LearningShortlist.RESOURCE_TRACK:
            resource = valid_tracks.get(row.track_id)
        elif row.resource_type == LearningShortlist.RESOURCE_EXAM:
            resource = valid_exams.get(row.exam_id)
        if resource is None:
            continue
        items.append({
            "item": row,
            "resource": resource,
            "type": row.resource_type,
        })
    return items


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
    last_activity_by_course = {}
    if course_ids:
        completed_rows = (
            LessonProgress.objects
            .filter(user=user, completed=True, lesson__section__course_id__in=course_ids)
            .values("lesson__section__course_id")
            .annotate(total=Count("id"))
        )
        completed_by_course.update({row["lesson__section__course_id"]: row["total"] for row in completed_rows})

        last_activity_rows = (
            LessonProgress.objects
            .filter(user=user, lesson__section__course_id__in=course_ids)
            .values("lesson__section__course_id")
            .annotate(last_activity=Max("completed_at"))
        )
        last_activity_by_course.update({row["lesson__section__course_id"]: row["last_activity"] for row in last_activity_rows})

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
            "last_activity": last_activity_by_course.get(course.id) or course.created_at,
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
        track_attempts = [attempt for exam in exams for attempt in attempts_by_exam.get(exam.id, [])]
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
            "last_activity": max((attempt.submitted_at for attempt in track_attempts if attempt.submitted_at), default=track.created_at),
        })

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
    shortlist_items = _shortlist_items(user)

    learning_activity = []
    for item in courses_data:
        learning_activity.append({
            "activity_type": "course",
            "resource": item["course"],
            "activity_date": item["last_activity"],
            "progress": item["progress"],
            "status": "Completed" if item["progress"] >= 100 else ("In Progress" if item["progress"] else "Not Started"),
            "source": item["source"],
            "url": f"/courses/{item['course'].slug}/learn/",
        })

    for attempt in submitted_attempts:
        learning_activity.append({
            "activity_type": "exam",
            "resource": attempt.exam,
            "activity_date": attempt.submitted_at,
            "progress": attempt.score,
            "status": "Passed" if attempt.passed else "Failed",
            "attempt": attempt,
        })

    for item in tracks_data:
        learning_activity.append({
            "activity_type": "track",
            "resource": item["track"],
            "activity_date": item["last_activity"],
            "progress": item["passed"],
            "total": item["exam_count"],
            "status": "Completed" if item["completed"] else "In Progress",
            "source": item["source"],
            "url": "/quiz/exams/",
        })

    learning_activity.sort(key=lambda item: item["activity_date"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    activity_search = request.GET.get("activity_search", "").strip()
    activity_type = request.GET.get("activity_type", "all").strip().lower()
    if activity_type in {"course", "exam", "track"}:
        learning_activity = [item for item in learning_activity if item["activity_type"] == activity_type]
    if activity_search:
        query = activity_search.casefold()
        learning_activity = [item for item in learning_activity if query in item["resource"].title.casefold()]

    learning_activity_page = Paginator(learning_activity, 5).get_page(request.GET.get("activity_page", 1))

    return render(
        request,
        "quiz/student/student_dashboard.html",
        {
            "active_attempt": active_attempt,
            "submitted_attempts": submitted_attempts,
            "total_attempts": len(submitted_attempts),
            "passed_count": sum(1 for attempt in submitted_attempts if attempt.passed is True),
            "failed_count": sum(1 for attempt in submitted_attempts if attempt.passed is False),
            "learning_activity_page": learning_activity_page,
            "activity_search": activity_search,
            "activity_type": activity_type,
            "courses": courses_data,
            "tracks": tracks_data,
            "exams": exams_data,
            "shortlist_items": shortlist_items,
            "shortlist_count": len(shortlist_items),
            "learning_count": len(courses_data) + len(tracks_data) + len(exams_data),
            "generated_at": timezone.now(),
        },
    )
