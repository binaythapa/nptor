from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from quiz.models import ExamTrack
from subscriptions.services import AccessService
from quiz.services.track_progress import build_track_progress


@login_required
def learning_track(request, slug):
    track = get_object_or_404(
        ExamTrack.objects.filter(
            is_active=True,
            organization__isnull=True,
        ).prefetch_related(
            "track_exams__exam",
            "track_exams__exam__primary_category",
            "track_exams__prerequisite_exams",
        ),
        slug=slug,
    )

    progress = build_track_progress(request.user, track)
    has_access = AccessService.has_access(
        student=request.user,
        resource_type=AccessService.RESOURCE_TRACK,
        resource=track,
    )

    return render(
        request,
        "quiz/student/learning_track.html",
        {
            "track": track,
            "exams": [item["exam"] for item in progress["items"]],
            "track_items": progress["items"],
            "completed_count": progress["completed_count"],
            "total_count": progress["total_count"],
            "track_progress": progress["percent"],
            "has_access": has_access,
            "is_free": track.is_free(),
        },
    )
