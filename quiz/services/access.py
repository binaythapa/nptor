from .subscription import has_valid_subscription
from .unlock import has_passed_prerequisites

def can_access_exam(user, exam):
    if not exam.is_published:
        return False, "Exam not published"

    if not has_valid_subscription(user, exam):
        return False, "Subscription required"

    if not has_passed_prerequisites(user, exam):
        return False, "Complete previous level first"

    return True, None
