from pathlib import Path

from django.test import SimpleTestCase


class CourseOverviewTemplateContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = (
            Path(__file__).resolve().parent.parent
            / "templates"
            / "courses"
            / "student"
            / "course_detail.html"
        ).read_text(encoding="utf-8")

    def test_overview_has_professional_course_sections(self):
        for hook in (
            'class="course-overview-page"',
            'class="course-overview-hero"',
            'class="course-overview-stats"',
            'class="course-overview-progress"',
            'class="course-curriculum-preview"',
            'class="course-description"',
            'class="course-detail-actions"',
        ):
            self.assertIn(hook, self.template)

    def test_overview_uses_existing_course_data_without_new_model_fields(self):
        for hook in (
            "course.title",
            "course.description",
            "course.level",
            "course.category",
            "course.thumbnail",
            "completed",
            "total",
            "progress",
            "course.created_by",
        ):
            self.assertIn(hook, self.template)

    def test_overview_preserves_existing_access_actions(self):
        for hook in (
            "courses:course_learn",
            "courses:enroll_free_course",
            "courses:subscribe_course",
            "course_is_free",
            "is_enrolled",
            "is_preview",
        ):
            self.assertIn(hook, self.template)

    def test_overview_includes_curriculum_and_learning_cta(self):
        for hook in (
            "Course curriculum",
            "lessons",
            "Start Learning",
            "Resume Learning",
            "Continue Learning",
        ):
            self.assertIn(hook, self.template)
