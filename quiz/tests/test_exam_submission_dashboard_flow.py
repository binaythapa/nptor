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

    def test_submit_endpoint_handles_direct_get_without_405(self):
        root = Path(__file__).resolve().parents[2]
        view_source = (root / "quiz" / "views" / "exam_submission.py").read_text(encoding="utf-8")

        self.assertNotIn("@require_POST", view_source)
        self.assertIn('if request.method == "GET":', view_source)
        self.assertIn('return redirect("quiz:student_dashboard")', view_source)

    def test_unified_learning_activity_table_supports_courses_exams_and_tracks(self):
        root = Path(__file__).resolve().parents[2]
        view_source = (root / "quiz" / "views" / "student_learning_dashboard.py").read_text(encoding="utf-8")
        template = (root / "templates" / "quiz" / "student" / "student_dashboard.html").read_text(encoding="utf-8")

        self.assertIn("learning_activity", view_source)
        self.assertIn("activity_type", view_source)
        self.assertIn("activity_date", view_source)
        self.assertIn('class="dashboard-learning-activity-table"', template)
        self.assertIn('data-activity-type="course"', template)
        self.assertIn('data-activity-type="exam"', template)
        self.assertIn('data-activity-type="track"', template)
        self.assertIn("Learning Activity", template)

    def test_learning_activity_is_paginated_and_searchable(self):
        root = Path(__file__).resolve().parents[2]
        view_source = (root / "quiz" / "views" / "student_learning_dashboard.py").read_text(encoding="utf-8")
        template = (root / "templates" / "quiz" / "student" / "student_dashboard.html").read_text(encoding="utf-8")
        css = (root / "static" / "css" / "dashboard_learning_hub.css").read_text(encoding="utf-8")

        self.assertIn("Paginator(learning_activity, 5).get_page", view_source)
        self.assertIn('request.GET.get("activity_page", 1)', view_source)
        self.assertIn('request.GET.get("activity_search", "")', view_source)
        self.assertIn('request.GET.get("activity_type", "all")', view_source)
        self.assertIn('"learning_activity_page": learning_activity_page', view_source)
        self.assertIn('name="activity_search"', template)
        self.assertIn('name="activity_type"', template)
        self.assertIn("learning_activity_page.has_previous", template)
        self.assertIn("learning_activity_page.has_next", template)
        self.assertIn("get_elided_page_range", template)
        self.assertIn("dashboard-learning-activity-pagination", css)

    def test_dashboard_resource_filters_ignore_learning_activity_rows(self):
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
