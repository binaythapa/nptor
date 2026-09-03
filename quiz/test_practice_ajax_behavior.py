from pathlib import Path
from django.test import SimpleTestCase


class PracticeAjaxBehaviorTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(__file__).resolve().parents[1]

    def test_question_actions_are_owned_by_practice_js(self):
        js = (self.root / "static/js/pages/practice.js").read_text()
        template = (
            self.root / "templates/quiz/student/practice/practice.html"
        ).read_text()

        self.assertIn('event.preventDefault();', js)
        self.assertIn('fetch(', js)
        self.assertIn('replacePracticeContent(', js)
        self.assertIn('data-practice-skip', js)
        self.assertIn('data-practice-next', js)
        self.assertNotIn('window.fetch = async function', template)

    def test_progress_updates_after_successful_question_transition(self):
        js = (self.root / "static/js/pages/practice.js").read_text()

        self.assertIn("function updateProgress", js)
        self.assertIn("updateProgress(1);", js)
        self.assertIn('aria-valuenow', js)
