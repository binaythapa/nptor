from pathlib import Path
from django.test import SimpleTestCase


class CourseVideoProgressSecurityTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(__file__).resolve().parents[1]

    def test_player_tracks_real_youtube_time_instead_of_fake_timer(self):
        template = (
            self.root / "templates/courses/student/course_player.html"
        ).read_text()

        self.assertIn("YT.Player", template)
        self.assertIn("getCurrentTime", template)
        self.assertIn("getDuration", template)
        self.assertNotIn("let watchedSeconds=0, duration=390", template)
        self.assertNotIn("watchedSeconds+=5", template)

    def test_video_progress_view_validates_watched_bounds(self):
        source = (
            self.root / "courses/views/student_views.py"
        ).read_text()

        self.assertIn("watched < 0", source)
        self.assertIn("duration <= 0", source)
        self.assertIn("watched > duration", source)
        self.assertIn("MAX_VIDEO_DURATION", source)
