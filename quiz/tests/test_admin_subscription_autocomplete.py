from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from quiz.models import ExamTrack


User = get_user_model()


class AdminSubscriptionAutocompleteTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="admin-search",
            email="admin-search@example.com",
            password="password",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(self.staff)

        User.objects.create_user(
            username="test-user",
            email="test@example.com",
            password="password",
            is_active=True,
        )
        User.objects.create_user(
            username="alpha-user",
            email="alpha@example.com",
            password="password",
            is_active=True,
        )

        Course.objects.create(
            title="Test Python Course",
            description="Test course",
            level="beginner",
            is_published=True,
            is_public=True,
            created_by=self.staff,
        )
        Course.objects.create(
            title="Accounting Basics",
            description="Accounting course",
            level="beginner",
            is_published=True,
            is_public=True,
            created_by=self.staff,
        )

        ExamTrack.objects.create(title="Test BI Track", slug="test-bi-track")
        ExamTrack.objects.create(title="Accounting Track", slug="accounting-track")

    def test_user_search_returns_only_prefix_matches(self):
        response = self.client.get(
            reverse("quiz:admin_subscription_user_search"),
            {"q": "test"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["username"] for item in response.json()["results"]],
            ["test-user"],
        )

    def test_course_search_returns_only_prefix_matches(self):
        response = self.client.get(
            reverse("quiz:admin_subscription_course_search"),
            {"q": "test"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["title"] for item in response.json()["results"]],
            ["Test Python Course"],
        )

    def test_track_search_returns_only_prefix_matches(self):
        response = self.client.get(
            reverse("quiz:admin_subscription_track_search"),
            {"q": "test"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["title"] for item in response.json()["results"]],
            ["Test BI Track"],
        )
