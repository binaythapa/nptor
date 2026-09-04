from pathlib import Path

from django.test import SimpleTestCase


class CourseVideoProgressUITests(SimpleTestCase):
    def test_video_progress_waits_for_youtube_api_when_api_is_not_ready(self):
        source = Path("static/js/pages/course_video_progress.js").read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            'if (!iframe || typeof YT === "undefined" || !YT.Player) return;',
            source,
        )
        self.assertIn("window.onYouTubeIframeAPIReady", source)
        self.assertIn("new YT.Player", source)

    def test_video_progress_posts_completion_threshold(self):
        source = Path("static/js/pages/course_video_progress.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("watched: String(watched)", source)
        self.assertIn("duration: String(duration)", source)
        self.assertIn("data.completed", source)
