from pathlib import Path
from django.test import SimpleTestCase


class CourseVideoProgressSecurityTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(__file__).resolve().parents[1]

    def test_player_uses_youtube_playback_time(self):
        template = (
            self.root / "templates/courses/student/course_player.html"
        ).read_text()
        tracker = (
            self.root / "static/js/pages/course_video_progress.js"
        ).read_text()

        self.assertIn("courseVideoPlayer", template)
        self.assertIn("course_video_progress.js", template)
        self.assertIn("YT.Player", tracker)
        self.assertIn("getCurrentTime", tracker)
        self.assertIn("getDuration", tracker)
        self.assertIn("PlayerState.PLAYING", tracker)

    def test_fake_elapsed_page_timer_is_not_used(self):
        template = (
            self.root / "templates/courses/student/course_player.html"
        ).read_text()

        self.assertNotIn("let watchedSeconds=0, duration=390", template)
        self.assertNotIn("watchedSeconds+=5", template)
