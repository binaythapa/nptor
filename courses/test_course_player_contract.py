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

    def test_final_polish_hooks_keep_compact_assessment_and_navigation_actions(self):
        for hook in (
            'class="lesson-surface lesson-surface-assessment"',
            'class="assessment-actions"',
            'class="certificate-card-main"',
            'class="certificate-actions"',
            'class="certificate-verify-btn"',
            'id="lessonNextLabel"',
        ):
            self.assertIn(hook, self.template)
        self.assertIn("Retake Assessment", self.template)

    def test_horizontal_overflow_constraints_are_defined(self):
        stylesheet = (
            Path(__file__).resolve().parent.parent
            / "static"
            / "css"
            / "pages"
            / "course-player-polish.css"
        ).read_text(encoding="utf-8")
        self.assertIn("min-width: 0;", stylesheet)
        self.assertIn("overflow-x: hidden;", stylesheet)
        self.assertIn("max-width: 100%;", stylesheet)
