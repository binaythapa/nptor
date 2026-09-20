"""Reliable completion handling for course practice lessons.

Practice questions are tracked through the current practice session. Completion
must use the same effective filters as the practice view; reconstructing the
pool only from Lesson fields can disagree with the active session and leave a
finished practice lesson incomplete.
"""

from django.db import transaction
from django.db.models import Q

from courses.models import LessonProgress
from quiz.models import Category, Domain, Question


def _apply_filters(queryset, domain_id=None, category_id=None, difficulty=None):
    """Apply the practice view's domain/category/difficulty rules."""
    selected_domain = None

    if domain_id and str(domain_id).isdigit():
        selected_domain = Domain.objects.filter(
            id=domain_id,
            organization__isnull=True,
            is_active=True,
        ).first()

        if not selected_domain:
            return queryset.none()

        queryset = queryset.filter(
            Q(primary_category__domain=selected_domain)
            | Q(categories__domain=selected_domain)
        ).distinct()

    if category_id and str(category_id).isdigit():
        if not selected_domain:
            selected_domain = Domain.objects.filter(
                Q(id=domain_id) if domain_id and str(domain_id).isdigit()
                else Q(categories__id=category_id),
                organization__isnull=True,
                is_active=True,
            ).first()

        category = Category.objects.filter(
            id=category_id,
            is_active=True,
        ).first()

        if not category:
            return queryset.none()

        category_ids = category.get_descendants_include_self()
        queryset = queryset.filter(
            Q(primary_category_id__in=category_ids)
            | Q(categories__id__in=category_ids)
        ).distinct()

    if difficulty:
        queryset = queryset.filter(difficulty=difficulty)

    return queryset


def _base_question_queryset():
    return Question.objects.filter(
        question_type__in=[
            Question.SINGLE,
            Question.MULTI,
            Question.TRUE_FALSE,
        ],
        is_active=True,
        is_deleted=False,
    )


def get_practice_question_queryset(lesson):
    """Return the lesson-configured eligible question pool."""
    if not lesson or not lesson.practice_domain_id:
        return _base_question_queryset().none()

    return _apply_filters(
        _base_question_queryset(),
        domain_id=lesson.practice_domain_id,
        category_id=lesson.practice_category_id,
        difficulty=lesson.practice_difficulty,
    )


def get_active_practice_question_queryset(request, lesson):
    """Return the exact pool represented by the active practice session.

    Course practice stores the effective filters in ``p_filters``. Those
    filters are authoritative for the current run because they are also used
    by the AJAX next-question endpoint.
    """
    filters = request.session.get("p_filters") or {}

    if filters.get("domain"):
        return _apply_filters(
            _base_question_queryset(),
            domain_id=filters.get("domain"),
            category_id=filters.get("category"),
            difficulty=filters.get("difficulty"),
        )

    return get_practice_question_queryset(lesson)


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
    """Return whether the current practice run satisfies lesson completion."""
    if not lesson or not getattr(request.user, "is_authenticated", False):
        return False

    if seen is None:
        seen = request.session.get("p_seen", [])

    seen_ids = {
        int(value)
        for value in seen
        if str(value).isdigit()
    }

    # The normal POST flow evaluates before appending the current question.
    current_question_id = request.session.get("p_qid")
    if current_question_id and str(current_question_id).isdigit():
        seen_ids.add(int(current_question_id))

    question_queryset = get_active_practice_question_queryset(request, lesson)
    eligible_ids = set(question_queryset.values_list("id", flat=True))
    completed_ids = seen_ids.intersection(eligible_ids)
    available_count = len(eligible_ids)

    if available_count <= 0:
        return False

    threshold = lesson.practice_threshold or available_count
    required_count = min(int(threshold), available_count)

    return len(completed_ids) >= required_count


def track_practice_completion(request, lesson):
    """Record current-run progress and update lesson progress."""
    seen = request.session.get("p_seen", [])
    seen_ids = {
        int(value)
        for value in seen
        if str(value).isdigit()
    }

    current_question_id = request.session.get("p_qid")
    if current_question_id and str(current_question_id).isdigit():
        seen_ids.add(int(current_question_id))

    question_queryset = get_active_practice_question_queryset(request, lesson)
    eligible_ids = set(question_queryset.values_list("id", flat=True))
    count = len(seen_ids.intersection(eligible_ids))

    request.session[f"practice_seen_lesson_{lesson.id}"] = count

    if is_practice_complete(request, lesson, seen=seen):
        _mark_lesson_completed(request.user, lesson)
        request.session[f"practice_done_{lesson.id}"] = True
        return max(count, int(lesson.practice_threshold or count))

    return count
