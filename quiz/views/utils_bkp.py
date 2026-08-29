



# -------------------------
# Helpers
# -------------------------
def _user_passed_exam(user, exam):
    """
    Return True if user has any UserExam for `exam` with passed=True.
    Non-destructive check used for gating rules.
    """
    return UserExam.objects.filter(user=user, exam=exam, passed=True).exists()





