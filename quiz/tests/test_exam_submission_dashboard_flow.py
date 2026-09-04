from pathlib import Path
import unittest


class ExamSubmissionDashboardFlowTests(unittest.TestCase):
    def test_exam_submit_route_uses_dashboard_first_submit_view(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "quiz" / "urls" / "urls.py").read_text(encoding="utf-8")
        view_source = (root / "quiz" / "views" / "exam_submission.py").read_text(encoding="utf-8")

        self.assertIn("from quiz.views.exam_submission import exam_submit_dashboard", source)
        self.assertIn(
            'path("exam/attempt/<int:user_exam_id>/submit/", require_POST(exam_submit_dashboard), name="exam_submit")',
            source,
        )
        self.assertIn("grade_exam(user_exam, request.POST, is_mock=is_mock)", view_source)
        self.assertIn('return redirect("quiz:student_dashboard")', view_source)

    def test_student_dashboard_exposes_submitted_attempts_for_answer_review(self):
        root = Path(__file__).resolve().parents[2]
        view_source = (root / "quiz" / "views" / "student_learning_dashboard.py").read_text(encoding="utf-8")
        template = (root / "templates" / "quiz" / "student" / "student_dashboard.html").read_text(encoding="utf-8")

        self.assertIn('"submitted_attempts": submitted_attempts', view_source)
        self.assertIn("Recent Exam Results", template)
        self.assertIn("View Answers", template)
        self.assertIn("quiz:exam_result", template)

    def test_dashboard_resource_filters_ignore_recent_result_cards(self):
        root = Path(__file__).resolve().parents[2]
        script = (root / "static" / "js" / "pages" / "dashboard_resource_filters.js").read_text(encoding="utf-8")

        self.assertIn('document.querySelectorAll("[data-dashboard-grid] [data-learning-card]")', script)

    def test_exam_result_remains_the_read_only_answer_review_destination(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "result.html").read_text(encoding="utf-8")

        self.assertIn("ANSWER REVIEW", template)
        self.assertIn("📋 Answer Review", template)


if __name__ == "__main__":
    unittest.main()
