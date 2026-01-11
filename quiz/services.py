from .utils import check_exam_lock


class ExamAccessService:
    """
    SINGLE source of access decision.
    """

    @staticmethod
    def can_start(user, exam) -> bool:
        if not user or not user.is_authenticated:
            return False

        locked, _ = check_exam_lock(user, exam)
        return not locked


