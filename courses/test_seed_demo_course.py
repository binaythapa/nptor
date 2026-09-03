from pathlib import Path

from django.test import SimpleTestCase


class SeedDemoCourseTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(__file__).resolve().parents[1]

    def test_demo_course_command_contains_complete_learning_flow(self):
        command = (
            self.root
            / "courses/management/commands/seed_demo_course.py"
        ).read_text()

        self.assertIn("CourseSection", command)
        self.assertIn("Lesson", command)
        self.assertIn("TYPE_ARTICLE", command)
        self.assertIn("TYPE_VIDEO", command)
        self.assertIn("TYPE_QUIZ", command)
        self.assertIn("Exam", command)
        self.assertIn("ExamCategoryAllocation", command)
        self.assertIn("--reset", command)

    def test_demo_course_is_publicly_available_after_seeding(self):
        command = (
            self.root
            / "courses/management/commands/seed_demo_course.py"
        ).read_text()

        self.assertIn("approval_status=Course.APPROVAL_APPROVED", command)
        self.assertIn("is_published=True", command)
        self.assertIn("is_public=True", command)

    def test_demo_command_is_idempotent(self):
        command = (
            self.root
            / "courses/management/commands/seed_demo_course.py"
        ).read_text()

        self.assertIn("update_or_create", command)
        self.assertIn("transaction.atomic", command)
