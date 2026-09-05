from pathlib import Path

from django.test import SimpleTestCase


class TrackDetailContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        root = Path(__file__).resolve().parent.parent
        cls.template = (root / "templates" / "quiz" / "student" / "learning_track.html").read_text(encoding="utf-8")
        cls.styles = (root / "static" / "css" / "pages" / "learning_track.css").read_text(encoding="utf-8")

    def test_track_page_has_progress_and_exam_state_hooks(self):
        for text in (
            'class="track-hero"',
            'class="track-progress"',
            'class="track-exam-card"',
            'class="track-exam-status"',
            'class="track-lock-message"',
            'class="track-primary-action"',
        ):
            self.assertIn(text, self.template)

    def test_track_page_explains_progression_and_access_states(self):
        for text in (
            "Certification progress",
            "Completed",
            "Locked",
            "Pass the previous exam to unlock",
            "Prerequisite exam",
            "You have access",
            "Unlock Full Track",
        ):
            self.assertIn(text, self.template)

    def test_track_page_is_responsive_and_accessible(self):
        for text in (
            'aria-labelledby="track-title"',
            'aria-label="Track progress"',
            'aria-label="Exams in this track"',
            "@media (max-width: 760px)",
            "@media (prefers-reduced-motion: reduce)",
        ):
            self.assertIn(text, self.template if text.startswith("aria-") else self.styles)
