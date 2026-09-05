from quiz.models import TrackExam, UserExam


def _published_track_exams(track):
    return list(
        TrackExam.objects.filter(
            track=track,
            exam__is_published=True,
            exam__organization__isnull=True,
        )
        .select_related("exam")
        .prefetch_related("prerequisites__exam")
        .order_by("position", "id")
    )


def _passed_exam_ids(user, exams):
    exam_ids = [item.exam_id for item in exams]
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


def track_exam_lock(user, exam, track=None, ordered_exams=None, passed_exam_ids=None):
    """Return (locked, reason) using only explicit track prerequisites."""
    track_exams = ordered_exams
    if track_exams is None:
        track = track or next(iter(exam.track_exams.all()), None).track if exam.track_exams.exists() else None
        if track is None:
            return False, None
        track_exams = _published_track_exams(track)

    passed_ids = passed_exam_ids if passed_exam_ids is not None else _passed_exam_ids(user, track_exams)
    current = next((item for item in track_exams if item.exam_id == exam.id), None)
    if current is None:
        return False, None

    prerequisite_ids = set(current.prerequisites.values_list("exam_id", flat=True))
    if prerequisite_ids and not prerequisite_ids.issubset(passed_ids):
        return True, "Prerequisite exam required"
    return False, None


def build_track_progress(user, track):
    """Build presentation-ready progression state for a student track."""
    track_exams = _published_track_exams(track)
    passed_ids = _passed_exam_ids(user, track_exams)
    items = []

    for index, track_exam in enumerate(track_exams):
        exam = track_exam.exam
        prerequisite_ids = set(track_exam.prerequisites.values_list("exam_id", flat=True))
        is_completed = exam.id in passed_ids
        is_unlocked = prerequisite_ids.issubset(passed_ids)
        lock_reason = None if is_unlocked else "Complete the prerequisite exam(s) first."

        items.append(
            {
                "exam": exam,
                "track_exam": track_exam,
                "index": index + 1,
                "is_completed": is_completed,
                "is_unlocked": is_unlocked,
                "lock_reason": lock_reason,
                "duration_minutes": (exam.duration_seconds or 0) // 60,
                "question_count": exam.question_count,
                "passing_score": exam.passing_score,
            }
        )

    total_count = len(track_exams)
    completed_count = len(passed_ids)
    percent = int((completed_count / total_count) * 100) if total_count else 0

    return {
        "items": items,
        "total_count": total_count,
        "completed_count": completed_count,
        "percent": percent,
    }
