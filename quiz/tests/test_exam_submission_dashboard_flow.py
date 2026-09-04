from pathlib import Path
import unittest


class ExamSubmissionDashboardFlowTests(unittest.TestCase):
    def test_exam_submit_returns_student_to_dashboard_after_submission(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "quiz" / "views" / "exams.py").read_text(encoding="utf-8")

        self.assertIn("return redirect('quiz:student_dashboard')", source)

    def test_student_dashboard_exposes_submitted_attempts_for_answer_review(self):
        root = Path(__file__).resolve().parents[2]
        view_source = (root / "quiz" / "views" / "student_learning_dashboard.py").read_text(encoding="utf-8")
        template = (root / "templates" / "quiz" / "student" / "student_dashboard.html").read_text(encoding="utf-8")

        self.assertIn('"submitted_attempts": submitted_attempts', view_source)
        self.assertIn("Recent Exam Results", template)
        self.assertIn("View Answers", template)
        self.assertIn("quiz:exam_result", template)

    def test_result_page_no_longer_contains_the_answer_review_section(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "result.html").read_text(encoding="utf-8")

        self.assertNotIn("ANSWER REVIEW", template)
        self.assertNotIn("📋 Answer Review", template)


if __name__ == "__main__":
    unittest.main()
