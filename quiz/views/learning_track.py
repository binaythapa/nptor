from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from quiz.models import ExamTrack
from subscriptions.services import AccessService
from quiz.services.track_progress import build_track_progress


@login_required
def learning_track(request, slug):
    track = get_object_or_404(
        ExamTrack.objects.filter(
            is_active=True,
        ).select_related(
            "organization",
        ).prefetch_related(
            "track_exams__exam",
            "track_exams__exam__categories",
            "track_exams__prerequisite_exams",
        ),
        slug=slug,
    )

    has_access = AccessService.has_access(
        student=request.user,
        resource_type=AccessService.RESOURCE_TRACK,
        resource=track,
    )

    # Organization-owned tracks are private learning resources. They are
    # available only to students explicitly assigned by that organization.
    # Public subscription/payment logic must never unlock them.
    if track.organization_id is not None and not has_access:
        raise Http404("Track not found.")

    progress = build_track_progress(request.user, track)

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
