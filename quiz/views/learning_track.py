from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from quiz.models import ExamTrack
from subscriptions.services import AccessService


@login_required
def learning_track(request, slug):
    track = get_object_or_404(
        ExamTrack.objects.filter(
            is_active=True,
            organization__isnull=True,
        ).prefetch_related(
            "exams",
            "exams__primary_category",
        ),
        slug=slug,
    )

    exams = [exam for exam in track.exams.all() if exam.is_published and exam.organization_id is None]
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
            "exams": exams,
            "has_access": has_access,
            "is_free": track.is_free(),
        },
    )
