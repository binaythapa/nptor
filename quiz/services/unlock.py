from quiz.models import UserExam

def has_passed_prerequisites(user, exam):
    prereqs = exam.prerequisite_exams.all()

    if not prereqs.exists():
        return True

    passed_ids = set(
        UserExam.objects.filter(
            user=user,
            exam__in=prereqs,
            passed=True
        ).values_list("exam_id", flat=True)
    )

    required_ids = set(prereqs.values_list("id", flat=True))
    return passed_ids == required_ids
