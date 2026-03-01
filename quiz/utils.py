from functools import lru_cache
from typing import Optional, Tuple, Dict

from django.db import transaction
from django.db.models import QuerySet

from .models import *



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


###############safe str delete logic########
# quiz/utils.py

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quiz.models import Exam


class SafeStrMixin:
    STR_FIELDS = ()

    def __str__(self):
        parts = []

        for field in self.STR_FIELDS:
            fk_id = getattr(self, f"{field}_id", None)
            if not fk_id:
                parts.append("N/A")
                continue

            try:
                obj = getattr(self, field)
                parts.append(str(obj))
            except Exception:
                parts.append("N/A")

        return " → ".join(parts) if parts else super().__str__()


def user_passed_exam(user, exam: "Exam") -> bool:
    # keep your existing logic here
    return True




def calculate_global_percentile(plan):
    from .models import StudyPlan

    total_users = StudyPlan.objects.filter(
        is_completed=True
    ).count()

    if total_users == 0:
        return 0

    higher = StudyPlan.objects.filter(
        is_completed=True,
        total_correct__gt=plan.total_correct
    ).count()

    percentile = 100 - round((higher / total_users) * 100, 2)
    return percentile



    # quiz/utils.py




def calculate_live_rank(plan, domain_id=None):
    """
    Calculate real-time global rank & percentile
    among active users.
    Optionally filter by domain.
    """

    from .models import StudyPlan

    # Only compare active competitive plans
    plans = StudyPlan.objects.filter(is_active=True)

    if domain_id:
        plans = plans.filter(domain_id=domain_id)

    plans = list(plans)

    if not plans:
        return None, 0

    # Compute competitive score safely
    scored = []

    for p in plans:
        try:
            score = p.global_competitive_score()
        except Exception:
            score = 0
        scored.append((p.id, score))

    # Sort highest score first
    scored.sort(key=lambda x: x[1], reverse=True)

    total_users = len(scored)

    # Find rank
    for index, (pid, _) in enumerate(scored, start=1):
        if pid == plan.id:

            percentile = round(
                ((total_users - index) / total_users) * 100,
                2
            ) if total_users > 0 else 0

            return index, percentile

    return None, 0