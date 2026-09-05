from pathlib import Path
from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates/quiz/student/exam/exam_detail.html"


class ExamDetailContractTests(SimpleTestCase):
    def test_exam_detail_exposes_student_facing_exam_information(self):
        html = TEMPLATE.read_text(encoding="utf-8")
        for hook in (
            "exam-detail-hero",
            "exam-detail-metrics",
            "exam-detail-rules",
            "exam-detail-access",
            "exam-detail-action",
            "exam-detail-track",
            "exam-detail-attempts",
        ):
            self.assertIn(hook, html)

    def test_exam_detail_has_expected_action_states(self):
        html = TEMPLATE.read_text(encoding="utf-8")
        for copy in (
            "Start Exam",
            "Continue Exam",
            "Retry Exam",
            "Review Result",
            "Preview Exam",
            "Locked",
            "Passing score",
            "Attempts",
        ):
            self.assertIn(copy, html)
