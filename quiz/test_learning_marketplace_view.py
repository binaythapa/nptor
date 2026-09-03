from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from quiz.models import Category, Domain, Exam


User = get_user_model()


class LearningMarketplaceViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="marketplace-user",
            password="test-password",
        )
        self.client.force_login(self.user)
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

    def test_marketplace_is_domain_first_and_links_to_domain_hub(self):
        Course.objects.create(
            title="Snowflake Fundamentals",
            description="Learn Snowflake.",
            category=self.category,
            level="beginner",
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )

        response = self.client.get(reverse("quiz:learning_marketplace"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Explore by domain")
        self.assertContains(response, "Snowflake")
        self.assertContains(
            response,
            reverse("quiz:learning_domain", kwargs={"slug": "snowflake"}),
        )

    def test_search_and_type_filter_are_server_side(self):
        Exam.objects.create(
            title="Snowflake Core Exam",
            primary_category=self.category,
            question_count=10,
            duration_seconds=1800,
            is_published=True,
            is_free=True,
        )
        Exam.objects.create(
            title="Different Exam",
            primary_category=self.category,
            question_count=10,
            duration_seconds=1800,
            is_published=True,
            is_free=True,
        )

        response = self.client.get(
            reverse("quiz:learning_marketplace"),
            {"q": "Snowflake Core", "type": "exams"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Snowflake Core Exam")
        self.assertNotContains(response, "Different Exam")

    def test_domain_hub_excludes_other_domain_resources(self):
        aws = Domain.objects.create(name="AWS", slug="aws", is_active=True)
        aws_category = Category.objects.create(
            name="AWS Core",
            slug="aws-core",
            domain=aws,
            is_active=True,
        )
        Course.objects.create(
            title="Snowflake Course",
            description="Snowflake.",
            category=self.category,
            level="beginner",
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )
        Course.objects.create(
            title="AWS Course",
            description="AWS.",
            category=aws_category,
            level="beginner",
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )

        response = self.client.get(
            reverse("quiz:learning_domain", kwargs={"slug": "snowflake"})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Snowflake Course")
        self.assertNotContains(response, "AWS Course")
