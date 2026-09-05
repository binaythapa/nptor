from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from quiz.models import Exam, UserExam
from quiz.services.access import can_access_exam
from quiz.services.track_progress import build_track_progress


@login_required
def exam_detail(request, exam_id):
    exam = get_object_or_404(
        Exam.objects.select_related(
            "primary_category",
            "primary_category__domain",
        ).prefetch_related(
            "subscription_plans",
            "track_memberships__track",
            "track_memberships__prerequisite_exams",
        ),
        pk=exam_id,
        is_published=True,
        organization__isnull=True,
    )

    active_attempt = (
        UserExam.objects.filter(
            user=request.user,
            exam=exam,
            submitted_at__isnull=True,
        )
        .order_by("-started_at")
        .first()
    )
    latest_attempt = (
        UserExam.objects.filter(
            user=request.user,
            exam=exam,
            submitted_at__isnull=False,
        )
        .order_by("-submitted_at")
        .first()
    )

    has_access, access_reason = can_access_exam(request.user, exam)

    track_contexts = []
    for membership in exam.track_memberships.all():
        if not membership.track.is_active or membership.track.organization_id is not None:
            continue
        progress = build_track_progress(request.user, membership.track)
        item = next(
            (entry for entry in progress["items"] if entry["exam"].id == exam.id),
            None,
        )
        track_contexts.append(
            {
                "track": membership.track,
                "progress": progress,
                "item": item,
            }
        )

    if active_attempt and not active_attempt.is_active():
        active_attempt = None

    if active_attempt:
        action = "continue"
        action_label = "Continue Exam"
    elif latest_attempt and latest_attempt.passed:
        action = "review"
        action_label = "Review Result"
    elif latest_attempt and has_access:
        action = "retry"
        action_label = "Retry Exam"
    elif has_access:
        action = "start"
        action_label = "Start Exam"
    elif exam.is_free and not track_contexts:
        action = "locked"
        action_label = "Locked"
    else:
        action = "preview"
        action_label = "Preview Exam"

    return render(
        request,
        "quiz/student/exam/exam_detail.html",
        {
            "exam": exam,
            "active_attempt": active_attempt,
            "latest_attempt": latest_attempt,
            "has_access": has_access,
            "access_reason": access_reason,
            "track_contexts": track_contexts,
            "action": action,
            "action_label": action_label,
            "duration_minutes": (exam.duration_seconds or 0) // 60,
        },
    )
