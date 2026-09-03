from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from quiz.models import Category, Domain, LearningShortlist


User = get_user_model()


class StudentLearningDashboardShortlistTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="dashboard-shortlist-user",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="dashboard-other-user",
            password="test-password",
        )
        domain = Domain.objects.create(
            name="Snowflake",
            slug="snowflake",
            is_active=True,
        )
        category = Category.objects.create(
            name="Snowflake Core",
            slug="snowflake-core",
            domain=domain,
            is_active=True,
        )
        self.course = Course.objects.create(
            title="Snowflake Fundamentals",
            slug="snowflake-fundamentals",
            description="Learn Snowflake.",
            category=category,
            level="beginner",
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )

    def test_dashboard_shows_only_current_users_shortlist(self):
        LearningShortlist.for_resource(
            user=self.user,
            resource_type=LearningShortlist.RESOURCE_COURSE,
            resource=self.course,
        )
        LearningShortlist.for_resource(
            user=self.other_user,
            resource_type=LearningShortlist.RESOURCE_COURSE,
            resource=self.course,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse("quiz:student_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["shortlist_count"], 1)
        self.assertEqual(response.context["shortlist_items"][0]["resource"], self.course)
        self.assertContains(response, "Your Shortlist")

    def test_unpublished_shortlist_is_not_rendered(self):
        LearningShortlist.for_resource(
            user=self.user,
            resource_type=LearningShortlist.RESOURCE_COURSE,
            resource=self.course,
        )
        self.course.is_published = False
        self.course.save(update_fields=["is_published"])

        self.client.force_login(self.user)
        response = self.client.get(reverse("quiz:student_dashboard"))

        self.assertEqual(response.context["shortlist_count"], 0)
