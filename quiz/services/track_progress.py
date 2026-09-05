from quiz.models import UserExam


def _published_track_items(track):
    return list(
        track.track_exams.filter(
            exam__is_published=True,
            exam__organization__isnull=True,
        )
        .select_related("exam")
        .prefetch_related("prerequisite_exams")
        .order_by("order", "id")
    )


def _passed_exam_ids(user, exams):
    exam_ids = [exam.id for exam in exams]
    if not exam_ids:
        return set()

    return set(
        UserExam.objects.filter(
            user=user,
            exam_id__in=exam_ids,
            submitted_at__isnull=False,
            passed=True,
        )
        .values_list("exam_id", flat=True)
        .distinct()
    )


def _passed_prerequisite_ids(user, prerequisites):
    prerequisite_ids = [exam.id for exam in prerequisites]
    if not prerequisite_ids:
        return set()

    return _passed_exam_ids(user, prerequisites)


def track_exam_lock(
    user,
    exam,
    ordered_exams=None,
    passed_exam_ids=None,
    track=None,
):
    """Return (locked, reason) for a track-specific exam progression policy."""
    if track is not None:
        track_items = _published_track_items(track)
        matching_items = [item for item in track_items if item.exam_id == exam.id]
    else:
        matching_items = list(
            exam.track_memberships.filter(
                track__is_active=True,
                exam__is_published=True,
            )
            .select_related("track", "exam")
            .prefetch_related("prerequisite_exams")
        )

    if not matching_items:
        return False, None

    for item in matching_items:
        items = ordered_exams
        if items is None:
            items = [entry.exam for entry in _published_track_items(item.track)]

        passed_ids = (
            passed_exam_ids
            if passed_exam_ids is not None
            else _passed_exam_ids(user, items)
        )

        try:
            index = next(
                item_index
                for item_index, candidate in enumerate(items)
                if candidate.id == exam.id
            )
        except StopIteration:
            index = 0

        if index > 0:
            previous = items[index - 1]
            if previous.id not in passed_ids:
                continue

        prerequisite_ids = {prereq.id for prereq in item.prerequisite_exams.all()}
        if prerequisite_ids:
            passed_prerequisites = _passed_prerequisite_ids(
                user,
                list(item.prerequisite_exams.all()),
            )
            if not prerequisite_ids.issubset(passed_prerequisites):
                continue

        return False, None

    return True, "Track progression requirement"


def build_track_progress(user, track):
    """Build presentation-ready progression state for a student track."""
    items = _published_track_items(track)
    exams = [item.exam for item in items]
    passed_ids = _passed_exam_ids(user, exams)
    progress_items = []

    for index, track_item in enumerate(items):
        exam = track_item.exam
        is_completed = exam.id in passed_ids
        is_unlocked = index == 0 or exams[index - 1].id in passed_ids
        lock_reason = None

        prerequisite_ids = {prereq.id for prereq in track_item.prerequisite_exams.all()}
        if is_unlocked and prerequisite_ids:
            passed_prerequisites = _passed_prerequisite_ids(
                user,
                list(track_item.prerequisite_exams.all()),
            )
            if not prerequisite_ids.issubset(passed_prerequisites):
                is_unlocked = False
                lock_reason = "Complete the prerequisite exam(s) first."
        elif not is_unlocked:
            lock_reason = "Complete the previous exam with a passing score."

        progress_items.append(
            {
                "exam": exam,
                "track_exam": track_item,
                "index": index + 1,
                "is_completed": is_completed,
                "is_required": track_item.is_required,
                "is_unlocked": is_unlocked,
                "lock_reason": lock_reason,
                "duration_minutes": (exam.duration_seconds or 0) // 60,
                "question_count": exam.question_count,
                "passing_score": exam.passing_score,
            }
        )

    total_count = len(progress_items)
    completed_count = len(passed_ids.intersection({exam.id for exam in exams}))
    percent = int((completed_count / total_count) * 100) if total_count else 0

    return {
        "items": progress_items,
        "total_count": total_count,
        "completed_count": completed_count,
        "percent": percent,
    }
