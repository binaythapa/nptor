"""Reliable completion handling for course practice lessons.

Practice questions are currently tracked through the practice session's ``p_seen``
list.  This service keeps that existing contract, but makes completion depend on
what is actually available for the lesson instead of requiring a threshold that
may be larger than the question pool.
"""

from django.db import transaction
from django.db.models import Q

from courses.models import LessonProgress
from quiz.models import Category, Domain, Question


def get_practice_question_queryset(lesson):
    """Return the same eligible question pool used by the practice view."""
    queryset = Question.objects.filter(
        question_type__in=[
            Question.SINGLE,
            Question.MULTI,
            Question.TRUE_FALSE,
        ],
        is_active=True,
        is_deleted=False,
    )

    if not lesson or not lesson.practice_domain_id:
        return queryset.none()

    domain = Domain.objects.filter(
        id=lesson.practice_domain_id,
        organization__isnull=True,
        is_active=True,
    ).first()
    if not domain:
        return queryset.none()

    queryset = queryset.filter(
        Q(primary_category__domain=domain)
        | Q(categories__domain=domain)
    ).distinct()

    if lesson.practice_category_id:
        category = Category.objects.filter(
            id=lesson.practice_category_id,
            domain=domain,
            is_active=True,
        ).first()
        if not category:
            return queryset.none()

        category_ids = category.get_descendants_include_self()
        queryset = queryset.filter(
            Q(primary_category_id__in=category_ids)
            | Q(categories__id__in=category_ids)
        ).distinct()

    if lesson.practice_difficulty:
        queryset = queryset.filter(difficulty=lesson.practice_difficulty)

    return queryset


def _mark_lesson_completed(user, lesson):
    """Mark a lesson complete safely and idempotently."""
    with transaction.atomic():
        progress, _ = LessonProgress.objects.select_for_update().get_or_create(
            user=user,
            lesson=lesson,
        )
        if not progress.completed:
            progress.mark_completed()


def is_practice_complete(request, lesson, seen=None):
    """Return whether the current practice run satisfies lesson completion.

    The effective requirement is capped at the number of eligible questions.
    This prevents a lesson from becoming impossible to complete when, for
    example, its threshold is 10 but only 4 matching questions exist.

    A lesson with no eligible questions is deliberately *not* auto-completed;
    that is a content/configuration issue that needs administrator attention.
    """
    if not lesson or not getattr(request.user, "is_authenticated", False):
        return False

    if seen is None:
        seen = request.session.get("p_seen", [])

    # Normalize IDs and remove duplicates before evaluating progress.
    seen_ids = {int(value) for value in seen if str(value).isdigit()}
    available_count = get_practice_question_queryset(lesson).count()
    if available_count <= 0:
        return False

    threshold = lesson.practice_threshold or available_count
    required_count = min(threshold, available_count)

    return len(seen_ids) >= required_count


def track_practice_completion(request, lesson):
    """Record one completed/left question and update lesson progress.

    The function retains its historical integer return value for existing
    callers.  When completion is reached, the returned value is promoted to
    the configured threshold so existing redirect checks continue to work.
    """
    key = f"practice_seen_lesson_{lesson.id}"
    count = request.session.get(key, 0) + 1
    request.session[key] = count

    seen = request.session.get("p_seen", [])
    if is_practice_complete(request, lesson, seen=seen):
        _mark_lesson_completed(request.user, lesson)
        request.session[f"practice_done_{lesson.id}"] = True
        return max(count, lesson.practice_threshold or count)

    return count
