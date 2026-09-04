from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import resolve
from django.template.loader import get_template

from courses.models import Course, CourseSection, Lesson
from quiz.models import ExamTrack
from subscriptions.models import SubscriptionPlan


User = get_user_model()


class LearningMarketplaceCTATests(SimpleTestCase):
    def test_marketplace_uses_resource_specific_actions(self):
        template = get_template("quiz/student/learning_marketplace.html")
        source = Path(template.origin.name).read_text(encoding="utf-8")

        self.assertIn("Preview →", source)
        self.assertIn("Start →", source)
        self.assertIn("{% url 'quiz:learning_track' item.resource.slug %}", source)
        self.assertIn("{% url 'courses:course_preview' item.resource.slug %}", source)
        self.assertIn("{% url 'quiz:exam_preview' item.resource.id %}", source)

    def test_learning_track_route_resolves_to_dedicated_view(self):
        self.assertEqual(
            resolve("/quiz/learning/track/sample-track/").url_name,
            "learning_track",
        )

    def test_free_preview_template_has_lock_and_unlock_actions(self):
        template = get_template("courses/student/course_free_preview.html")
        source = Path(template.origin.name).read_text(encoding="utf-8")

        self.assertIn("FREE COURSE PREVIEW", source)
        self.assertIn("Unlock Full Course", source)
        self.assertIn("preview=1", source)
        self.assertIn("course-free-preview.css", source)


class LearningTrackViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="track-view-user",
            password="test-password",
        )
        self.track = ExamTrack.objects.create(
            title="Test Learning Track",
            slug="test-learning-track",
            description="Track description",
            pricing_type=ExamTrack.PRICING_FREE,
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_track_page_lists_published_exams(self):
        response = self.client.get(
            f"/quiz/learning/track/{self.track.slug}/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["track"], self.track)
        self.assertEqual(response.context["exams"], [])
        self.assertTrue(response.context["is_free"])
