from pathlib import Path

from django.test import SimpleTestCase


class CoursePlayerTemplateContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = (
            Path(__file__).resolve().parent.parent
            / "templates"
            / "courses"
            / "student"
            / "course_player.html"
        ).read_text(encoding="utf-8")

    def test_player_has_professional_lms_regions(self):
        for hook in (
            'class="course-player-header"',
            'id="courseSidebar"',
            'class="course-curriculum"',
            'class="course-content"',
            'class="course-progress"',
            'class="lesson-navigation"',
        ):
            self.assertIn(hook, self.template)

    def test_mobile_curriculum_control_is_accessible(self):
        self.assertIn('aria-controls="courseSidebar"', self.template)
        self.assertIn('aria-expanded="false"', self.template)
        self.assertIn('aria-label="Open course lessons"', self.template)

    def test_existing_learning_flow_hooks_are_preserved(self):
        for hook in (
            "courseVideoPlayer",
            "track_video_progress",
            "quiz:exam_start",
            "quiz:practice",
            "course_certificate_pdf",
            "lessonPrev",
            "lessonNext",
        ):
            self.assertIn(hook, self.template)

    def test_preview_mode_keeps_preview_navigation_and_notice(self):
        self.assertIn("is_preview", self.template)
        self.assertIn("preview=1", self.template)
        self.assertIn("preview-notice", self.template)

    def test_lesson_polish_hooks_keep_assessment_and_completion_hierarchy(self):
        for hook in (
            'class="lesson-meta"',
            'class="assessment-card"',
            'class="completion-stat"',
            'class="certificate-card"',
        ):
            self.assertIn(hook, self.template)
