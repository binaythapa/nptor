from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from quiz.models import Category, Domain, Exam, ExamTrack, LearningShortlist


User = get_user_model()


class LearningShortlistViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="shortlist-view-user",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="other-shortlist-user",
            password="test-password",
        )
        self.domain = Domain.objects.create(
            name="Snowflake",
            slug="snowflake",
            is_active=True,
        )
        self.category = Category.objects.create(
            name="Snowflake Core",
            slug="snowflake-core",
            domain=self.domain,
            is_active=True,
        )
        self.course = Course.objects.create(
            title="Snowflake Fundamentals",
            description="Learn Snowflake.",
            category=self.category,
            level="beginner",
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )
        self.exam = Exam.objects.create(
            title="Snowflake Core Exam",
            primary_category=self.category,
            question_count=10,
            duration_seconds=1800,
            is_published=True,
            is_free=False,
        )
        self.url = reverse(
            "quiz:learning_shortlist_toggle",
            args=["course", self.course.id],
        )

    def test_requires_login(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(LearningShortlist.objects.exists())

    def test_toggle_is_post_only(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertFalse(LearningShortlist.objects.exists())

    def test_post_toggles_only_a_public_resource_for_current_user(self):
        self.client.force_login(self.user)

        first = self.client.post(self.url)
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["shortlisted"])
        self.assertTrue(
            LearningShortlist.objects.filter(
                user=self.user,
                course=self.course,
            ).exists()
        )

        second = self.client.post(self.url)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.json()["shortlisted"])
        self.assertFalse(
            LearningShortlist.objects.filter(
                user=self.user,
                course=self.course,
            ).exists()
        )

    def test_user_cannot_shortlist_hidden_resource(self):
        hidden = Course.objects.create(
            title="Hidden Course",
            description="Not public.",
            category=self.category,
            level="beginner",
            is_public=False,
            is_published=False,
            approval_status=Course.APPROVAL_DRAFT,
        )
        self.client.force_login(self.user)
        url = reverse(
            "quiz:learning_shortlist_toggle",
            args=["course", hidden.id],
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            LearningShortlist.objects.filter(
                user=self.user,
                course=hidden,
            ).exists()
        )

    def test_shortlist_is_user_scoped(self):
        LearningShortlist.for_resource(
            user=self.other_user,
            resource_type=LearningShortlist.RESOURCE_COURSE,
            resource=self.course,
        )
        self.client.force_login(self.user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["shortlisted"])
        self.assertEqual(
            LearningShortlist.objects.filter(course=self.course).count(),
            2,
        )
