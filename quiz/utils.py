from functools import lru_cache
from typing import Optional, Tuple, Dict

from django.db import transaction
from django.db.models import QuerySet

from .models import Category, Exam, UserExam


# ============================================================
# CATEGORY HELPERS
# ============================================================

@lru_cache(maxsize=1024)
def _leaf_category_name_cached(category_id: int) -> Optional[str]:
    if not category_id:
        return None

    try:
        c = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return None

    try:
        if c.children.exists():
            return ""
    except Exception:
        pass

    parts = [p.strip() for p in (c.name or "").split("->") if p]
    return parts[-1] if parts else (c.name or "")


def get_leaf_category_name(category: Optional[Category]) -> Optional[str]:
    if not category:
        return None

    cid = getattr(category, "id", None)
    if cid is None:
        parts = [p.strip() for p in (category.name or "").split("->") if p]
        return parts[-1] if parts else (category.name or "")

    return _leaf_category_name_cached(cid)


def clear_leaf_category_cache() -> None:
    _leaf_category_name_cached.cache_clear()


# ============================================================
# EXAM PROGRESSION / LOCKING (SINGLE SOURCE OF TRUTH)
# ============================================================

def user_passed_exam(user, exam: Exam) -> bool:
    """
    Return True if user has PASSED this exam.
    """
    return UserExam.objects.filter(
        user=user,
        exam=exam,
        passed=True
    ).exists()


def check_exam_lock(user, exam: Exam) -> Tuple[bool, Optional[str]]:
    """
    STRICT progression rules (FINAL VERSION):

    1️⃣ Prerequisite exams (explicit) must be PASSED
    2️⃣ Level-based lock:
        - Level 1 → always unlocked
        - Level N → user must pass Level N-1 exam
          in the SAME TRACK (if track exists)
    """

    # --------------------------------------------------
    # 1️⃣ PREREQUISITE EXAMS
    # --------------------------------------------------
    prereqs = getattr(exam, "prerequisite_exams", None)
    if prereqs and prereqs.exists():
        missing = [
            p.title for p in prereqs.all()
            if not user_passed_exam(user, p)
        ]
        if missing:
            return True, "Pass prerequisite exam(s): " + ", ".join(missing)

    # --------------------------------------------------
    # 2️⃣ LEVEL-BASED LOCK (TRACK-SAFE)
    # --------------------------------------------------
    if exam.level and exam.level > 1:

        prev_level_exams = Exam.objects.filter(
            is_published=True,
            level=exam.level - 1,
        )

        # 🔒 Apply track filter ONLY if track exists
        if exam.track:
            prev_level_exams = prev_level_exams.filter(track=exam.track)

        passed_prev = UserExam.objects.filter(
            user=user,
            exam__in=prev_level_exams,
            passed=True,
        ).exists()

        if not passed_prev:
            track_name = exam.track.title if exam.track else "this track"
            return True, f"Pass Level {exam.level - 1} of {track_name} to unlock"

    return False, None


# ============================================================
# TRACK / DOMAIN PROGRESS SUMMARY
# ============================================================

def get_domain_progress(user) -> Dict[str, dict]:
    """
    Track-wise progress summary:

    {
      "SnowPro Core": {"total": 3, "passed": 1},
      "Power BI": {"total": 4, "passed": 2},
    }
    """

    result: Dict[str, dict] = {}

    exams = Exam.objects.filter(
        is_published=True
    ).select_related("track")

    for exam in exams:
        key = exam.track.title if exam.track else "General"

        result.setdefault(key, {"total": 0, "passed": 0})
        result[key]["total"] += 1

        if user_passed_exam(user, exam):
            result[key]["passed"] += 1

    return result


# ============================================================
# SAFE CLEANUP (ACTIVE ATTEMPTS ONLY)
# ============================================================

def cleanup_illegal_attempts(user):
    """
    Deletes ONLY ACTIVE attempts that violate lock rules.
    🔒 Completed attempts are NEVER deleted.
    """

    illegal_ids = []

    active_attempts = (
        UserExam.objects
        .select_related("exam")
        .filter(user=user, submitted_at__isnull=True)
    )

    for ue in active_attempts:
        locked, _ = check_exam_lock(user, ue.exam)
        if locked:
            illegal_ids.append(ue.id)

    if illegal_ids:
        UserExam.objects.filter(id__in=illegal_ids).delete()

    return len(illegal_ids)
