from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from courses.models import Course
from quiz.models import Exam, ExamTrack, LearningShortlist


RESOURCE_MAP = {
    LearningShortlist.RESOURCE_COURSE: Course,
    LearningShortlist.RESOURCE_TRACK: ExamTrack,
    LearningShortlist.RESOURCE_EXAM: Exam,
}


def _public_resource_queryset(resource_type):
    model = RESOURCE_MAP.get(resource_type)
    if model is None:
        raise Http404("Resource not found.")

    if resource_type == LearningShortlist.RESOURCE_COURSE:
        return model.objects.filter(
            approval_status=Course.APPROVAL_APPROVED,
            is_published=True,
            is_public=True,
            organization__isnull=True,
            category__is_active=True,
            category__organization__isnull=True,
            category__domain__is_active=True,
            category__domain__organization__isnull=True,
        )

    if resource_type == LearningShortlist.RESOURCE_TRACK:
        return model.objects.filter(
            is_active=True,
            organization__isnull=True,
            exams__is_published=True,
            exams__organization__isnull=True,
            exams__primary_category__is_active=True,
            exams__primary_category__organization__isnull=True,
            exams__primary_category__domain__is_active=True,
            exams__primary_category__domain__organization__isnull=True,
        ).distinct()

    return model.objects.filter(
        is_published=True,
        organization__isnull=True,
        primary_category__is_active=True,
        primary_category__organization__isnull=True,
        primary_category__domain__is_active=True,
        primary_category__domain__organization__isnull=True,
    )


@login_required
@require_POST
def learning_shortlist_toggle(request, resource_type, resource_id):
    resource = get_object_or_404(
        _public_resource_queryset(resource_type),
        pk=resource_id,
    )

    lookup = LearningShortlist.resource_lookup(resource_type, resource)
    existing = LearningShortlist.objects.filter(
        user=request.user,
        resource_type=resource_type,
        **lookup,
    ).first()

    if existing:
        existing.delete()
        shortlisted = False
    else:
        LearningShortlist.for_resource(
            user=request.user,
            resource_type=resource_type,
            resource=resource,
        )
        shortlisted = True

    return JsonResponse({
        "shortlisted": shortlisted,
        "resource_type": resource_type,
        "resource_id": resource.id,
    })
