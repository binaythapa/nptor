"""Reliable completion handling for course practice lessons.

Practice questions are currently tracked through the practice session's ``p_seen``
list. This service keeps that existing contract, but makes completion depend on
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

    A lesson with no eligible questions is deliberately not auto-completed;
    that is a content/configuration issue requiring administrator attention.
    """
    if not lesson or not getattr(request.user, "is_authenticated", False):
        return False

    if seen is None:
        seen = request.session.get("p_seen", [])

    # Include the currently displayed question. The standard POST flow calls
    # this service before it appends the current question to p_seen, while the
    # AJAX flow appends it first. Supporting both makes completion consistent.
    seen_ids = {
        int(value)
        for value in seen
        if str(value).isdigit()
    }
    current_question_id = request.session.get("p_qid")
    if current_question_id and str(current_question_id).isdigit():
        seen_ids.add(int(current_question_id))

    available_count = get_practice_question_queryset(lesson).count()
    if available_count <= 0:
        return False

    threshold = lesson.practice_threshold or available_count
    required_count = min(threshold, available_count)

    return len(seen_ids) >= required_count


def track_practice_completion(request, lesson):
    """Record progress from the current run and update lesson progress.

    The count is derived from the current run's unique ``p_seen`` question IDs
    rather than an accumulated lifetime/session counter. This prevents a retry
    from inheriting the previous run's count and completing prematurely.
    """
    seen = request.session.get("p_seen", [])
    seen_ids = {
        int(value)
        for value in seen
        if str(value).isdigit()
    }
    current_question_id = request.session.get("p_qid")
    if current_question_id and str(current_question_id).isdigit():
        seen_ids.add(int(current_question_id))

    count = len(seen_ids)

    # Keep the historical key synchronized for compatibility with any older
    # code, but never use its previous value to calculate this run's progress.
    request.session[f"practice_seen_lesson_{lesson.id}"] = count

    if is_practice_complete(request, lesson, seen=seen):
        _mark_lesson_completed(request.user, lesson)
        request.session[f"practice_done_{lesson.id}"] = True
        return max(count, lesson.practice_threshold or count)

    return count
