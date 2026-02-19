

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from quiz.models import (
    ExamTrack,
    ExamSubscription,
    ExamTrackSubscription,
    UserExam,
)
from courses.models import Course, CourseSubscription
@login_required
def exam_list(request):
    user = request.user

    # ================================
    # COURSES (PLATFORM ONLY)
    # ================================
    courses_qs = Course.objects.filter(
        is_published=True,
        organization__isnull=True,   # ✅ THIS is the key filter
    ).order_by("-created_at")

    subscribed_course_ids = set(
        CourseSubscription.objects.filter(
            user=user,
            is_active=True,
            course__organization__isnull=True
        ).values_list("course_id", flat=True)
    )

    courses = [
        {
            "course": course,
            "is_subscribed": course.id in subscribed_course_ids,
        }
        for course in courses_qs
    ]

    # ================================
    # EXAM TRACKS
    # ================================
    tracks = (
        ExamTrack.objects
        .filter(is_active=True)
        .prefetch_related(
            "exams",
            "exams__prerequisite_exams"
        )
        .order_by("title")
    )

    track_subs = {
        s.track_id: s
        for s in ExamTrackSubscription.objects.filter(
            user=user,
            is_active=True
        )
    }

    exam_subs = {
        s.exam_id: s
        for s in ExamSubscription.objects.filter(
            user=user,
            is_active=True
        )
    }

    passed_exam_ids = set(
        UserExam.objects.filter(
            user=user,
            passed=True
        ).values_list("exam_id", flat=True)
    )

    track_map = {}

    for track in tracks:
        exams = (
            track.exams
            .filter(is_published=True)
            .order_by("level", "title")
        )

        if not exams.exists():
            continue

        track_subscription = track_subs.get(track.id)
        is_track_subscribed = (
            track_subscription is not None
            and track_subscription.is_valid()
        )

        items = []

        for exam in exams:
            locked_reason = None

            prereqs = exam.prerequisite_exams.all()
            missing = [
                p.title for p in prereqs
                if p.id not in passed_exam_ids
            ]
            if missing:
                locked_reason = "Pass prerequisite: " + ", ".join(missing)

            if not locked_reason and exam.level and exam.level > 1:
                has_prev = any(
                    e.level == exam.level - 1 and e.id in passed_exam_ids
                    for e in exams
                )
                if not has_prev:
                    locked_reason = f"Pass Level {exam.level - 1} first"

            exam_subscription = exam_subs.get(exam.id)
            is_exam_subscribed = (
                exam_subscription is not None
                and exam_subscription.is_valid()
            )

            can_subscribe = (
                track.subscription_scope == ExamTrack.EXAM
                and locked_reason is None
            )

            items.append({
                "exam": exam,
                "duration_minutes": exam.duration_seconds // 60,
                "is_exam_subscribed": is_exam_subscribed,
                "can_subscribe": can_subscribe,
                "locked_reason": locked_reason,
                "exam_subscription": exam_subscription,
                "is_track_subscribed": is_track_subscribed,
                "track_subscription": track_subscription,
            })

        track_map[track] = items

    return render(request, "quiz/student/exam/exam_list.html", {
        "courses": courses,        # ✅ platform courses only
        "track_map": track_map,
    })
