from quiz.models import UserExam


def _published_track_exams(track):
    return list(
        track.exams.filter(
            is_published=True,
            organization__isnull=True,
        )
        .prefetch_related("prerequisite_exams")
        .order_by("created_at", "id")
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


def track_exam_lock(user, exam, ordered_exams=None, passed_exam_ids=None):
    """Return (locked, reason) for an exam's track progression policy."""
    if not exam.track_id:
        return False, None

    exams = ordered_exams or _published_track_exams(exam.track)
    passed_ids = (
        passed_exam_ids
        if passed_exam_ids is not None
        else _passed_exam_ids(user, exams)
    )

    try:
        index = next(
            item_index
            for item_index, item in enumerate(exams)
            if item.id == exam.id
        )
    except StopIteration:
        return False, None

    if index > 0:
        previous = exams[index - 1]
        if previous.id not in passed_ids:
            return True, "Previous track exam required"

    prerequisite_ids = set(
        exam.prerequisite_exams.values_list("id", flat=True)
    )
    if prerequisite_ids and not prerequisite_ids.issubset(passed_ids):
        return True, "Prerequisite exam required"

    return False, None


def build_track_progress(user, track):
    """Build presentation-ready progression state for a student track."""
    exams = _published_track_exams(track)
    passed_ids = _passed_exam_ids(user, exams)
    items = []

    for index, exam in enumerate(exams):
        is_completed = exam.id in passed_ids
        is_unlocked = index == 0 or exams[index - 1].id in passed_ids
        lock_reason = None

        prerequisite_ids = set(
            exam.prerequisite_exams.values_list("id", flat=True)
        )
        if is_unlocked and prerequisite_ids and not prerequisite_ids.issubset(passed_ids):
            is_unlocked = False
            lock_reason = "Complete the prerequisite exam(s) first."
        elif not is_unlocked:
            lock_reason = "Complete the previous exam with a passing score."

        items.append(
            {
                "exam": exam,
                "index": index + 1,
                "is_completed": is_completed,
                "is_unlocked": is_unlocked,
                "lock_reason": lock_reason,
                "duration_minutes": (exam.duration_seconds or 0) // 60,
                "question_count": exam.question_count,
                "passing_score": exam.passing_score,
            }
        )

    total_count = len(exams)
    completed_count = len(passed_ids)
    percent = int((completed_count / total_count) * 100) if total_count else 0

    return {
        "items": items,
        "total_count": total_count,
        "completed_count": completed_count,
        "percent": percent,
    }
